"""
backtesting.py — Validación de VaR y ES (Fase 11, DEC-028)
===========================================================

Responsabilidad única: comprobar si las medidas de riesgo pronosticadas
son coherentes con las pérdidas observadas.

    - Kupiec (1995): cobertura incondicional (proporción de excesos = alfa).
    - Christoffersen (1998): independencia de los excesos y cobertura
      condicional.
    - Zona de semáforo de Basilea para VaR 99 % (escalada a n observaciones).
    - Prueba de los excesos para ES: en los días con exceso, la pérdida
      relativa L/ES debería promediar 1.
    - Pérdida cuantílica ("tick loss"), que permite comparar métodos de VaR.
"""

import numpy as np
from scipy import stats


def _xlogy(x, y):
    return 0.0 if x == 0 else x * np.log(y)


def excesos(rendimiento, var):
    """Indicador de exceso: la pérdida supera el VaR (R_t < -VaR_t)."""
    r = np.asarray(rendimiento, float)
    v = np.asarray(var, float)
    if r.shape != v.shape or np.isnan(r).any() or np.isnan(v).any():
        raise ValueError("Rendimientos y VaR de distinta forma o con faltantes.")
    return r < -v


def kupiec(ex, alfa):
    """Prueba de proporción de fallas. Retorna (LR, p-valor)."""
    ex = np.asarray(ex, bool)
    n, x = len(ex), int(ex.sum())
    p_hat = x / n
    lr = -2 * (_xlogy(n - x, 1 - alfa) + _xlogy(x, alfa)
               - _xlogy(n - x, 1 - p_hat) - _xlogy(x, p_hat))
    return float(lr), float(stats.chi2.sf(lr, 1))


def christoffersen(ex, alfa):
    """Independencia (cadena de Markov) y cobertura condicional.

    Retorna dict con LR y p-valor de independencia y de cobertura
    condicional (Kupiec + independencia, chi2 con 2 g.l.).
    """
    ex = np.asarray(ex, int)
    previo, actual = ex[:-1], ex[1:]
    n00 = int(((previo == 0) & (actual == 0)).sum())
    n01 = int(((previo == 0) & (actual == 1)).sum())
    n10 = int(((previo == 1) & (actual == 0)).sum())
    n11 = int(((previo == 1) & (actual == 1)).sum())
    pi0 = n01 / (n00 + n01) if n00 + n01 else 0.0
    pi1 = n11 / (n10 + n11) if n10 + n11 else 0.0
    pi = (n01 + n11) / (n00 + n01 + n10 + n11)
    log_h0 = _xlogy(n00 + n10, 1 - pi) + _xlogy(n01 + n11, pi)
    log_h1 = (_xlogy(n00, 1 - pi0) + _xlogy(n01, pi0)
              + _xlogy(n10, 1 - pi1) + _xlogy(n11, pi1))
    lr_ind = max(-2 * (log_h0 - log_h1), 0.0)
    lr_uc, _ = kupiec(ex.astype(bool), alfa)
    lr_cc = lr_uc + lr_ind
    return {"lr_ind": float(lr_ind), "pvalor_ind": float(stats.chi2.sf(lr_ind, 1)),
            "lr_cc": float(lr_cc), "pvalor_cc": float(stats.chi2.sf(lr_cc, 2)),
            "excesos_consecutivos": n11}


def zona_basilea(n_excesos, n, alfa=0.01):
    """Semáforo de Basilea para VaR 99 %: verde si la probabilidad
    acumulada binomial < 95 %, amarillo si < 99,99 %, rojo en otro caso
    (equivale a 0–4 / 5–9 / 10+ excesos en 250 días)."""
    acumulada = stats.binom.cdf(n_excesos, n, alfa)
    if acumulada < 0.95:
        return "verde"
    if acumulada < 0.9999:
        return "amarillo"
    return "rojo"


def prueba_es(rendimiento, var, es, minimo=3):
    """Pérdida relativa L/ES en los días con exceso (debería promediar 1).

    Retorna dict con n de excesos, media de L/ES y p-valor unilateral de
    H0: media <= 1 frente a H1: media > 1 (ES subestima la cola). Con menos
    de ``minimo`` excesos no hay prueba (NaN).
    """
    r = np.asarray(rendimiento, float)
    es = np.asarray(es, float)
    ex = excesos(r, var)
    ratio = -r[ex] / es[ex]
    n = int(ex.sum())
    if n < minimo:
        return {"n_excesos": n, "perdida_sobre_es": float(ratio.mean()) if n else np.nan,
                "pvalor_es": np.nan}
    t = stats.ttest_1samp(ratio, 1.0, alternative="greater")
    return {"n_excesos": n, "perdida_sobre_es": float(ratio.mean()),
            "pvalor_es": float(t.pvalue)}


def perdida_cuantilica(rendimiento, var, alfa):
    """Tick loss del cuantil q = -VaR: (alfa - 1{R < q}) (R - q). Menor es mejor."""
    r = np.asarray(rendimiento, float)
    q = -np.asarray(var, float)
    return (alfa - (r < q)) * (r - q)
