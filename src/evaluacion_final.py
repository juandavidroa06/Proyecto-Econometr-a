"""
evaluacion_final.py — Fase 15: evaluación final (plan APROBADO DEC-034)
========================================================================

ÚNICO módulo de ``src`` autorizado a abrir el bloque de prueba
(``confirmar_evaluacion_final=True``; lo vigila
``tests/test_particiones_reales.py``).

Modos:
    ensayo : historia = entrenamiento (2020–2023), evaluación = validación
             (2024). Debe reproducir las Fases 7–14; deja un informe de
             reproducción.
    final  : historia = entrenamiento + validación (2020–2024, Opción A),
             evaluación = prueba (2025-01-02 a 2026-09-14). Se ejecuta UNA
             vez, solo si el ensayo reprodujo, y con ``--confirmar``.

Variantes (DEC-034): ``con_regla`` (principal: fechas detectadas por la regla
mecánica tratadas como DEC-022) y ``sin_regla`` (sensibilidad). Si la regla
no detecta ninguna fecha, ambas coinciden y solo se ejecuta una.

Familias confirmatorias: H15-1 media diaria, H15-2 varianza diaria,
H15-3 volatilidad semanal, H15-4 VaR/ES, H15-5 portafolios walk-forward.

Ejecutar:
    python -m src.evaluacion_final --modo ensayo
    python -m src.evaluacion_final --modo final --confirmar
"""

import argparse
import hashlib
import json
import logging
from datetime import datetime

import numpy as np
import pandas as pd

from config.environment import RUTA_PARTICIONES, RUTA_RESULTADOS
from config.settings import (
    ARIMA_CRITERIO,
    ARIMA_MAX_P,
    ARIMA_MAX_Q,
    EWMA_LAMBDA,
    GARCH_DISTRIBUCION,
    LIMITE_SECTOR,
)
from src.backtesting import fase14
from src.comparacion import fase10
from src.econometrics import arima, garch
from src.machine_learning import modelos, variables
from src.machine_learning.fase8 import matriz_variables
from src.neural_networks import fase9
from src.portfolio.fase6 import construir_portafolios
from src.portfolio.markowitz import log_a_simple, seleccionar_universo_liquido
from src.portfolio.metricas import rendimiento_diario
from src.preprocessing.invalid_data import (
    detectar_reversiones_simultaneas,
    invalidar_fechas_rendimientos,
)
from src.preprocessing.split import cargar_entrenamiento_validacion, cargar_particion
from src.riesgo.fase11 import evaluar_riesgo
from src.volatilidad_semanal import ejecutar as sem
from src.volatilidad_semanal import panel as pv

logger = logging.getLogger(__name__)

BASES = ("rendimientos_log", "volumen", "externos", "tasas")
RUTA_FASE15 = RUTA_RESULTADOS / "fase15"


# --- Datos ------------------------------------------------------------------------

def cargar_bloques(modo):
    """{base: (historia, evaluacion)} según el modo."""
    datos = {b: cargar_entrenamiento_validacion(RUTA_PARTICIONES, b) for b in BASES}
    if modo == "ensayo":
        return {b: (d["train"], d["validacion"]) for b, d in datos.items()}
    if modo == "final":
        bloques = {}
        for b, d in datos.items():
            prueba = cargar_particion(RUTA_PARTICIONES, b, "test", confirmar_evaluacion_final=True)
            bloques[b] = (pd.concat([d["train"], d["validacion"]]), prueba)
        return bloques
    raise ValueError(f"Modo desconocido: {modo!r}")


def aplicar_regla(bloques):
    """Detecta fechas sospechosas en la EVALUACIÓN y aplica DEC-022 (DEC-034)."""
    hist_r, eval_r = bloques["rendimientos_log"]
    hist_v, eval_v = bloques["volumen"]
    detectadas = detectar_reversiones_simultaneas(eval_r)
    if detectadas.empty:
        return bloques, detectadas
    r, v = invalidar_fechas_rendimientos(eval_r, eval_v, detectadas["fecha"])
    nuevos = dict(bloques)
    nuevos["rendimientos_log"] = (hist_r, r)
    nuevos["volumen"] = (hist_v, v)
    return nuevos, detectadas


def cargar_muestra_completa():
    """Muestra completa 2020-01 a 2026-09 para análisis EXPLORATORIOS posteriores
    a la Fase 15 (p. ej. robustez, DEC-037/038), con la regla de DEC-034
    aplicada al bloque de prueba. Este módulo sigue siendo el único punto de
    acceso a la prueba; quien use esta función debe rotular sus resultados
    como exploratorios.
    """
    rep = RUTA_FASE15 / "final" / "huellas_resultados.json"
    if not rep.exists():
        raise RuntimeError("La evaluación final aún no se ha hecho: la prueba no puede usarse.")
    bloques, detectadas = aplicar_regla(cargar_bloques("final"))
    return {b: pd.concat(par) for b, par in bloques.items()}, detectadas


# --- H15-1: rendimiento diario ------------------------------------------------------

def familia_media(bloques, iliquidos, fin_hist, fin_eval):
    hist_r, eval_r = bloques["rendimientos_log"]
    rend = pd.concat([hist_r, eval_r])
    vol = pd.concat(bloques["volumen"])
    ext = pd.concat(bloques["externos"])
    panel = variables.construir_panel(rend, vol, ext)
    train, valid, filas = variables.separar(panel, fin_hist, fin_eval)
    columnas = variables.columnas_variables(panel)
    empresas = list(rend.columns)
    X_tr = matriz_variables(train, columnas, empresas)
    X_va = matriz_variables(valid, columnas, empresas)

    comp = valid[["fecha_objetivo", "empresa", "objetivo"]].copy()
    hiper = []
    for tipo in ("random_forest", "gradient_boosting"):
        mejores, _ = modelos.validacion_cruzada(tipo, X_tr, train["objetivo"], train["Date"])
        comp[tipo] = modelos.ajustar_final(tipo, mejores, X_tr, train["objetivo"]).predict(X_va)
        hiper.append({"modelo": tipo, **{k: str(v) for k, v in mejores.items()}})
    comp["cero"] = 0.0
    comp["media_train"] = comp["empresa"].map(hist_r.mean())

    pron_arima = []
    for e in empresas:
        h, ev = hist_r[e].dropna(), eval_r[e].dropna()
        orden, _ = arima.seleccionar_orden(h, ARIMA_MAX_P, ARIMA_MAX_Q, ARIMA_CRITERIO)
        res, _ = arima.ajustar_arima(h, orden)
        p = arima.pronostico_un_paso(h, ev, res)
        pron_arima.append(pd.DataFrame({"fecha_objetivo": p.index, "empresa": e,
                                        "arima": p.to_numpy()}))
        hiper.append({"modelo": f"arima {e}", "p": str(orden[0]), "q": str(orden[1])})
    comp = comp.merge(pd.concat(pron_arima), on=["fecha_objetivo", "empresa"], how="inner")

    clave = ["fecha_objetivo", "empresa"]
    for tipo in ("mlp", "lstm"):
        h, _ = fase9.seleccionar(tipo, panel, train, columnas, empresas)
        p, _ = fase9.conjunto_final(tipo, h, panel, train, valid, columnas, empresas)
        comp = comp.merge(p[clave + [tipo]], on=clave, how="inner")
        hiper.append({"modelo": tipo, **{k: str(v) for k, v in h.items()}})

    agregado, por_empresa, _ = fase10.comparar_media(comp, iliquidos)
    return {"media": agregado, "media_por_empresa": por_empresa, "media_pronosticos": comp,
            "media_filas": filas, "media_hiperparametros": pd.DataFrame(hiper)}


# --- H15-2: varianza diaria ---------------------------------------------------------

def familia_varianza(bloques, liquidos, iliquidos):
    hist_r, eval_r = bloques["rendimientos_log"]
    pron = []
    for e in hist_r.columns:
        h, ev = hist_r[e].dropna(), eval_r[e].dropna()
        res = garch.ajustar_garch(h, ev, GARCH_DISTRIBUCION)
        pron.append(pd.DataFrame({
            "Date": ev.index, "empresa": e, "rendimiento": ev.to_numpy(),
            "varianza_garch": garch.pronostico_varianza_un_paso(res, h, ev).to_numpy(),
            "varianza_constante": garch.varianza_constante(h, ev).to_numpy(),
            "varianza_ewma": garch.varianza_ewma(h, ev, EWMA_LAMBDA).to_numpy(),
            "garch_convergio": res.convergence_flag == 0}))
    pron = pd.concat(pron, ignore_index=True)
    mcs, por_empresa = fase10.comparar_varianza(pron, liquidos, iliquidos)
    return {"varianza_mcs": mcs, "varianza_por_empresa": por_empresa,
            "varianza_pronosticos": pron}


# --- H15-3: volatilidad semanal -------------------------------------------------------

def familia_semanal(bloques, liquidos, fin_hist, fin_eval):
    rend = pd.concat(bloques["rendimientos_log"])
    panel = pv.construir_panel_semanal(rend, pd.concat(bloques["volumen"]),
                                       pd.concat(bloques["externos"]), liquidos)
    panel, columnas = pv.variables_modelo(panel)
    tr, va, filas = pv.separar(panel, columnas, fin_hist, fin_eval, "rv_objetivo")
    pron = {}
    pron["har"], _ = sem.har(tr, va)
    pron["ewma"], pron["garch"] = sem.referencias_diarias(rend, va, fin_hist)
    for tipo in ("random_forest", "gradient_boosting"):
        pron[tipo], _, _ = sem.arbol(tipo, tr, va, columnas, liquidos, "log_rv_objetivo", en_log=True)
    pron["mlp"], _, _ = sem.mlp(tr, va, columnas, liquidos)
    agregado, pruebas, por_empresa = sem.evaluar_volatilidad(va, pron)
    return {"semanal_volatilidad": agregado, "semanal_pruebas": pruebas,
            "semanal_por_empresa": por_empresa.reset_index(), "semanal_filas": filas}


# --- H15-4: VaR y ES ------------------------------------------------------------------

def familia_riesgo(bloques, liquidos):
    hist_r, eval_r = bloques["rendimientos_log"]
    hs, es = log_a_simple(hist_r), log_a_simple(eval_r)
    series = {f"accion: {e}": (hs[e].dropna(), es[e].dropna()) for e in liquidos}
    universos = {"9_empresas": list(hs.columns), "liquidas": liquidos}
    for nombre_u, activos in universos.items():
        pesos, _ = construir_portafolios(hs[activos])     # procedimiento de la Fase 6
        for clave, w in pesos.items():
            r_h, _ = rendimiento_diario(hs[w.index], w)
            r_e, _ = rendimiento_diario(es[w.index], w)
            series[f"portafolio: {clave} ({nombre_u})"] = (r_h, r_e)
    res = evaluar_riesgo(series)
    return {"riesgo_backtesting": res["resumen"], "riesgo_mcs": res["mcs"]}


# --- H15-5: portafolios walk-forward -------------------------------------------------

def familia_portafolios(bloques, liquidos, ini_eval, fin_eval):
    rend = log_a_simple(pd.concat(bloques["rendimientos_log"]))
    tasas = pd.concat(bloques["tasas"])
    # Primer rebalanceo: último día bursátil del mes anterior a la evaluación.
    inicio = (pd.Timestamp(ini_eval).to_period("M") - 1).start_time.strftime("%Y-%m-%d")
    rf = fase14.tasa_diaria(tasas, rend.index[rend.index >= pd.Timestamp(inicio)])
    universos = {"9_empresas": (list(rend.columns), LIMITE_SECTOR), "liquidas": (liquidos, None)}
    periodos = {"evaluacion": (ini_eval, fin_eval)}
    for anio in sorted({d.year for d in rend.loc[ini_eval:fin_eval].index}):
        periodos[str(anio)] = (f"{anio}-01-01", f"{anio}-12-31")
    res = fase14.correr_backtesting(rend, rf, universos, inicio, fin_eval, periodos)
    return {"portafolios_metricas": res["metricas"], "portafolios_pruebas": res["pruebas"],
            "portafolios_rotacion": res["rotacion"], "portafolios_riqueza": res["riqueza"]}


# --- Ejecución --------------------------------------------------------------------------

def ejecutar_variante(bloques, carpeta):
    hist_r, eval_r = bloques["rendimientos_log"]
    fin_hist, ini_eval, fin_eval = hist_r.index.max(), eval_r.index.min(), eval_r.index.max()
    if not fin_hist < ini_eval:
        raise ValueError("Leakage: la evaluación no empieza después de la historia.")
    # Universo líquido fijado con ENTRENAMIENTO (DEC-020), en ambos modos.
    train = cargar_entrenamiento_validacion(RUTA_PARTICIONES, "rendimientos_log")["train"]
    liquidos, iliquidos, _ = seleccionar_universo_liquido(train)
    res = {}
    for nombre, f in (("H15-1", lambda: familia_media(bloques, iliquidos, fin_hist, fin_eval)),
                      ("H15-2", lambda: familia_varianza(bloques, liquidos, iliquidos)),
                      ("H15-3", lambda: familia_semanal(bloques, liquidos, fin_hist, fin_eval)),
                      ("H15-4", lambda: familia_riesgo(bloques, liquidos)),
                      ("H15-5", lambda: familia_portafolios(bloques, liquidos, ini_eval, fin_eval))):
        logger.info("Ejecutando %s ...", nombre)
        res.update(f())
    carpeta.mkdir(parents=True, exist_ok=True)
    for clave, df in res.items():
        df.to_csv(carpeta / f"{clave}.csv", index=False)
    return res


def _maximo_dif(a, b, claves):
    """Máxima diferencia absoluta entre columnas numéricas tras alinear por claves."""
    m = a.merge(b, on=claves, suffixes=("_a", "_b"))
    if len(m) != len(a) or len(m) != len(b):
        return np.inf
    cols = [c[:-2] for c in m.columns if c.endswith("_a")
            and pd.api.types.is_numeric_dtype(m[c]) and f"{c[:-2]}_b" in m.columns]
    if not cols:
        return 0.0
    return float(np.nanmax([np.nanmax(np.abs(m[f"{c}_a"].to_numpy(float) - m[f"{c}_b"].to_numpy(float)))
                            if m[f"{c}_a"].notna().any() else 0.0 for c in cols]))


def informe_reproduccion(res):
    """Compara el ensayo con los resultados oficiales de las Fases 7–14."""
    leer = lambda n: pd.read_csv(RUTA_RESULTADOS / n)
    filas = []

    def agregar(familia, archivo, dif, tol):
        filas.append({"familia": familia, "comparado_con": archivo, "max_dif": dif,
                      "tolerancia": tol, "reproduce": bool(dif <= tol)})

    agregar("H15-1", "fase10_media.csv",
            _maximo_dif(res["media"], leer("fase10_media.csv"), ["modelo"]), 1e-9)
    agregar("H15-2", "fase10_varianza_mcs.csv",
            _maximo_dif(res["varianza_mcs"], leer("fase10_varianza_mcs.csv"), ["universo", "modelo"]), 1e-9)
    agregar("H15-3", "semanal_volatilidad.csv",
            _maximo_dif(res["semanal_volatilidad"], leer("semanal_volatilidad.csv"), ["modelo"]), 1e-9)
    # Fase 6 se reestima: el optimizador SLSQP reproduce los pesos a ~1e-8.
    agregar("H15-4", "fase11_backtesting.csv",
            _maximo_dif(res["riesgo_backtesting"].drop(columns=["error"]),
                        leer("fase11_backtesting.csv").drop(columns=["error"]),
                        ["serie", "nivel", "metodo"]), 1e-6)
    # La Fase 14 empezó en 2021: en 2024 solo difiere el primer día (costo de
    # la compra inicial frente al del rebalanceo). Se comparan los rendimientos
    # diarios desde el segundo día de 2024 (pct_change deja NaN el primero).
    riq = leer("fase14_riqueza.csv").set_index("Date")
    riq.index = pd.to_datetime(riq.index)
    ens = res["portafolios_riqueza"].set_index("Date")
    ens.index = pd.to_datetime(ens.index)
    cols = [c for c in ens.columns if c != "ibr"]
    r_of = riq.loc["2024-01-01":, cols].pct_change().iloc[1:]
    r_en = ens[cols].pct_change().iloc[1:].loc[r_of.index]
    agregar("H15-5", "fase14_riqueza.csv (2024, desde el 2.º día)",
            float((r_of - r_en).abs().max().max()), 1e-10)
    return pd.DataFrame(filas)


def huellas_resultados(carpeta):
    return {str(p.relative_to(carpeta)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(carpeta.rglob("*.csv"))}


def ejecutar(modo):
    salida = RUTA_FASE15 / modo
    if modo == "final":
        rep = RUTA_FASE15 / "ensayo" / "reproduccion.csv"
        if not rep.exists() or not pd.read_csv(rep)["reproduce"].all():
            raise RuntimeError("El ensayo no existe o no reprodujo las Fases 7–14: "
                               "no se abre el bloque de prueba.")
        if salida.exists() and any(salida.iterdir()):
            raise FileExistsError(f"{salida} ya tiene resultados: la prueba se evalúa una sola vez.")
    bloques = cargar_bloques(modo)
    con_regla, detectadas = aplicar_regla(bloques)
    salida.mkdir(parents=True, exist_ok=True)
    detectadas.to_csv(salida / "fechas_detectadas.csv", index=False)
    logger.info("Fechas detectadas por la regla (%s): %s", modo,
                detectadas.to_dict("records") or "ninguna")

    res = ejecutar_variante(con_regla, salida / "con_regla")
    if not detectadas.empty:
        ejecutar_variante(bloques, salida / "sin_regla")
    if modo == "ensayo":
        informe = informe_reproduccion(res)
        informe.to_csv(salida / "reproduccion.csv", index=False)
        print(informe.to_string(index=False))
    meta = {"modo": modo, "ejecutado": datetime.now().isoformat(timespec="seconds"),
            "fechas_detectadas": [str(d.date()) for d in detectadas["fecha"]],
            "huellas": huellas_resultados(salida)}
    (salida / "huellas_resultados.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                                   encoding="utf-8")
    return res


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Fase 15: evaluación final (DEC-034).")
    parser.add_argument("--modo", choices=("ensayo", "final"), required=True)
    parser.add_argument("--confirmar", action="store_true",
                        help="Obligatorio en modo final: abre el bloque de prueba una sola vez.")
    args = parser.parse_args()
    if args.modo == "final" and not args.confirmar:
        parser.error("El modo final abre el bloque de prueba: use --confirmar.")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ejecutar(args.modo)
