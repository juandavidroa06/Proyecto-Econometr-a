"""
panel.py — Panel semanal de varianza realizada (DEC-029)
=========================================================

Responsabilidad única: pasar de datos diarios a un panel (semana w, empresa)
con variables conocidas al cierre de la semana w y objetivos de w+1.

Definiciones (fijadas en DEC-029 antes de ejecutar):
    - Semanas de calendario que terminan en viernes (``W-FRI``); válida si
      tiene al menos ``MIN_DIAS`` días con rendimiento.
    - RV_w = suma de (100 r_t)^2 de la semana (en %^2).
    - HAR: RV_w, media de RV de las semanas w-3..w y r^2 del último día.
    - Externas: |rendimiento semanal| de TRM y Brent con precios de fecha
      ESTRICTAMENTE anterior al último día bursátil de la semana.
    - Objetivo: semana inmediatamente siguiente (w+1) y válida; si no, la
      fila se descarta (se cuenta).
"""

import numpy as np
import pandas as pd

MIN_DIAS = 3
ESCALA = 100.0


def _semana(indice):
    return pd.DatetimeIndex(indice).to_period("W-FRI")


def resumen_semanal(r, volumen):
    """Agregados semanales de una empresa (r y volumen diarios, mismo índice)."""
    datos = pd.DataFrame({"r": r, "vol": np.log1p(volumen)}).dropna(subset=["r"])
    datos["sem"] = _semana(datos.index)
    g = datos.groupby("sem")
    out = pd.DataFrame({
        "n_dias": g.size(),
        "rv": g["r"].apply(lambda x: float(((ESCALA * x) ** 2).sum())),
        "rv_dia": g["r"].apply(lambda x: float((ESCALA * x.iloc[-1]) ** 2)),
        "ret": g["r"].sum(),
        "abs_ret": g["r"].apply(lambda x: float(x.abs().sum())),
        "pct_cero": g["r"].apply(lambda x: float((x == 0).mean())),
        "log_vol": g["vol"].mean(),
        "ultimo_dia": g.apply(lambda x: x.index.max(), include_groups=False),
    })
    return out


def externas_semanales(externos, ultimos_dias):
    """|rendimiento semanal| de cada externa con precios de fecha < último día.

    ``ultimos_dias``: Series {semana: último día bursátil}. Retorna DataFrame
    indexado por semana.
    """
    izq = pd.DataFrame({"sem": ultimos_dias.index, "Date": ultimos_dias.to_numpy()})
    izq = izq.sort_values("Date")
    salida = pd.DataFrame(index=ultimos_dias.index)
    for col in externos.columns:
        der = externos[[col]].dropna().reset_index().rename(columns={"index": "Date"})
        der.columns = ["Date", "precio"]
        unido = pd.merge_asof(izq, der, on="Date", direction="backward",
                              allow_exact_matches=False,
                              tolerance=pd.Timedelta(days=10))
        precio = unido.set_index("sem")["precio"].sort_index()
        salida[f"{col}_abs_ret_sem"] = np.log(precio).diff().abs()
    return salida


def construir_panel_semanal(rend_log, volumen, externos, empresas):
    """Panel (semana, empresa) con variables de w y objetivos de w+1."""
    resumenes = {e: resumen_semanal(rend_log[e], volumen[e]) for e in empresas}
    validas = {e: s[s["n_dias"] >= MIN_DIAS].copy() for e, s in resumenes.items()}

    # RV promedio de las empresas en la semana (variable de "mercado").
    rv_mercado = pd.concat({e: s["rv"] for e, s in validas.items()}, axis=1).mean(axis=1)
    ultimo = pd.concat({e: s["ultimo_dia"] for e, s in resumenes.items()}, axis=1).max(axis=1)
    ext = externas_semanales(externos, ultimo)

    bloques = []
    for e, s in validas.items():
        s = s.sort_index()
        b = pd.DataFrame(index=s.index)
        b["rv_sem"] = s["rv"]
        b["rv_mes"] = s["rv"].rolling(4, min_periods=4).mean()
        b["rv_dia"] = s["rv_dia"]
        b["ret_sem"] = s["ret"]
        b["abs_ret_sem"] = s["abs_ret"]
        b["pct_cero_sem"] = s["pct_cero"]
        b["log_vol_rel"] = s["log_vol"] - s["log_vol"].rolling(4, min_periods=4).median().shift(1)
        b["rv_mercado"] = rv_mercado.reindex(s.index)
        b = b.join(ext)
        # Objetivo: semana calendario inmediatamente siguiente y válida.
        siguiente = s.index + 1
        es_siguiente = pd.Series(siguiente, index=s.index).isin(s.index)
        b["semana_objetivo"] = siguiente
        b["rv_objetivo"] = s["rv"].reindex(siguiente).to_numpy()
        b["ret_objetivo"] = s["ret"].reindex(siguiente).to_numpy()
        b["n_dias_objetivo"] = s["n_dias"].reindex(siguiente).to_numpy()
        b.loc[~es_siguiente.to_numpy(), ["rv_objetivo", "ret_objetivo", "n_dias_objetivo"]] = np.nan
        b["ultimo_dia"] = s["ultimo_dia"]
        b["empresa"] = e
        bloques.append(b)
    panel = pd.concat(bloques).rename_axis("semana").reset_index()
    panel["fecha_objetivo"] = panel["semana_objetivo"].dt.end_time.dt.normalize()
    return panel.sort_values(["semana", "empresa"]).reset_index(drop=True)


VARIABLES_HAR = ["log_rv_sem", "log_rv_mes", "log_rv_dia"]


def variables_modelo(panel):
    """Agrega logs (con piso para ceros) y devuelve (panel, columnas ML)."""
    p = panel.copy()
    piso = 1e-4   # %^2: evita log(0) en semanas o días sin variación
    for c in ("rv_sem", "rv_mes", "rv_dia", "rv_mercado"):
        p[f"log_{c}"] = np.log(np.maximum(p[c], piso))
    p["log_rv_objetivo"] = np.log(np.maximum(p["rv_objetivo"], piso))
    columnas = VARIABLES_HAR + ["log_rv_mercado", "ret_sem", "abs_ret_sem", "pct_cero_sem",
                                "log_vol_rel"] + [c for c in p.columns if c.endswith("_abs_ret_sem")]
    return p, columnas


def separar(panel, columnas, fin_train, fin_validacion, objetivo):
    """Separa por fecha de la semana OBJETIVO; descarta filas incompletas."""
    fin_train, fin_validacion = pd.Timestamp(fin_train), pd.Timestamp(fin_validacion)
    f = panel["fecha_objetivo"]
    bloques = {"train": panel[f <= fin_train],
               "validacion": panel[(f > fin_train) & (f <= fin_validacion)]}
    resumen, salida = [], {}
    for nombre, b in bloques.items():
        completo = b.dropna(subset=columnas + [objetivo])
        resumen.append({"bloque": nombre, "filas": len(b), "completas": len(completo),
                        "descartadas": len(b) - len(completo)})
        salida[nombre] = completo.reset_index(drop=True)
    if salida["train"]["fecha_objetivo"].max() >= salida["validacion"]["fecha_objetivo"].min():
        raise ValueError("Leakage: semanas objetivo de train y validación se solapan.")
    return salida["train"], salida["validacion"], pd.DataFrame(resumen)
