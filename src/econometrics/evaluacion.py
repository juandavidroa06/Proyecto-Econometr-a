"""
evaluacion.py — Métricas de pronóstico (Fase 7)
================================================

Responsabilidad única: comparar pronósticos con valores observados.

    - Media condicional: MAE, RMSE y prueba de Diebold-Mariano.
    - Varianza condicional: QLIKE y MSE frente a un proxy (r_t^2).

No lee archivos ni ajusta modelos.
"""

import numpy as np
import pandas as pd
from scipy import stats


def _alinear(observado, pronostico):
    if not isinstance(observado, pd.Series) or not isinstance(pronostico, pd.Series):
        raise TypeError("Se esperaban Series de pandas.")
    if not observado.index.equals(pronostico.index):
        raise ValueError("Observado y pronóstico deben tener el mismo índice.")
    if observado.isna().any() or pronostico.isna().any():
        raise ValueError("Hay faltantes en observado o pronóstico.")
    return observado.to_numpy(float), pronostico.to_numpy(float)


def mae(observado, pronostico):
    y, f = _alinear(observado, pronostico)
    return float(np.mean(np.abs(y - f)))


def rmse(observado, pronostico):
    y, f = _alinear(observado, pronostico)
    return float(np.sqrt(np.mean((y - f) ** 2)))


def qlike(proxy, varianza):
    """QLIKE robusto (Patton, 2011): mean(log h + proxy / h).

    Admite proxy = 0 (frecuente en acciones ilíquidas). Menor es mejor.
    """
    y, h = _alinear(proxy, varianza)
    if (h <= 0).any():
        raise ValueError("La varianza pronosticada debe ser positiva.")
    return float(np.mean(np.log(h) + y / h))


def mse_varianza(proxy, varianza):
    y, h = _alinear(proxy, varianza)
    return float(np.mean((y - h) ** 2))


def perdida_cuadratica(observado, pronostico):
    """Pérdida por observación (y - f)^2, como Series (para Diebold-Mariano)."""
    y, f = _alinear(observado, pronostico)
    return pd.Series((y - f) ** 2, index=observado.index)


def perdida_qlike(proxy, varianza):
    """Pérdida QLIKE por observación log h + proxy / h, como Series."""
    y, h = _alinear(proxy, varianza)
    if (h <= 0).any():
        raise ValueError("La varianza pronosticada debe ser positiva.")
    return pd.Series(np.log(h) + y / h, index=proxy.index)


def diebold_mariano(perdida_modelo, perdida_referencia, horizonte=1):
    """Prueba de Diebold-Mariano con corrección de Harvey-Leybourne-Newbold.

    d_t = pérdida_modelo - pérdida_referencia. H0: igual precisión.
    Estadístico negativo => el modelo tiene menor pérdida.
    Retorna dict con estadístico, p-valor bilateral y n.
    """
    a, b = _alinear(perdida_modelo, perdida_referencia)
    d = a - b
    n = len(d)
    if n < 10:
        raise ValueError("Muy pocas observaciones para Diebold-Mariano.")
    d_media = d.mean()
    # Varianza de largo plazo con autocovarianzas hasta horizonte - 1.
    gamma = [np.mean((d[k:] - d_media) * (d[:n - k] - d_media))
             for k in range(horizonte)]
    var = (gamma[0] + 2 * sum(gamma[1:])) / n
    if var <= 0:
        return {"dm_estadistico": float("nan"), "dm_pvalor": float("nan"), "n": n}
    dm = d_media / np.sqrt(var)
    correccion = np.sqrt((n + 1 - 2 * horizonte
                          + horizonte * (horizonte - 1) / n) / n)
    dm *= correccion
    pvalor = 2 * stats.t.sf(abs(dm), df=n - 1)
    return {"dm_estadistico": float(dm), "dm_pvalor": float(pvalor), "n": n}
