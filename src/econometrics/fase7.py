"""
fase7.py — Ejecución de la Fase 7: ARIMA (media) y GARCH (volatilidad)
=======================================================================

Flujo (DEC-023):
    1. Carga SOLO entrenamiento y validación (``cargar_entrenamiento_validacion``).
    2. Por empresa: selecciona ARIMA(p,0,q) por BIC y ajusta GARCH(1,1)-t
       con entrenamiento; diagnostica residuos.
    3. Pronostica a un paso en validación con parámetros fijos y compara
       contra referencias simples:
         media    -> pronóstico cero y media de entrenamiento (MAE, RMSE, DM);
         varianza -> varianza constante de entrenamiento y EWMA (QLIKE, MSE, DM).
    4. Guarda resultados en ``resultados/``.

Cada empresa se modela con sus propios días con rendimiento (se descartan
de forma explícita los NaN de esa empresa; no se imputa nada).

No toca el bloque de prueba.

Ejecutar:  python -m src.econometrics.fase7
"""

import logging

import numpy as np
import pandas as pd

from config.environment import RUTA_GRAFICOS, RUTA_PARTICIONES, RUTA_RESULTADOS
from config.settings import (
    ARIMA_CRITERIO,
    ARIMA_MAX_P,
    ARIMA_MAX_Q,
    EWMA_LAMBDA,
    GARCH_DISTRIBUCION,
    REZAGOS_DIAGNOSTICO,
)
from src.econometrics import arima, evaluacion, garch
from src.portfolio.markowitz import seleccionar_universo_liquido
from src.preprocessing.split import cargar_entrenamiento_validacion

logger = logging.getLogger(__name__)


def _modelar_media(empresa, train, valid):
    """Selección, diagnóstico y evaluación del ARIMA de una empresa."""
    orden, tabla = arima.seleccionar_orden(train, ARIMA_MAX_P, ARIMA_MAX_Q,
                                           ARIMA_CRITERIO)
    res, avisos = arima.ajustar_arima(train, orden)
    diag = arima.diagnostico_residuos(res, REZAGOS_DIAGNOSTICO)
    pred = arima.pronostico_un_paso(train, valid, res)
    refs = {"cero": pd.Series(0.0, index=valid.index),
            "media_train": pd.Series(float(train.mean()), index=valid.index)}

    fila = {"empresa": empresa, "p": orden[0], "q": orden[1],
            "n_train": len(train), "n_validacion": len(valid),
            "avisos_ajuste": " | ".join(avisos), **diag,
            "mae_arima": evaluacion.mae(valid, pred),
            "rmse_arima": evaluacion.rmse(valid, pred)}
    perdida_arima = evaluacion.perdida_cuadratica(valid, pred)
    for nombre, ref in refs.items():
        fila[f"mae_{nombre}"] = evaluacion.mae(valid, ref)
        fila[f"rmse_{nombre}"] = evaluacion.rmse(valid, ref)
        dm = evaluacion.diebold_mariano(perdida_arima,
                                        evaluacion.perdida_cuadratica(valid, ref))
        fila[f"dm_vs_{nombre}"] = dm["dm_estadistico"]
        fila[f"dm_pvalor_vs_{nombre}"] = dm["dm_pvalor"]
    tabla.insert(0, "empresa", empresa)
    return fila, tabla, pred


def _modelar_varianza(empresa, train, valid):
    """Ajuste, diagnóstico y evaluación del GARCH(1,1) de una empresa."""
    res = garch.ajustar_garch(train, valid, GARCH_DISTRIBUCION)
    resumen = garch.resumen_garch(res, REZAGOS_DIAGNOSTICO)
    pronosticos = {
        "garch": garch.pronostico_varianza_un_paso(res, train, valid),
        "constante": garch.varianza_constante(train, valid),
        "ewma": garch.varianza_ewma(train, valid, EWMA_LAMBDA),
    }
    proxy = (valid * garch.ESCALA) ** 2
    fila = {"empresa": empresa, **resumen}
    perdidas = {k: evaluacion.perdida_qlike(proxy, h) for k, h in pronosticos.items()}
    for nombre, h in pronosticos.items():
        fila[f"qlike_{nombre}"] = evaluacion.qlike(proxy, h)
        fila[f"mse_{nombre}"] = evaluacion.mse_varianza(proxy, h)
    for ref in ("constante", "ewma"):
        dm = evaluacion.diebold_mariano(perdidas["garch"], perdidas[ref])
        fila[f"dm_qlike_vs_{ref}"] = dm["dm_estadistico"]
        fila[f"dm_pvalor_vs_{ref}"] = dm["dm_pvalor"]
    return fila, pronosticos


def ejecutar_fase7(guardar=True):
    datos = cargar_entrenamiento_validacion(RUTA_PARTICIONES, "rendimientos_log")
    train_df, valid_df = datos["train"], datos["validacion"]
    _, iliquidos, _ = seleccionar_universo_liquido(train_df)

    filas_media, filas_var, tablas, pron = [], [], [], []
    for empresa in train_df.columns:
        train = train_df[empresa].dropna()
        valid = valid_df[empresa].dropna()
        logger.info("%s: %d obs. train, %d validación (NaN descartados: %d y %d)",
                    empresa, len(train), len(valid),
                    int(train_df[empresa].isna().sum()),
                    int(valid_df[empresa].isna().sum()))
        fm, tabla, pred = _modelar_media(empresa, train, valid)
        fv, varianzas = _modelar_varianza(empresa, train, valid)
        fm["iliquida_train"] = empresa in iliquidos
        fv["iliquida_train"] = empresa in iliquidos
        filas_media.append(fm)
        filas_var.append(fv)
        tablas.append(tabla)
        pron.append(pd.DataFrame({
            "empresa": empresa, "rendimiento": valid, "pronostico_arima": pred,
            **{f"varianza_{k}": v for k, v in varianzas.items()}}))

    res = {
        "arima": pd.DataFrame(filas_media),
        "arima_seleccion": pd.concat(tablas, ignore_index=True),
        "garch": pd.DataFrame(filas_var),
        "pronosticos_validacion": pd.concat(pron).rename_axis("Date").reset_index(),
    }
    if guardar:
        RUTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
        res["arima"].to_csv(RUTA_RESULTADOS / "fase7_arima.csv", index=False)
        res["arima_seleccion"].to_csv(RUTA_RESULTADOS / "fase7_arima_seleccion.csv",
                                      index=False)
        res["garch"].to_csv(RUTA_RESULTADOS / "fase7_garch.csv", index=False)
        res["pronosticos_validacion"].to_csv(
            RUTA_RESULTADOS / "fase7_pronosticos_validacion.csv", index=False)
        _graficar_volatilidad(res["pronosticos_validacion"])
    return res


def _graficar_volatilidad(pron):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    RUTA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    empresas = list(pron["empresa"].unique())
    fig, ejes = plt.subplots(3, 3, figsize=(15, 10), sharex=True)
    for eje, empresa in zip(ejes.ravel(), empresas):
        d = pron[pron["empresa"] == empresa].set_index("Date")
        eje.plot(d.index, np.abs(d["rendimiento"] * 100), color="lightgray",
                 lw=0.8, label="|r_t| (%)")
        for col, color in (("varianza_garch", "black"), ("varianza_ewma", "tab:blue"),
                           ("varianza_constante", "tab:red")):
            eje.plot(d.index, np.sqrt(d[col]), color=color, lw=1,
                     label=col.replace("varianza_", ""))
        eje.set_title(empresa, fontsize=9)
        eje.tick_params(labelsize=7)
    ejes[0, 0].legend(fontsize=7)
    fig.suptitle("Validación 2024: volatilidad diaria pronosticada a un paso (%) "
                 "— parámetros estimados con entrenamiento")
    fig.tight_layout()
    fig.savefig(RUTA_GRAFICOS / "fase7_volatilidad_validacion.png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    r = ejecutar_fase7()
    pd.set_option("display.width", 250)
    print(r["arima"].round(4).to_string(index=False))
    print(r["garch"].round(4).to_string(index=False))
