"""
descriptive_statistics.py — Estadística descriptiva de rendimientos
====================================================================

Proporciona funciones para resumir las series de rendimientos. Todas las
funciones descartan los NaN *dentro* de cada columna de forma explícita,
sin modificar los datos originales.
"""

import numpy as np
import pandas as pd

from config.settings import DIAS_BURSATILES_ANIO


def estadisticas_descriptivas(df_rendimientos):
    """Calcula estadísticas descriptivas por activo (columna).

    Retorna un DataFrame con una fila por activo y columnas:
    observaciones, media, mediana, desviación estándar, mínimo, máximo,
    percentiles (1, 5, 25, 75, 95, 99), asimetría y curtosis.
    """
    filas = {}
    for columna in df_rendimientos.columns:
        serie = df_rendimientos[columna].dropna()
        if len(serie) == 0:
            continue
        filas[columna] = {
            "observaciones": int(len(serie)),
            "media": float(serie.mean()),
            "mediana": float(serie.median()),
            "desviacion_estandar": float(serie.std()),
            "minimo": float(serie.min()),
            "maximo": float(serie.max()),
            "percentil_1": float(serie.quantile(0.01)),
            "percentil_5": float(serie.quantile(0.05)),
            "percentil_25": float(serie.quantile(0.25)),
            "percentil_75": float(serie.quantile(0.75)),
            "percentil_95": float(serie.quantile(0.95)),
            "percentil_99": float(serie.quantile(0.99)),
            "asimetria": float(serie.skew()),
            "curtosis": float(serie.kurtosis()),
        }
    return pd.DataFrame(filas).T


def volatilidad_diaria(df_rendimientos):
    """Distancia estándar (volatilidad) diaria por activo."""
    return df_rendimientos.std().rename("volatilidad_diaria")


def volatilidad_anualizada(df_rendimientos, dias=DIAS_BURSATILES_ANIO):
    """Volatilidad anualizada usando la convención sigma_anual = sigma_diaria * sqrt(dias).

    ``dias``=252 es una aproximación convencional al número de días bursátiles
    por año. No es una verdad universal, solo una convención de mercado.
    """
    return (df_rendimientos.std() * np.sqrt(dias)).rename("volatilidad_anualizada")


def resumir_volatilidad(df_rendimientos, dias=DIAS_BURSATILES_ANIO):
    """Combina volatilidad diaria y anualizada en un DataFrame."""
    return pd.DataFrame({
        "volatilidad_diaria": volatilidad_diaria(df_rendimientos),
        "volatilidad_anualizada": volatilidad_anualizada(df_rendimientos, dias),
    })