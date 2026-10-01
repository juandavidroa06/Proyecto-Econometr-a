"""
metricas.py — Evaluación de un portafolio con pesos fijos
==========================================================

Calcula métricas sobre un bloque de rendimientos SIMPLES dado, aplicando
pesos constantes (rebalanceo diario implícito). Es una evaluación estática;
el backtesting walk-forward con rebalanceo periódico es la Fase 14.

Los faltantes no se rellenan: se descartan filas completas y se informa
cuántas.
"""

import numpy as np
import pandas as pd

from config.settings import DIAS_BURSATILES_ANIO, TASA_LIBRE_RIESGO_ANUAL


def rendimiento_diario(rend_simple, pesos):
    """Serie del rendimiento diario del portafolio y n de filas descartadas."""
    if list(pesos.index) != list(rend_simple.columns):
        raise ValueError("Los pesos y los rendimientos deben tener los mismos "
                         "activos y el mismo orden.")
    completos = rend_simple.dropna(how="any")
    if len(completos) == 0:
        raise ValueError("No quedan filas completas para evaluar.")
    serie = completos.to_numpy() @ pesos.to_numpy()
    return (pd.Series(serie, index=completos.index),
            int(len(rend_simple) - len(completos)))


def maximo_drawdown(r_diario):
    """Mayor caída porcentual desde un máximo previo del valor acumulado."""
    valor = (1.0 + r_diario).cumprod()
    pico = valor.cummax()
    return float((valor / pico - 1.0).min())


def metricas_portafolio(rend_simple, pesos, rf=TASA_LIBRE_RIESGO_ANUAL,
                        dias=DIAS_BURSATILES_ANIO):
    """Métricas anualizadas de un portafolio con pesos fijos."""
    r, n_desc = rendimiento_diario(rend_simple, pesos)
    ret = float(r.mean() * dias)
    vol = float(r.std(ddof=1) * np.sqrt(dias))
    return {
        "observaciones": int(len(r)),
        "filas_descartadas": n_desc,
        "retorno_anual": ret,
        "volatilidad_anual": vol,
        "sharpe": (ret - rf) / vol if vol > 0 else float("nan"),
        "rendimiento_acumulado": float((1.0 + r).prod() - 1.0),
        "max_drawdown": maximo_drawdown(r),
    }
