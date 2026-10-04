"""
variables.py — Variables explicativas y objetivo para la Fase 8 (DEC-025)
==========================================================================

Responsabilidad única: construir el panel (fecha de origen t, empresa) con
variables conocidas al cierre de t y el objetivo r_{t+1}.

Reglas anti-leakage:
    - Toda variable de una fila de origen t usa datos con fecha <= t
      (ventanas móviles hacia atrás, sin centrar).
    - Las externas (TRM, Brent) se toman con fecha ESTRICTAMENTE anterior a
      t (``merge_asof`` con ``allow_exact_matches=False``): su cierre diario
      en Yahoo ocurre después del cierre de la BVC.
    - Cada fila se asigna a entrenamiento o validación por la fecha del
      OBJETIVO (t+1), no por la de origen: así ningún objetivo de
      validación entra al entrenamiento.
    - No se imputa nada: las filas con faltantes se descartan de forma
      explícita y se cuentan.
"""

import numpy as np
import pandas as pd

VENTANA_CORTA = 5
VENTANA_LARGA = 21
REZAGOS = 5
TOLERANCIA_EXTERNOS = pd.Timedelta(days=7)


def _validar_ancho(df, nombre):
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"{nombre}: se esperaba un DataFrame.")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError(f"{nombre}: el índice debe ser DatetimeIndex.")
    if not df.index.is_monotonic_increasing or df.index.has_duplicates:
        raise ValueError(f"{nombre}: índice no cronológico o con duplicados.")


def _rolling(serie, ventana, funcion):
    return getattr(serie.rolling(ventana, min_periods=int(ventana * 0.8)), funcion)()


def variables_empresa(r, volumen):
    """Variables de una empresa en su calendario (columna Series)."""
    log_vol = np.log1p(volumen)
    v = {f"r_lag{k}": r.shift(k) for k in range(REZAGOS)}
    v.update({
        f"media_{VENTANA_CORTA}": _rolling(r, VENTANA_CORTA, "mean"),
        f"media_{VENTANA_LARGA}": _rolling(r, VENTANA_LARGA, "mean"),
        f"vol_{VENTANA_CORTA}": _rolling(r, VENTANA_CORTA, "std"),
        f"vol_{VENTANA_LARGA}": _rolling(r, VENTANA_LARGA, "std"),
        f"pct_cero_{VENTANA_LARGA}": _rolling((r == 0).astype(float).where(r.notna()),
                                             VENTANA_LARGA, "mean"),
        "log_volumen_rel": log_vol - _rolling(log_vol, VENTANA_LARGA, "median"),
    })
    return pd.DataFrame(v)


def variables_externas(externos, fechas):
    """Rendimientos log de las externas conocidos ANTES de cada fecha.

    ``externos``: precios en su propio calendario. Retorna DataFrame indexado
    por ``fechas`` con el último rendimiento diario y el acumulado de 5 días
    con fecha estrictamente anterior (tolerancia de 7 días; si no hay dato
    reciente queda NaN).
    """
    _validar_ancho(externos, "externos")
    salida = pd.DataFrame(index=pd.DatetimeIndex(fechas, name="Date"))
    izquierda = pd.DataFrame({"Date": salida.index})
    for col in externos.columns:
        serie = np.log(externos[col].dropna()).diff()
        derecha = pd.DataFrame({
            "Date": serie.index,
            f"{col}_r1": serie.to_numpy(),
            f"{col}_r5": serie.rolling(VENTANA_CORTA).sum().to_numpy(),
        }).dropna()
        unido = pd.merge_asof(izquierda, derecha, on="Date", direction="backward",
                              allow_exact_matches=False,
                              tolerance=TOLERANCIA_EXTERNOS)
        salida[f"{col}_r1"] = unido[f"{col}_r1"].to_numpy()
        salida[f"{col}_r5"] = unido[f"{col}_r5"].to_numpy()
    return salida


def construir_panel(rend_log, volumen, externos):
    """Panel largo: una fila por (fecha de origen, empresa).

    Columnas: Date (origen t), fecha_objetivo, empresa, variables, objetivo
    (r_{t+1}). La fecha objetivo es la siguiente fecha del calendario de la
    empresa con rendimiento observado o no (se usa el índice del panel).
    """
    _validar_ancho(rend_log, "rend_log")
    _validar_ancho(volumen, "volumen")
    if not rend_log.index.equals(volumen.index) or list(rend_log.columns) != list(volumen.columns):
        raise ValueError("rend_log y volumen deben tener el mismo índice y columnas.")

    mercado = rend_log.mean(axis=1)  # promedio de las empresas con dato en t
    comunes = pd.DataFrame({
        "mercado_r0": mercado,
        f"mercado_media_{VENTANA_CORTA}": _rolling(mercado, VENTANA_CORTA, "mean"),
    })
    externas = variables_externas(externos, rend_log.index)
    fecha_siguiente = pd.Series(rend_log.index, index=rend_log.index).shift(-1)

    bloques = []
    for empresa in rend_log.columns:
        r = rend_log[empresa]
        v = variables_empresa(r, volumen[empresa])
        v = v.join(comunes).join(externas)
        v["empresa"] = empresa
        v["fecha_objetivo"] = fecha_siguiente
        v["objetivo"] = r.shift(-1)
        bloques.append(v)
    panel = pd.concat(bloques).rename_axis("Date").reset_index()
    return panel.sort_values(["Date", "empresa"]).reset_index(drop=True)


def columnas_variables(panel):
    """Columnas explicativas (sin identificadores ni objetivo)."""
    excluir = {"Date", "fecha_objetivo", "empresa", "objetivo"}
    return [c for c in panel.columns if c not in excluir]


def separar(panel, fin_train, fin_validacion):
    """Divide por FECHA OBJETIVO y descarta filas incompletas (contándolas).

    Retorna (train, validacion, resumen) donde resumen informa cuántas filas
    se descartaron por faltantes en cada bloque.
    """
    fin_train, fin_validacion = pd.Timestamp(fin_train), pd.Timestamp(fin_validacion)
    obj = panel["fecha_objetivo"]
    bloques = {"train": panel[obj <= fin_train],
               "validacion": panel[(obj > fin_train) & (obj <= fin_validacion)]}
    cols = columnas_variables(panel) + ["objetivo"]
    resumen, salida = [], {}
    for nombre, b in bloques.items():
        completo = b.dropna(subset=cols)
        resumen.append({"bloque": nombre, "filas": len(b),
                        "filas_completas": len(completo),
                        "descartadas_por_faltantes": len(b) - len(completo)})
        salida[nombre] = completo.reset_index(drop=True)
    if salida["train"]["fecha_objetivo"].max() >= salida["validacion"]["fecha_objetivo"].min():
        raise ValueError("Leakage: objetivos de train y validación se solapan.")
    return salida["train"], salida["validacion"], pd.DataFrame(resumen)
