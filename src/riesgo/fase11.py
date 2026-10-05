"""
fase11.py — Ejecución de la Fase 11: estimación y validación del riesgo
========================================================================

Flujo (DEC-028):
    1. Carga SOLO entrenamiento y validación de rendimientos log y los
       convierte a simples.
    2. Series: las 4 acciones líquidas (según train) y los 6 portafolios de
       la Fase 6 (pesos fijos estimados con train).
    3. Para cada serie, método y nivel (95 %, 99 %): VaR y ES a un día en
       validación con información hasta el día anterior.
    4. Backtesting: Kupiec, Christoffersen, zona de Basilea (99 %), prueba
       de ES, pérdida cuantílica; Holm sobre la cobertura condicional y MCS
       de la pérdida cuantílica entre métodos.

No toca el bloque de prueba.

Ejecutar:  python -m src.riesgo.fase11
"""

import logging

import numpy as np
import pandas as pd

from config.environment import RUTA_GRAFICOS, RUTA_PARTICIONES, RUTA_RESULTADOS
from config.settings import SEMILLA_ALEATORIA
from src.comparacion import estadistica as est
from src.portfolio.markowitz import log_a_simple, seleccionar_universo_liquido
from src.portfolio.metricas import rendimiento_diario
from src.preprocessing.split import cargar_entrenamiento_validacion
from src.riesgo import backtesting as bt
from src.riesgo import medidas

logger = logging.getLogger(__name__)

NIVELES = {"95%": 0.05, "99%": 0.01}


def construir_series():
    """Dict {nombre: (train, validacion)} de rendimientos simples sin NaN."""
    datos = cargar_entrenamiento_validacion(RUTA_PARTICIONES, "rendimientos_log")
    tr, va = log_a_simple(datos["train"]), log_a_simple(datos["validacion"])
    liquidos, _, _ = seleccionar_universo_liquido(datos["train"])
    series = {f"accion: {e}": (tr[e].dropna(), va[e].dropna()) for e in liquidos}

    pesos = pd.read_csv(RUTA_RESULTADOS / "fase6_pesos.csv")
    for (universo, portafolio), g in pesos.groupby(["universo", "portafolio"], sort=False):
        w = g.set_index("empresa")["peso"]
        r_tr, _ = rendimiento_diario(tr[w.index], w)
        r_va, _ = rendimiento_diario(va[w.index], w)
        series[f"portafolio: {portafolio} ({universo})"] = (r_tr, r_va)
    return series


def ejecutar_fase11(guardar=True):
    series = construir_series()
    pron, filas = [], []
    for nombre, (train, valid) in series.items():
        for nivel, alfa in NIVELES.items():
            for metodo in medidas.METODOS:
                try:
                    m = medidas.calcular(metodo, train, valid, alfa)
                except (RuntimeError, ValueError) as exc:
                    # Error de datos/modelo (p. ej. GARCH sin converger): se
                    # registra y la combinación queda fuera, no se inventa.
                    logger.warning("%s | %s | %s: %s", nombre, nivel, metodo, exc)
                    filas.append({"serie": nombre, "nivel": nivel, "metodo": metodo,
                                  "error": str(exc)})
                    continue
                ex = bt.excesos(valid, m["var"])
                kup = bt.kupiec(ex, alfa)
                chr_ = bt.christoffersen(ex, alfa)
                pes = bt.prueba_es(valid, m["var"], m["es"])
                tick = bt.perdida_cuantilica(valid, m["var"], alfa)
                filas.append({
                    "serie": nombre, "nivel": nivel, "metodo": metodo, "error": "",
                    "n": len(valid), "excesos": int(ex.sum()),
                    "excesos_esperados": alfa * len(valid),
                    "tasa_excesos": float(ex.mean()),
                    "pvalor_kupiec": kup[1], "pvalor_independencia": chr_["pvalor_ind"],
                    "pvalor_cc": chr_["pvalor_cc"],
                    "zona_basilea": bt.zona_basilea(int(ex.sum()), len(valid))
                    if nivel == "99%" else "",
                    "var_medio": float(m["var"].mean()), "es_medio": float(m["es"].mean()),
                    "perdida_sobre_es": pes["perdida_sobre_es"], "pvalor_es": pes["pvalor_es"],
                    "perdida_cuantilica": float(tick.mean()),
                })
                pron.append(pd.DataFrame({"serie": nombre, "nivel": nivel, "metodo": metodo,
                                          "rendimiento": valid, "var": m["var"],
                                          "es": m["es"], "exceso": ex,
                                          "perdida_cuantilica": tick}))
    resumen = pd.DataFrame(filas)
    ok = resumen["error"] == ""
    resumen.loc[ok, "pvalor_cc_holm"] = est.holm(resumen.loc[ok, "pvalor_cc"]).to_numpy()
    resumen["rechaza_cc_holm_5pct"] = resumen["pvalor_cc_holm"] < 0.05
    con_es = ok & resumen["pvalor_es"].notna()
    resumen.loc[con_es, "pvalor_es_holm"] = est.holm(resumen.loc[con_es, "pvalor_es"]).to_numpy()
    pronosticos = pd.concat(pron).rename_axis("Date").reset_index()

    # MCS de la pérdida cuantílica entre métodos, promediando las 10 series por fecha.
    mcs = []
    for nivel in NIVELES:
        d = pronosticos[pronosticos["nivel"] == nivel]
        tabla = d.pivot_table(index=["Date", "serie"], columns="metodo",
                              values="perdida_cuantilica").dropna()
        por_fecha = tabla.groupby(level="Date").mean()
        t = est.model_confidence_set(por_fecha, alfa=0.10, n_remuestras=2000,
                                     largo_bloque=10, semilla=SEMILLA_ALEATORIA)
        t.insert(0, "nivel", nivel)
        mcs.append(t)
    mcs = pd.concat(mcs, ignore_index=True)

    res = {"resumen": resumen, "mcs": mcs, "pronosticos": pronosticos}
    if guardar:
        RUTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
        resumen.to_csv(RUTA_RESULTADOS / "fase11_backtesting.csv", index=False)
        mcs.to_csv(RUTA_RESULTADOS / "fase11_mcs_metodos.csv", index=False)
        pronosticos.to_csv(RUTA_RESULTADOS / "fase11_var_es_validacion.csv", index=False)
        _graficar(pronosticos, "portafolio: min_var (liquidas)")
    return res


def _graficar(pron, serie):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    RUTA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    d = pron[(pron["serie"] == serie) & (pron["nivel"] == "99%")]
    fig, ejes = plt.subplots(2, 2, figsize=(14, 7), sharex=True, sharey=True)
    for eje, metodo in zip(ejes.ravel(), medidas.METODOS):
        g = d[d["metodo"] == metodo].set_index("Date")
        eje.bar(g.index, g["rendimiento"] * 100, color="lightgray", width=1.5)
        eje.plot(g.index, -g["var"] * 100, color="black", lw=1, label="−VaR 99 %")
        eje.plot(g.index, -g["es"] * 100, color="tab:red", lw=0.8, ls="--", label="−ES 99 %")
        x = g[g["exceso"]]
        eje.scatter(x.index, x["rendimiento"] * 100, color="tab:red", zorder=3, s=18)
        eje.set_title(f"{metodo}: {int(g['exceso'].sum())} excesos de {len(g)}", fontsize=9)
        eje.tick_params(labelsize=7)
    ejes[0, 0].legend(fontsize=7)
    ejes[0, 0].set_ylabel("Rendimiento diario (%)")
    fig.suptitle(f"Validación 2024 — {serie}: VaR y ES al 99 % a un día", fontsize=10)
    fig.tight_layout()
    fig.savefig(RUTA_GRAFICOS / "fase11_var_validacion.png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    r = ejecutar_fase11()
    pd.set_option("display.width", 250)
    cols = ["serie", "nivel", "metodo", "n", "excesos", "excesos_esperados", "pvalor_kupiec",
            "pvalor_cc", "pvalor_cc_holm", "zona_basilea", "perdida_sobre_es", "pvalor_es",
            "perdida_cuantilica"]
    print(r["resumen"][cols].round(4).to_string(index=False))
    print(r["mcs"].round(6).to_string(index=False))
