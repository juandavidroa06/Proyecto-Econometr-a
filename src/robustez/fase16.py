"""
fase16.py — Análisis de robustez EXPLORATORIO (plan DEC-037, resultados DEC-038)
=================================================================================

Usa la muestra completa 2020-01 a 2026-09 (la prueba ya se evaluó en la
Fase 15) mediante ``evaluacion_final.cargar_muestra_completa``.

    R1  Portafolios: 27 configuraciones (ventana x peso máximo x universo).
    R2  Volatilidad diaria y VaR 99 % por año 2021–2026 (historia expansiva).
    R3  Rendimiento diario por año 2021–2026 (ARIMA, RF, GB frente a la media).

Ejecutar:  python -m src.robustez.fase16
"""

import itertools
import logging

import numpy as np
import pandas as pd

from config.environment import RUTA_GRAFICOS, RUTA_PARTICIONES, RUTA_RESULTADOS
from config.settings import ARIMA_CRITERIO, ARIMA_MAX_P, ARIMA_MAX_Q, LIMITE_SECTOR, SEMILLA_ALEATORIA
from src.backtesting import fase14, motor
from src.comparacion import estadistica as est
from src.econometrics import arima, evaluacion, garch
from src.evaluacion_final import cargar_muestra_completa
from src.machine_learning import modelos, variables
from src.machine_learning.fase8 import matriz_variables
from src.optimizacion import optimizadores as opt
from src.portfolio.markowitz import log_a_simple, seleccionar_universo_liquido
from src.preprocessing.split import cargar_entrenamiento_validacion
from src.riesgo import backtesting as bt
from src.riesgo import medidas

logger = logging.getLogger(__name__)

RUTA = RUTA_RESULTADOS / "fase16"
ANIOS = list(range(2021, 2027))
VENTANAS = (126, 252, 504)
PESOS_MAX = (0.20, 0.30, 0.50)
PERIODOS = {"2021-2023": ("2021-01-01", "2023-12-31"), "2024": ("2024-01-01", "2024-12-31"),
            "2025-2026": ("2025-01-01", "2026-12-31"), "total": ("2021-01-01", "2026-12-31")}
LAMBDAS = (0.90, 0.94, 0.97)
BOOT = dict(n_remuestras=2000, largo_bloque=10, semilla=SEMILLA_ALEATORIA)


# --- R1: portafolios ------------------------------------------------------------------

def r1_portafolios(datos, liquidos):
    rend = log_a_simple(datos["rendimientos_log"])
    fin = rend.index.max()
    todas = list(rend.columns)
    universos = {"9_empresas": (todas, LIMITE_SECTOR), "liquidas": (liquidos, None),
                 "7_sin_ETB_Nutresa": ([e for e in todas if e not in ("ETB", "Nutresa")],
                                       LIMITE_SECTOR)}
    filas, omitidas = [], []
    for ventana, peso_max, (nombre_u, (activos, limite)) in itertools.product(
            VENTANAS, PESOS_MAX, universos.items()):
        config = {"ventana": ventana, "peso_max": peso_max, "universo": nombre_u}
        try:
            opt.Restricciones(activos, peso_max).punto_inicial()
        except ValueError as exc:
            omitidas.append({**config, "motivo": str(exc)})
            continue
        # Primer rebalanceo: fin de mes con al menos ``ventana`` días de historia
        # y no antes de diciembre de 2020.
        pos_min = rend.index[ventana - 1]
        inicio = max(pd.Timestamp("2020-12-01"), pos_min.to_period("M").start_time)
        fechas = motor.fechas_rebalanceo(rend.index, inicio, fin, "M")
        if fechas[0] < pos_min:
            inicio = (fechas[0].to_period("M") + 1).start_time
        rf = fase14.tasa_diaria(datos["tasas"], rend.index[rend.index >= inicio])
        primer_dia = rend.index[rend.index > motor.fechas_rebalanceo(rend.index, inicio, fin, "M")[0]][0]
        periodos = {k: (max(pd.Timestamp(a), primer_dia), pd.Timestamp(b))
                    for k, (a, b) in PERIODOS.items() if pd.Timestamp(b) >= primer_dia}
        res = fase14.correr_backtesting(rend, rf, {nombre_u: (activos, limite)}, inicio, fin,
                                        periodos, ventana=ventana, peso_max=peso_max)
        m = res["metricas"]
        m = m[(m["frecuencia"] == "mensual") & (m["costo"] == fase14.COSTO_PRINCIPAL)]
        for _, fila in m.iterrows():
            filas.append({**config, "inicio_backtesting": primer_dia.date(),
                          "estrategia": fila["estrategia"], "periodo": fila["periodo"],
                          "sharpe": fila["sharpe"], "retorno_anual": fila["retorno_anual"],
                          "volatilidad_anual": fila["volatilidad_anual"],
                          "max_drawdown": fila["max_drawdown"]})
        logger.info("R1 %s listo", config)
    tabla = pd.DataFrame(filas)
    base = tabla[tabla["estrategia"] == "igual"][["ventana", "peso_max", "universo", "periodo", "sharpe"]]
    tabla = tabla.merge(base.rename(columns={"sharpe": "sharpe_1n"}),
                        on=["ventana", "peso_max", "universo", "periodo"])
    tabla["supera_1n"] = tabla["sharpe"] > tabla["sharpe_1n"]
    return tabla, pd.DataFrame(omitidas)


# --- R2: volatilidad y VaR por año ----------------------------------------------------------

def r2_volatilidad(datos, liquidos):
    r = datos["rendimientos_log"]
    perdidas, var_filas = [], []
    for anio, e in itertools.product(ANIOS, liquidos):
        s = r[e].dropna()
        hist, ev = s[s.index < f"{anio}-01-01"], s[(s.index.year == anio)]
        res = garch.ajustar_garch(hist, ev, "t")
        pron = {"garch": garch.pronostico_varianza_un_paso(res, hist, ev),
                "constante": garch.varianza_constante(hist, ev)}
        for lam in LAMBDAS:
            pron[f"ewma_{lam:.2f}"] = garch.varianza_ewma(hist, ev, lam)
        proxy = (ev * garch.ESCALA) ** 2
        d = pd.DataFrame({m: np.log(h) + proxy / h for m, h in pron.items()})
        d["anio"], d["empresa"], d["garch_convergio"] = anio, e, res.convergence_flag == 0
        perdidas.append(d.rename_axis("Date").reset_index())
        hs, es = log_a_simple(hist), log_a_simple(ev)
        for metodo in medidas.METODOS:
            try:
                m = medidas.calcular(metodo, hs, es, 0.01)
            except (ValueError, RuntimeError) as exc:
                var_filas.append({"anio": anio, "empresa": e, "metodo": metodo, "error": str(exc)})
                continue
            ex = bt.excesos(es, m["var"])
            var_filas.append({"anio": anio, "empresa": e, "metodo": metodo, "error": "",
                              "n": len(es), "excesos": int(ex.sum()), "esperados": 0.01 * len(es),
                              "perdida_sobre_es": bt.prueba_es(es, m["var"], m["es"])["perdida_sobre_es"]})
    perdidas = pd.concat(perdidas, ignore_index=True)
    modelos_v = ["garch", "constante"] + [f"ewma_{l:.2f}" for l in LAMBDAS]
    mcs = []
    for anio, g in perdidas.groupby("anio"):
        por_fecha = g.groupby("Date")[modelos_v].mean()
        t = est.model_confidence_set(por_fecha, alfa=0.10, **BOOT)
        t.insert(0, "anio", anio)
        mcs.append(t)
    return pd.concat(mcs, ignore_index=True), pd.DataFrame(var_filas), perdidas


# --- R3: rendimiento por año -------------------------------------------------------------------

def r3_rendimiento(datos):
    rend, vol, ext = datos["rendimientos_log"], datos["volumen"], datos["externos"]
    panel = variables.construir_panel(rend, vol, ext)
    columnas = variables.columnas_variables(panel)
    empresas = list(rend.columns)
    filas, pruebas = [], []
    for anio in ANIOS:
        fin_hist, fin_eval = pd.Timestamp(f"{anio - 1}-12-31"), pd.Timestamp(f"{anio}-12-31")
        hist_r = rend[rend.index <= fin_hist]
        train, valid, _ = variables.separar(panel, fin_hist, fin_eval)
        X_tr = matriz_variables(train, columnas, empresas)
        X_va = matriz_variables(valid, columnas, empresas)
        comp = valid[["fecha_objetivo", "empresa", "objetivo"]].copy()
        for tipo in ("random_forest", "gradient_boosting"):
            mejores, _ = modelos.validacion_cruzada(tipo, X_tr, train["objetivo"], train["Date"])
            comp[tipo] = modelos.ajustar_final(tipo, mejores, X_tr, train["objetivo"]).predict(X_va)
        comp["media"] = comp["empresa"].map(hist_r.mean())
        comp["cero"] = 0.0
        ar = []
        for e in empresas:
            h = hist_r[e].dropna()
            ev = rend[e][(rend.index > fin_hist) & (rend.index <= fin_eval)].dropna()
            orden, _ = arima.seleccionar_orden(h, ARIMA_MAX_P, ARIMA_MAX_Q, ARIMA_CRITERIO)
            res, _ = arima.ajustar_arima(h, orden)
            p = arima.pronostico_un_paso(h, ev, res)
            ar.append(pd.DataFrame({"fecha_objetivo": p.index, "empresa": e, "arima": p.to_numpy()}))
        comp = comp.merge(pd.concat(ar), on=["fecha_objetivo", "empresa"], how="inner")
        perd = pd.DataFrame({m: (comp["objetivo"] - comp[m]) ** 2
                             for m in ("arima", "random_forest", "gradient_boosting", "media", "cero")})
        por_fecha = perd.groupby(comp["fecha_objetivo"]).mean()
        familia = []
        for m in ("arima", "random_forest", "gradient_boosting"):
            dm = evaluacion.diebold_mariano(por_fecha[m], por_fecha["media"])
            r2 = 1 - por_fecha[m].sum() / por_fecha["media"].sum()
            familia.append({"anio": anio, "modelo": m, "n_filas": len(comp), "r2_os_vs_media": r2,
                            "dm_estadistico": dm["dm_estadistico"], "pvalor": dm["dm_pvalor"]})
        familia = pd.DataFrame(familia)
        familia["pvalor_holm"] = est.holm(familia["pvalor"]).to_numpy()
        familia["mejor_que_media_holm_5pct"] = (familia["pvalor_holm"] < 0.05) & (familia["dm_estadistico"] < 0)
        pruebas.append(familia)
        logger.info("R3 %d listo", anio)
    return pd.concat(pruebas, ignore_index=True)


# --- Ejecución ------------------------------------------------------------------------------------

def ejecutar_fase16(guardar=True):
    datos, detectadas = cargar_muestra_completa()
    train = cargar_entrenamiento_validacion(RUTA_PARTICIONES, "rendimientos_log")["train"]
    liquidos, _, _ = seleccionar_universo_liquido(train)
    r1, omitidas = r1_portafolios(datos, liquidos)
    r2_mcs, r2_var, _ = r2_volatilidad(datos, liquidos)
    r3 = r3_rendimiento(datos)
    res = {"r1_portafolios": r1, "r1_omitidas": omitidas, "r2_mcs_volatilidad": r2_mcs,
           "r2_var99": r2_var, "r3_rendimiento": r3, "fechas_regla": detectadas}
    if guardar:
        RUTA.mkdir(parents=True, exist_ok=True)
        for clave, df in res.items():
            df.to_csv(RUTA / f"{clave}.csv", index=False)
        _graficar_r1(r1)
    return res


def _graficar_r1(r1):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    d = r1[(r1["periodo"] == "total") & (r1["estrategia"] != "igual")].copy()
    d["dif"] = d["sharpe"] - d["sharpe_1n"]
    d["config"] = (d["universo"] + " | v" + d["ventana"].astype(str)
                   + " | máx " + (d["peso_max"] * 100).astype(int).astype(str) + "%")
    tabla = d.pivot_table(index="config", columns="estrategia", values="dif")
    fig, eje = plt.subplots(figsize=(9, max(4, 0.32 * len(tabla))))
    lim = np.nanmax(np.abs(tabla.to_numpy()))
    im = eje.imshow(tabla.to_numpy(), cmap="RdBu", vmin=-lim, vmax=lim, aspect="auto")
    eje.set_xticks(range(len(tabla.columns)), tabla.columns, rotation=30, ha="right", fontsize=8)
    eje.set_yticks(range(len(tabla.index)), tabla.index, fontsize=7)
    for i in range(tabla.shape[0]):
        for j in range(tabla.shape[1]):
            v = tabla.iat[i, j]
            if np.isfinite(v):
                eje.text(j, i, f"{v:+.2f}", ha="center", va="center", fontsize=6)
    fig.colorbar(im, ax=eje, label="Sharpe estrategia − Sharpe 1/N (azul = supera al 1/N)")
    eje.set_title("Fase 16 (exploratoria): robustez de 'ninguna estrategia supera al 1/N'\n"
                  "Sharpe neto total 2021–2026, rebalanceo mensual, 20 pb", fontsize=9)
    fig.tight_layout()
    RUTA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    fig.savefig(RUTA_GRAFICOS / "fase16_robustez_portafolios.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ejecutar_fase16()
