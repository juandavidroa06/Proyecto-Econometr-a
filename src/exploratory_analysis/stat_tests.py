"""
stat_tests.py — Pruebas formales sobre rendimientos (Fase 4, EDA)
=================================================================

Justifican (o no) los modelos de la Fase 7:
    - Normalidad: Jarque-Bera.
    - Estacionariedad: ADF (H0: raíz unitaria) y KPSS (H0: estacionaria).
    - Autocorrelación: Ljung-Box sobre r_t  -> orden ARIMA.
    - Efectos ARCH: Ljung-Box sobre r_t^2 y ARCH-LM -> justifica GARCH.

USAR SOLO SOBRE EL BLOQUE DE ENTRENAMIENTO (ver split.py, DEC-017).

Nota: el p-valor de KPSS está truncado a [0.01, 0.10] por construcción.
"""

import warnings

import pandas as pd
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox, het_arch
from statsmodels.tools.sm_exceptions import InterpolationWarning
from statsmodels.tsa.stattools import adfuller, kpss

from config.settings import NIVEL_SIGNIFICANCIA


def pruebas_estacionariedad(df, alfa=NIVEL_SIGNIFICANCIA):
    filas = []
    for col in df.columns:
        s = df[col].dropna()
        adf_p = adfuller(s, autolag="AIC", result_object=False)[1]
        with warnings.catch_warnings():
            # KPSS trunca el p-valor a [0.01, 0.10] (tabla de valores críticos).
            warnings.simplefilter("ignore", InterpolationWarning)
            kpss_p = kpss(s, regression="c", nlags="auto",
                          result_object=False)[1]
        filas.append({"serie": col, "n": len(s), "adf_pvalor": adf_p,
                      "kpss_pvalor": kpss_p,
                      "adf_rechaza_raiz_unitaria": adf_p < alfa,
                      "kpss_rechaza_estacionariedad": kpss_p < alfa})
    return pd.DataFrame(filas)


def pruebas_rendimientos(rend_log, rezagos=10, alfa=NIVEL_SIGNIFICANCIA):
    filas = []
    for col in rend_log.columns:
        r = rend_log[col].dropna()
        jb_p = stats.jarque_bera(r).pvalue
        lb_r = acorr_ljungbox(r, lags=[rezagos])["lb_pvalue"].iloc[0]
        lb_r2 = acorr_ljungbox(r ** 2, lags=[rezagos])["lb_pvalue"].iloc[0]
        arch_p = het_arch(r, nlags=rezagos, result_object=False)[1]
        filas.append({
            "serie": col, "n": len(r),
            "jb_pvalor": jb_p, "lb_r_pvalor": lb_r,
            "lb_r2_pvalor": lb_r2, "arch_lm_pvalor": arch_p,
            "no_normal": jb_p < alfa,
            "autocorrelacion": lb_r < alfa,
            "efecto_arch": (lb_r2 < alfa) or (arch_p < alfa),
        })
    return pd.DataFrame(filas)
