"""
fase8.py — Ejecución de la Fase 8: Random Forest y Gradient Boosting
=====================================================================

Flujo (DEC-025):
    1. Carga SOLO entrenamiento y validación de rendimientos, volumen y
       variables externas (``cargar_entrenamiento_validacion``).
    2. Construye el panel (origen t, empresa) con variables conocidas en t y
       objetivo r_{t+1}; separa por fecha objetivo.
    3. Elige hiperparámetros con validación cruzada temporal en train y
       ajusta un modelo agrupado (las 9 empresas, con indicador de empresa).
    4. Evalúa en validación por empresa contra: pronóstico cero, media de
       entrenamiento y ARIMA de la Fase 7, sobre las MISMAS filas.
    5. Importancia por permutación en validación (interpretación).

No toca el bloque de prueba.

Ejecutar:  python -m src.machine_learning.fase8
"""

import logging

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

from config.environment import RUTA_GRAFICOS, RUTA_PARTICIONES, RUTA_RESULTADOS
from config.settings import FECHA_FIN_TRAIN, FECHA_FIN_VALIDACION, SEMILLA_ALEATORIA
from src.econometrics import evaluacion
from src.machine_learning import modelos, variables
from src.portfolio.markowitz import seleccionar_universo_liquido
from src.preprocessing.split import cargar_entrenamiento_validacion

logger = logging.getLogger(__name__)

TIPOS = ("random_forest", "gradient_boosting")


def cargar_datos():
    datos = {base: cargar_entrenamiento_validacion(RUTA_PARTICIONES, base)
             for base in ("rendimientos_log", "volumen", "externos")}
    unir = lambda d: pd.concat([d["train"], d["validacion"]])
    return (unir(datos["rendimientos_log"]), unir(datos["volumen"]),
            unir(datos["externos"]), datos["rendimientos_log"]["train"])


def matriz_variables(df, columnas, empresas):
    """Variables + indicadores de empresa (one-hot con categorías fijas)."""
    X = df[columnas].copy()
    for e in empresas:
        X[f"empresa_{e}"] = (df["empresa"] == e).astype(float)
    return X


def ejecutar_fase8(guardar=True):
    rend, vol, ext, rend_train = cargar_datos()
    panel = variables.construir_panel(rend, vol, ext)
    train, valid, resumen_filas = variables.separar(panel, FECHA_FIN_TRAIN,
                                                    FECHA_FIN_VALIDACION)
    columnas = variables.columnas_variables(panel)
    empresas = list(rend.columns)
    X_tr, X_va = matriz_variables(train, columnas, empresas), matriz_variables(valid, columnas, empresas)
    y_tr, y_va = train["objetivo"], valid["objetivo"]
    logger.info("Filas: %s", resumen_filas.to_dict("records"))

    tablas_cv, hiper, pred = [], {}, {}
    ajustados = {}
    for tipo in TIPOS:
        mejores, tabla = modelos.validacion_cruzada(tipo, X_tr, y_tr, train["Date"])
        logger.info("%s: mejores hiperparámetros %s", tipo, mejores)
        tablas_cv.append(tabla)
        hiper[tipo] = mejores
        ajustados[tipo] = modelos.ajustar_final(tipo, mejores, X_tr, y_tr)
        pred[tipo] = ajustados[tipo].predict(X_va)

    # Pronósticos alineados por (fecha objetivo, empresa).
    comp = valid[["fecha_objetivo", "empresa", "objetivo"]].copy()
    for tipo in TIPOS:
        comp[tipo] = pred[tipo]
    comp["cero"] = 0.0
    comp["media_train"] = comp["empresa"].map(rend_train.mean())
    arima = pd.read_csv(RUTA_RESULTADOS / "fase7_pronosticos_validacion.csv",
                        parse_dates=["Date"])
    arima = arima.rename(columns={"Date": "fecha_objetivo",
                                  "pronostico_arima": "arima"})
    comp = comp.merge(arima[["fecha_objetivo", "empresa", "arima"]],
                      on=["fecha_objetivo", "empresa"], how="left")
    n_antes = len(comp)
    comp = comp.dropna(subset=["arima"]).reset_index(drop=True)
    logger.info("Filas de validación sin pronóstico ARIMA descartadas: %d",
                n_antes - len(comp))

    _, iliquidos, _ = seleccionar_universo_liquido(rend_train)
    filas = []
    for empresa, g in [("Todas", comp)] + list(comp.groupby("empresa", sort=False)):
        y = g["objetivo"].reset_index(drop=True)
        fila = {"empresa": empresa, "n": len(g),
                "iliquida_train": empresa in iliquidos}
        perdida_media = evaluacion.perdida_cuadratica(
            y, g["media_train"].reset_index(drop=True))
        for nombre in TIPOS + ("arima", "media_train", "cero"):
            f = g[nombre].reset_index(drop=True)
            fila[f"rmse_{nombre}"] = evaluacion.rmse(y, f)
            fila[f"mae_{nombre}"] = evaluacion.mae(y, f)
        for nombre in TIPOS:
            dm = evaluacion.diebold_mariano(
                evaluacion.perdida_cuadratica(y, g[nombre].reset_index(drop=True)),
                perdida_media)
            fila[f"dm_{nombre}_vs_media"] = dm["dm_estadistico"]
            fila[f"dm_pvalor_{nombre}_vs_media"] = dm["dm_pvalor"]
        filas.append(fila)
    metricas = pd.DataFrame(filas)

    importancias = []
    for tipo in TIPOS:
        imp = permutation_importance(ajustados[tipo], X_va, y_va, n_repeats=5,
                                     random_state=SEMILLA_ALEATORIA,
                                     scoring="neg_mean_squared_error", n_jobs=-1)
        importancias.append(pd.DataFrame({
            "modelo": tipo, "variable": X_va.columns,
            "aumento_mse_medio": imp.importances_mean,
            "desviacion": imp.importances_std}))
    importancia = (pd.concat(importancias)
                   .sort_values(["modelo", "aumento_mse_medio"], ascending=[True, False]))

    res = {
        "filas": resumen_filas,
        "cv": pd.concat(tablas_cv, ignore_index=True),
        "hiperparametros": pd.DataFrame([{"modelo": t, **h} for t, h in hiper.items()]),
        "metricas": metricas,
        "pronosticos": comp,
        "importancia": importancia,
    }
    if guardar:
        RUTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
        for clave, archivo in (("filas", "fase8_filas.csv"), ("cv", "fase8_validacion_cruzada.csv"),
                               ("hiperparametros", "fase8_hiperparametros.csv"),
                               ("metricas", "fase8_metricas.csv"),
                               ("pronosticos", "fase8_pronosticos_validacion.csv"),
                               ("importancia", "fase8_importancia_permutacion.csv")):
            res[clave].to_csv(RUTA_RESULTADOS / archivo, index=False)
        _graficar_importancia(importancia)
    return res


def _graficar_importancia(importancia, top=12):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    RUTA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    fig, ejes = plt.subplots(1, len(TIPOS), figsize=(13, 5))
    for eje, tipo in zip(np.atleast_1d(ejes), TIPOS):
        d = importancia[importancia["modelo"] == tipo].head(top).iloc[::-1]
        eje.barh(d["variable"], d["aumento_mse_medio"], xerr=d["desviacion"],
                 color="gray")
        eje.axvline(0, color="black", lw=0.8)
        eje.set_title(f"{tipo}: importancia por permutación (validación)", fontsize=9)
        eje.tick_params(labelsize=7)
    fig.tight_layout()
    fig.savefig(RUTA_GRAFICOS / "fase8_importancia.png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    r = ejecutar_fase8()
    pd.set_option("display.width", 250)
    print(r["filas"].to_string(index=False))
    print(r["hiperparametros"].to_string(index=False))
    m = r["metricas"]
    cols = ["empresa", "n", "rmse_random_forest", "rmse_gradient_boosting", "rmse_arima",
            "rmse_media_train", "rmse_cero", "dm_pvalor_random_forest_vs_media",
            "dm_pvalor_gradient_boosting_vs_media", "iliquida_train"]
    print(m[cols].round(5).to_string(index=False))
