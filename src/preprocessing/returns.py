"""
returns.py — Cálculo de rendimientos
=====================================

Calcula los rendimientos a partir de una serie de precios.

Definiciones:
    - Rendimiento simple:   R_t = (P_t - P_{t-1}) / P_{t-1}
    - Rendimiento logarítmico: r_t = ln(P_t / P_{t-1})

Nota metodológica importante:
    La primera observación de cada serie queda como NaN porque no existe
    precio previo con el cual calcular el rendimiento. Este NaN NO se elimina
    silenciosamente: se conserva y se documenta. Los análisis que lo requieran
    (estadísticos, correlaciones) aplican ``dropna()`` de forma explícita.
"""

import numpy as np
import pandas as pd


def rendimiento_simple(precios):
    """Rendimiento simple: R_t = P_t / P_{t-1} - 1."""
    return precios.pct_change()


def rendimiento_log(precios):
    """Rendimiento logarítmico: r_t = ln(P_t / P_{t-1})."""
    return np.log(precios / precios.shift(1))


def calcular_rendimientos(precios):
    """Calcula rendimientos simple y logarítmico.

    Parámetros:
        precios: pd.DataFrame (o Series) con precios. El índice debe ser
        cronológico.

    Retorna:
        (rendimientos_simples, rendimientos_log) como tupla.
    """
    simples = rendimiento_simple(precios)
    logs = rendimiento_log(precios)
    return simples, logs