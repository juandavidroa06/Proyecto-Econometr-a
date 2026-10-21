"""
fase21.py — Ejecución de la Fase 21: extensiones metodológicas (plan DEC-046)
=============================================================================

Bloque A (inferencia) y bloque B (portafolios con pronósticos), exactamente
como los fija DEC-046:

    - Principal: entrenamiento y validación (2020–2024), con los pronósticos
      y series ya publicados por las Fases 7–14.
    - Exploratorio: bloque de prueba (2025-01 a 2026-09), solo con los
      pronósticos publicados de la Fase 15 o con
      ``evaluacion_final.cargar_muestra_completa`` (único acceso a la prueba).

Resultados en ``resultados/fase21/validacion`` y
``resultados/fase21/exploratorio_prueba``.

Ejecutar:  python -m src.extensiones.fase21
"""

import logging

import numpy as np
import pandas as pd

from config.environment import RUTA_GRAFICOS, RUTA_PARTICIONES, RUTA_RESULTADOS
from config.settings import (
    EWMA_LAMBDA,
    FECHA_FIN_VALIDACION,
    LIMITE_SECTOR,
    SEMILLA_ALEATORIA,
)
from src.backtesting import fase14, motor
from src.comparacion import estadistica as est
from src.econometrics import garch
from src.extensiones import inferencia as inf
from src.extensiones import portafolios_pronostico as pp
from src.portfolio.fase6 import construir_portafolios
from src.portfolio.markowitz import log_a_simple, seleccionar_universo_liquido
from src.portfolio.metricas import rendimiento_diario
from src.preprocessing.split import cargar_entrenamiento_validacion
from src.riesgo import medidas
from src.riesgo.fase11 import NIVELES, construir_series

logger = logging.getLogger(__name__)

RUTA = RUTA_RESULTADOS / "fase21"
FASE15 = RUTA_RESULTADOS / "fase15" / "final" / "con_regla"
SPA = dict(n_remuestras=5000, bloque_medio=10, semilla=SEMILLA_ALEATORIA)
N_SIM_ES = 5000
MODELOS_MEDIA = ["cero", "arima", "random_forest", "gradient_boosting", "mlp", "lstm"]
MODELOS_DIRECCION = ["media_train", "arima", "random_forest", "gradient_boosting", "mlp", "lstm"]
MODELOS_SEMANAL = ["ewma", "garch", "random_forest", "gradient_boosting", "mlp"]
K_SENAL = {"9_empresas": 3, "liquidas": 2}
BOOT_B3 = dict(n_remuestras=2000, largo_bloque=10, semilla=SEMILLA_ALEATORIA)
COSTOS_B3 = {"20pb": 0.002, "0pb": 0.0}


def _liquidos():
    train = cargar_entrenamiento_validacion(RUTA_PARTICIONES, "rendimientos_log")["train"]
    liquidos, _, _ = seleccionar_universo_liquido(train)
    return liquidos


# --- A1: SPA ---------------------------------------------------------------------------

def _fila_spa(familia, referencia, perdidas, ref):
    r = inf.prueba_spa(perdidas[ref], perdidas.drop(columns=[ref]), **SPA)
    mejor = r["modelos"].iloc[0]
    return {"familia": familia, "referencia": ref, "n_fechas": r["n"],
            "modelos": ", ".join(perdidas.columns.drop(ref)),
            "mejor_modelo": mejor["modelo"], "mejora_media_mejor": mejor["mejora_media"],
            "estadistico": r["estadistico"],
            "pvalor_spa_consistente": r["pvalor_spa_consistente"],
            "pvalor_spa_inferior": r["pvalor_spa_inferior"],
            "pvalor_spa_superior": r["pvalor_spa_superior"],
            "pvalor_reality_check": r["pvalor_reality_check"],
            "algun_modelo_supera_5pct": r["pvalor_spa_consistente"] < 0.05}


def a1_media(pron):
    perd = pron[["fecha_objetivo"]].copy()
    for m in MODELOS_MEDIA + ["media_train"]:
        perd[m] = (pron["objetivo"] - pron[m]) ** 2
    por_fecha = perd.groupby("fecha_objetivo").mean().sort_index()
    return _fila_spa("A1.1 rendimiento diario", "media_train", por_fecha, "media_train")


def a1_varianza(pron, liquidos):
    d = pron[pron["empresa"].isin(liquidos)]
    proxy = (d["rendimiento"] * garch.ESCALA) ** 2
    perd = d[["Date"]].copy()
    for m in ("ewma", "garch", "constante"):
        h = d[f"varianza_{m}"]
        perd[m] = np.log(h) + proxy / h
    por_fecha = perd.groupby("Date").mean().sort_index()
    return _fila_spa("A1.2 varianza diaria (4 líquidas)", "ewma", por_fecha, "ewma")


def a1_semanal(pron):
    perd = pron[["fecha_objetivo"]].copy()
    for m in MODELOS_SEMANAL + ["har"]:
        perd[m] = np.log(pron[m]) + pron["rv_objetivo"] / pron[m]
    por_semana = perd.groupby("fecha_objetivo").mean().sort_index()
    return _fila_spa("A1.3 volatilidad semanal", "har", por_semana, "har")


# --- A2: dirección -----------------------------------------------------------------------

def a2_direccion(pron):
    filas = []
    for m in MODELOS_DIRECCION:
        hac = inf.direccional_hac(pron["fecha_objetivo"], pron["objetivo"], pron[m])
        pt = est.pesaran_timmermann(pron["objetivo"], pron[m])
        filas.append({"modelo": m, "acierto": hac["acierto"], "n": hac["n"],
                      "fechas": hac["fechas"], "pt_original_pvalor": pt["pt_pvalor"],
                      "hac_estadistico": hac["estadistico"], "hac_pvalor": hac["pvalor"]})
    t = pd.DataFrame(filas)
    t["pt_original_pvalor_holm"] = est.holm(t["pt_original_pvalor"]).to_numpy()
    t["hac_pvalor_holm"] = est.holm(t["hac_pvalor"]).to_numpy()
    t["significativa_hac_holm_5pct"] = t["hac_pvalor_holm"] < 0.05
    return t


# --- A3: Expected Shortfall -------------------------------------------------------------

def _simulador(metodo, train, valid):
    """Función rng, n -> (n, T) con la distribución predictiva del método."""
    T = len(valid)
    if metodo == "ewma_normal":
        _, sigma = medidas._sigma_ewma(train, valid, EWMA_LAMBDA)
        s = sigma.to_numpy()
        return lambda rng, n: rng.standard_normal((n, T)) * s
    if metodo == "fhs":
        sigma_tr, sigma = medidas._sigma_ewma(train, valid, EWMA_LAMBDA)
        z = (train / sigma_tr).to_numpy()
        s = sigma.to_numpy()
        return lambda rng, n: z[rng.integers(0, len(z), (n, T))] * s
    if metodo == "historica":
        completa = pd.concat([train, valid]).to_numpy()
        n_tr = len(train)
        ventanas = np.stack([completa[n_tr + i - 250:n_tr + i] for i in range(T)], axis=1)
        return lambda rng, n: ventanas[rng.integers(0, 250, (n, T)), np.arange(T)]
    if metodo == "garch_t":
        res = garch.ajustar_garch(train, valid, "t")
        if res.convergence_flag != 0:
            raise RuntimeError("El GARCH no convergió.")
        s = (np.sqrt(garch.pronostico_varianza_un_paso(res, train, valid)) / garch.ESCALA).to_numpy()
        nu = float(res.params["nu"])
        if nu <= 2:
            raise ValueError(f"nu = {nu:.3f} <= 2")
        escala = np.sqrt((nu - 2) / nu)
        return lambda rng, n: rng.standard_t(nu, (n, T)) * escala * s
    raise ValueError(f"Método desconocido: {metodo!r}")


def a3_es(series):
    filas = []
    for nombre, (train, valid) in series.items():
        for nivel, alfa in NIVELES.items():
            for metodo in medidas.METODOS:
                try:
                    m = medidas.calcular(metodo, train, valid, alfa)
                    r = inf.acerbi_szekely_z2(valid.to_numpy(), m["var"].to_numpy(),
                                              m["es"].to_numpy(), alfa,
                                              _simulador(metodo, train, valid),
                                              N_SIM_ES, SEMILLA_ALEATORIA)
                except (RuntimeError, ValueError) as exc:
                    logger.warning("%s | %s | %s: %s", nombre, nivel, metodo, exc)
                    filas.append({"serie": nombre, "nivel": nivel, "metodo": metodo,
                                  "error": str(exc)})
                    continue
                filas.append({"serie": nombre, "nivel": nivel, "metodo": metodo, "error": "",
                              "n": len(valid), "excesos": int((valid < -m["var"]).sum()), **r})
    t = pd.DataFrame(filas)
    ok = t["error"] == ""
    t.loc[ok, "pvalor_holm"] = est.holm(t.loc[ok, "pvalor"]).to_numpy()
    t["rechaza_holm_5pct"] = t["pvalor_holm"] < 0.05
    resumen = (t[ok].groupby(["nivel", "metodo"])
               .agg(z2_medio=("z2", "mean"), rechazos_sin_corregir=("pvalor", lambda p: int((p < 0.05).sum())),
                    rechazos_holm=("rechaza_holm_5pct", "sum"), series=("z2", "size"))
               .reset_index())
    return t, resumen


def series_riesgo_prueba(muestra):
    """Las 10 series de la Fase 11 con historia 2020–2024 y evaluación 2025–2026
    (como la familia H15-4 de la evaluación final)."""
    rl = muestra["rendimientos_log"]
    hist, ev = rl.loc[:FECHA_FIN_VALIDACION], rl.loc[pd.Timestamp(FECHA_FIN_VALIDACION) + pd.Timedelta(days=1):]
    hs, es = log_a_simple(hist), log_a_simple(ev)
    liquidos = _liquidos()
    series = {f"accion: {e}": (hs[e].dropna(), es[e].dropna()) for e in liquidos}
    for nombre_u, activos in {"9_empresas": list(hs.columns), "liquidas": liquidos}.items():
        pesos, _ = construir_portafolios(hs[activos])
        for clave, w in pesos.items():
            r_h, _ = rendimiento_diario(hs[w.index], w)
            r_e, _ = rendimiento_diario(es[w.index], w)
            series[f"portafolio: {clave} ({nombre_u})"] = (r_h, r_e)
    return series


# --- A4 y B: Sharpe ------------------------------------------------------------------------

def a4_sharpe(series, rf, referencia="igual"):
    """PSR/DSR de cada serie neta y pruebas de diferencia de Sharpe frente a ``referencia``.

    ``series``: {(universo, estrategia): Series de rendimiento neto diario}.
    """
    excesos = {k: (s - rf.reindex(s.index)).dropna() for k, s in series.items()}
    sharpes = [x.mean() / x.std(ddof=1) for x in excesos.values()]
    filas, pruebas = [], []
    for (u, e), x in excesos.items():
        filas.append({"universo": u, "estrategia": e, "dias": len(x),
                      "sharpe_anual": float(x.mean() / x.std(ddof=1) * np.sqrt(252)),
                      "psr_0": inf.sharpe_probabilistico(x),
                      "dsr": inf.sharpe_deflactado(x, sharpes), "n_estrategias_familia": len(sharpes)})
        if e != referencia and (u, referencia) in excesos:
            b = excesos[(u, referencia)]
            comunes = x.index.intersection(b.index)
            hac = inf.diferencia_sharpe_hac(x.loc[comunes], b.loc[comunes])
            pruebas.append({"universo": u, "estrategia": e, "referencia": referencia,
                            "dif_sharpe_hac": hac["dif_sharpe"], "ee_hac": hac["error_estandar"],
                            "pvalor_hac": hac["pvalor"]})
    pruebas = pd.DataFrame(pruebas)
    if len(pruebas):
        pruebas["pvalor_hac_holm"] = est.holm(pruebas["pvalor_hac"]).to_numpy()
    return pd.DataFrame(filas), pruebas


def _series_desde_riqueza(riqueza):
    r = riqueza.set_index("Date")
    r.index = pd.to_datetime(r.index)
    netos = r.pct_change()
    netos.iloc[0] = r.iloc[0] - 1
    return {tuple(c.split("|")): netos[c] for c in r.columns if c != "ibr"}


def _pruebas_bootstrap(series, rf, referencia, boot):
    filas = []
    for (u, e), s in series.items():
        if e == referencia:
            continue
        base = series[(u, referencia)]
        comunes = s.index.intersection(base.index)
        d = motor.diferencia_sharpe((s - rf.reindex(s.index)).loc[comunes],
                                    (base - rf.reindex(base.index)).loc[comunes], **boot)
        filas.append({"universo": u, "estrategia": e, "referencia": referencia, **d})
    t = pd.DataFrame(filas)
    t["pvalor_holm"] = est.holm(t["pvalor"]).to_numpy()
    t["significativa_5pct"] = t["pvalor_holm"] < 0.05
    return t


# --- B1–B2 ---------------------------------------------------------------------------------

def universos_b12(columnas, liquidos):
    return {"9_empresas": (list(columnas), LIMITE_SECTOR,
                           ["igual", "min_var_ewma", "paridad_riesgo_ewma", "vol_target_1n"]),
            "liquidas": (liquidos, None, ["igual", "min_var_ewma", "paridad_riesgo_ewma",
                                          "min_var_ccc_garch", "vol_target_1n"])}


def ejecutar_b12(rend, rf, inicio, fin, periodos):
    res = pp.correr_b12(rend, rf, universos_b12(rend.columns, _liquidos()), inicio, fin,
                        periodos, fase14.COSTOS)
    principales = {(u, e): s for (u, e, c), s in res["series"].items() if c == fase14.COSTO_PRINCIPAL}
    res["pruebas"] = _pruebas_bootstrap(principales, rf, "igual", fase14.BOOT)
    res["sharpe"], hac = a4_sharpe(principales, rf)
    res["pruebas"] = res["pruebas"].merge(hac, on=["universo", "estrategia", "referencia"])
    return res


# --- B3 ------------------------------------------------------------------------------------

def ejecutar_b3(pron, rf, liquidos):
    pron = pron.copy()
    pron["fecha_objetivo"] = pd.to_datetime(pron["fecha_objetivo"])
    universos = {"9_empresas": pron, "liquidas": pron[pron["empresa"].isin(liquidos)]}
    filas, series = [], {}
    for u, d in universos.items():
        for nombre_c, c in COSTOS_B3.items():
            base, rot_b = pp.simular_senales(d, None, K_SENAL[u], c)
            series[(u, "igual_diario", nombre_c)] = base
            filas.append({"universo": u, "estrategia": "igual_diario", "costo": nombre_c,
                          "rotacion_media": rot_b, **motor.metricas(base, rf)})
            for m in MODELOS_DIRECCION:
                neto, rot = pp.simular_senales(d, m, K_SENAL[u], c)
                series[(u, f"top{K_SENAL[u]}_{m}", nombre_c)] = neto
                filas.append({"universo": u, "estrategia": f"top{K_SENAL[u]}_{m}",
                              "costo": nombre_c, "rotacion_media": rot,
                              **motor.metricas(neto, rf)})
    principales = {(u, e): s for (u, e, c), s in series.items() if c == "20pb"}
    pruebas = _pruebas_bootstrap(principales, rf, "igual_diario", BOOT_B3)
    sharpe, hac = a4_sharpe(principales, rf, "igual_diario")
    pruebas = pruebas.merge(hac, on=["universo", "estrategia", "referencia"])
    return {"metricas": pd.DataFrame(filas), "pruebas": pruebas, "sharpe": sharpe,
            "equilibrio": costo_equilibrio(universos, rf)}


def costo_equilibrio(universos, rf, maximo=0.01):
    """DESCRIPTIVO (no registrado en DEC-046): costo por lado con el que el Sharpe
    neto de cada señal iguala al del 1/N diario con ese mismo costo (bisección).
    NaN si la señal no supera al 1/N ni sin costos."""
    def sharpe(d, m, k, c):
        neto, _ = pp.simular_senales(d, m, k, c)
        x = neto - rf.reindex(neto.index)
        return x.mean() / x.std(ddof=1)

    filas = []
    for u, d in universos.items():
        k = K_SENAL[u]
        for m in MODELOS_DIRECCION:
            brecha = lambda c: sharpe(d, m, k, c) - sharpe(d, None, k, c)
            if brecha(0.0) <= 0:
                eq = np.nan
            elif brecha(maximo) > 0:
                eq = np.inf
            else:
                lo, hi = 0.0, maximo
                for _ in range(30):
                    mid = (lo + hi) / 2
                    lo, hi = (mid, hi) if brecha(mid) > 0 else (lo, mid)
                eq = (lo + hi) / 2
            filas.append({"universo": u, "estrategia": f"top{k}_{m}",
                          "costo_equilibrio_pb": eq * 1e4 if np.isfinite(eq) else eq,
                          "nota": "descriptivo, no registrado en DEC-046"})
    return pd.DataFrame(filas)


# --- Ejecución -------------------------------------------------------------------------------

def _guardar(carpeta, res):
    carpeta.mkdir(parents=True, exist_ok=True)
    for nombre, df in res.items():
        df.to_csv(carpeta / f"{nombre}.csv", index=False)


def principal():
    """Todo lo calculado con entrenamiento y validación (2020–2024)."""
    liquidos = _liquidos()
    leer = lambda n: pd.read_csv(RUTA_RESULTADOS / n)
    res = {}
    pron9 = leer("fase9_pronosticos_validacion.csv")
    res["a1_spa"] = pd.DataFrame([a1_media(pron9),
                                  a1_varianza(leer("fase7_pronosticos_validacion.csv"), liquidos),
                                  a1_semanal(leer("semanal_pronosticos.csv"))])
    res["a2_direccion"] = a2_direccion(pron9)
    res["a3_es"], res["a3_es_resumen"] = a3_es(construir_series())

    rend_log = cargar_entrenamiento_validacion(RUTA_PARTICIONES, "rendimientos_log")
    tasas = cargar_entrenamiento_validacion(RUTA_PARTICIONES, "tasas")
    rend = log_a_simple(pd.concat([rend_log["train"], rend_log["validacion"]]))
    rf = fase14.tasa_diaria(pd.concat([tasas["train"], tasas["validacion"]]),
                            rend.index[rend.index >= pd.Timestamp(fase14.INICIO_PRIMER_REBALANCEO)])
    f14 = _series_desde_riqueza(leer("fase14_riqueza.csv"))
    res["a4_sharpe_fase14"], res["a4_pruebas_fase14"] = a4_sharpe(f14, rf)

    b12 = ejecutar_b12(rend, rf, fase14.INICIO_PRIMER_REBALANCEO, FECHA_FIN_VALIDACION,
                       fase14.PERIODOS)
    # Control: el 1/N de B1–B2 debe ser idéntico al de la Fase 14.
    for u in ("9_empresas", "liquidas"):
        dif = (b12["series"][(u, "igual", "20pb")] - f14[(u, "igual")]).abs().max()
        if not dif < 1e-12:
            raise RuntimeError(f"El 1/N de B1–B2 no reproduce la Fase 14 ({u}: {dif:.2e}).")
    res.update({f"b12_{k}": v for k, v in b12.items() if k != "series"})

    pron_val = pron9.copy()
    rf_b3 = fase14.tasa_diaria(pd.concat([tasas["train"], tasas["validacion"]]),
                               pd.DatetimeIndex(pd.to_datetime(pron_val["fecha_objetivo"].unique())))
    res.update({f"b3_{k}": v for k, v in ejecutar_b3(pron_val, rf_b3, liquidos).items()})
    return res, b12["series"]


def exploratorio():
    """Lo mismo en el bloque de prueba ya abierto (EXPLORATORIO)."""
    from src.evaluacion_final import cargar_muestra_completa

    liquidos = _liquidos()
    res = {}
    pron = pd.read_csv(FASE15 / "media_pronosticos.csv")
    res["a1_spa"] = pd.DataFrame([a1_media(pron),
                                  a1_varianza(pd.read_csv(FASE15 / "varianza_pronosticos.csv"), liquidos)])
    res["a2_direccion"] = a2_direccion(pron)

    muestra, _ = cargar_muestra_completa()
    res["a3_es"], res["a3_es_resumen"] = a3_es(series_riesgo_prueba(muestra))

    rend = log_a_simple(muestra["rendimientos_log"])
    ini_eval = rend.loc[pd.Timestamp(FECHA_FIN_VALIDACION) + pd.Timedelta(days=1):].index.min()
    fin_eval = rend.index.max()
    inicio = (ini_eval.to_period("M") - 1).start_time.strftime("%Y-%m-%d")
    rf = fase14.tasa_diaria(muestra["tasas"], rend.index[rend.index >= pd.Timestamp(inicio)])
    f15 = _series_desde_riqueza(pd.read_csv(FASE15 / "portafolios_riqueza.csv"))
    res["a4_sharpe_fase15"], res["a4_pruebas_fase15"] = a4_sharpe(f15, rf)

    periodos = {"evaluacion": (ini_eval, fin_eval), "2025": ("2025-01-01", "2025-12-31"),
                "2026": ("2026-01-01", "2026-12-31")}
    b12 = ejecutar_b12(rend, rf, inicio, fin_eval, periodos)
    for u in ("9_empresas", "liquidas"):
        dif = (b12["series"][(u, "igual", "20pb")] - f15[(u, "igual")]).abs().max()
        if not dif < 1e-12:
            raise RuntimeError(f"El 1/N de B1–B2 no reproduce la Fase 15 ({u}: {dif:.2e}).")
    res.update({f"b12_{k}": v for k, v in b12.items() if k != "series"})

    rf_b3 = fase14.tasa_diaria(muestra["tasas"],
                               pd.DatetimeIndex(pd.to_datetime(pron["fecha_objetivo"].unique())))
    res.update({f"b3_{k}": v for k, v in ejecutar_b3(pron, rf_b3, liquidos).items()})
    return res, b12["series"]


def ejecutar_fase21(guardar=True):
    res_v, series_v = principal()
    res_p, series_p = exploratorio()
    if guardar:
        _guardar(RUTA / "validacion", res_v)
        _guardar(RUTA / "exploratorio_prueba", res_p)
        _graficar(series_v, series_p)
    return res_v, res_p


def _graficar(series_v, series_p):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    RUTA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    estilos = {"igual": ("black", "-"), "min_var_ewma": ("tab:blue", "-"),
               "paridad_riesgo_ewma": ("tab:green", "-."), "min_var_ccc_garch": ("tab:purple", "--"),
               "vol_target_1n": ("tab:orange", "-")}
    fig, ejes = plt.subplots(2, 2, figsize=(15, 9))
    for fila, (series, titulo) in enumerate(((series_v, "2021–2024 (principal)"),
                                              (series_p, "2025–2026 (exploratorio)"))):
        for col, u in enumerate(("9_empresas", "liquidas")):
            eje = ejes[fila, col]
            for e, (c, ls) in estilos.items():
                s = series.get((u, e, "20pb"))
                if s is not None:
                    eje.plot(s.index, (1 + s).cumprod(), color=c, ls=ls, lw=1.2, label=e)
            eje.set_title(f"{u} — {titulo}, 20 pb", fontsize=9)
            eje.set_ylabel("Valor de 1 peso")
            eje.legend(fontsize=7)
    fig.suptitle("Fase 21: portafolios con pronósticos de covarianza y volatilidad frente al 1/N",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(RUTA_GRAFICOS / "fase21_portafolios.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    rv, rp = ejecutar_fase21()
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    for titulo, r in (("PRINCIPAL (2020–2024)", rv), ("EXPLORATORIO (prueba)", rp)):
        print(f"\n===== {titulo} =====")
        for k, v in r.items():
            print(f"\n--- {k} ---")
            print(v.round(4).to_string(index=False))
