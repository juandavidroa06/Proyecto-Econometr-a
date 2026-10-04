"""
modelos.py — Random Forest y Gradient Boosting (Fase 8, DEC-025)
=================================================================

Responsabilidad única: elegir hiperparámetros con validación cruzada
TEMPORAL dentro de entrenamiento y ajustar el modelo final.

    - Pliegues por FECHAS (no por filas): todas las empresas de un mismo día
      quedan en el mismo pliegue, y cada pliegue de prueba es posterior a su
      entrenamiento (ventana expansiva). Nunca se usa el bloque de validación
      para elegir hiperparámetros: queda para comparar modelos.
    - Semilla fija (``SEMILLA_ALEATORIA``) en todos los estimadores.
"""

import itertools

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor

from config.settings import SEMILLA_ALEATORIA

REJILLAS = {
    "random_forest": {
        "max_depth": [3, 6],
        "min_samples_leaf": [50, 200],
        "max_features": [0.3, 1.0],
    },
    "gradient_boosting": {
        "learning_rate": [0.02, 0.1],
        "max_depth": [2, 4],
        "min_samples_leaf": [50, 200],
    },
}


def crear_modelo(tipo, **hiper):
    """Instancia el estimador con semilla fija."""
    if tipo == "random_forest":
        return RandomForestRegressor(n_estimators=300, n_jobs=-1,
                                     random_state=SEMILLA_ALEATORIA, **hiper)
    if tipo == "gradient_boosting":
        return HistGradientBoostingRegressor(max_iter=300, early_stopping=False,
                                             random_state=SEMILLA_ALEATORIA, **hiper)
    raise ValueError(f"Tipo de modelo desconocido: {tipo!r}")


def pliegues_por_fecha(fechas, n_pliegues=5):
    """Índices (train, prueba) de validación cruzada expansiva por fechas.

    Las fechas únicas se dividen en ``n_pliegues + 1`` bloques consecutivos;
    el pliegue k entrena con los bloques 0..k y prueba con el k+1.
    """
    fechas = pd.Series(pd.to_datetime(fechas)).reset_index(drop=True)
    unicas = np.sort(fechas.unique())
    if len(unicas) < 2 * (n_pliegues + 1):
        raise ValueError("Muy pocas fechas para la validación cruzada.")
    bloques = np.array_split(unicas, n_pliegues + 1)
    pliegues = []
    for k in range(n_pliegues):
        fin_train = bloques[k][-1]
        prueba = bloques[k + 1]
        idx_train = np.flatnonzero(fechas <= fin_train)
        idx_prueba = np.flatnonzero(fechas.isin(prueba))
        pliegues.append((idx_train, idx_prueba))
    return pliegues


def validacion_cruzada(tipo, X, y, fechas, n_pliegues=5):
    """Evalúa la rejilla de ``tipo`` con pliegues temporales.

    Retorna (mejores_hiperparametros, tabla) con el MSE medio por
    combinación y, como referencia, el MSE de predecir la media del
    entrenamiento de cada pliegue.
    """
    if len(X) != len(y) or len(X) != len(fechas):
        raise ValueError("X, y y fechas deben tener la misma longitud.")
    if pd.isna(X).any().any() or pd.isna(y).any():
        raise ValueError("X o y tienen faltantes.")
    pliegues = pliegues_por_fecha(fechas, n_pliegues)
    rejilla = REJILLAS[tipo]
    nombres = list(rejilla)
    filas = []
    for valores in itertools.product(*rejilla.values()):
        hiper = dict(zip(nombres, valores))
        errores, referencia = [], []
        for idx_tr, idx_te in pliegues:
            modelo = crear_modelo(tipo, **hiper).fit(X.iloc[idx_tr], y.iloc[idx_tr])
            pred = modelo.predict(X.iloc[idx_te])
            errores.append(float(np.mean((y.iloc[idx_te].to_numpy() - pred) ** 2)))
            media = float(y.iloc[idx_tr].mean())
            referencia.append(float(np.mean((y.iloc[idx_te].to_numpy() - media) ** 2)))
        filas.append({"modelo": tipo, **hiper, "mse_cv": float(np.mean(errores)),
                      "mse_cv_media": float(np.mean(referencia))})
    tabla = pd.DataFrame(filas).sort_values("mse_cv").reset_index(drop=True)
    mejores = {k: tabla.loc[0, k] for k in nombres}
    # Tipos nativos (pandas devuelve numpy scalars / floats para enteros).
    mejores = {k: (int(v) if float(v).is_integer() and k != "max_features"
                   and k != "learning_rate" else float(v)) for k, v in mejores.items()}
    return mejores, tabla


def ajustar_final(tipo, hiper, X, y):
    """Ajusta el modelo con todos los datos de entrenamiento."""
    return crear_modelo(tipo, **hiper).fit(X, y)
