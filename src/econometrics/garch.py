"""
garch.py — Volatilidad condicional GARCH(1,1) (Fase 7)
=======================================================

Responsabilidad única: ajustar, diagnosticar y pronosticar la varianza
condicional de los rendimientos, y sus referencias simples (varianza
constante y EWMA).

Reglas del proyecto que este módulo respeta:
    - Los parámetros se estiman SOLO con entrenamiento (``last_obs``).
    - El pronóstico de validación es a un paso con parámetros fijos: la
      varianza de t usa solo datos hasta t-1.
    - Si el optimizador no converge se informa (``convergio = False``);
      no se devuelven parámetros "de relleno".

Escala: ``arch`` es numéricamente más estable con rendimientos en %; las
varianzas se devuelven en %^2 (rendimiento logarítmico x 100).
"""

import numpy as np
import pandas as pd
from arch import arch_model
from statsmodels.stats.diagnostic import acorr_ljungbox

from src.econometrics.arima import ESCALA, _validar_serie


def _serie_completa(train, validacion):
    _validar_serie(train, "train")
    if validacion is None:
        return train * ESCALA
    _validar_serie(validacion, "validacion")
    if not train.index.max() < validacion.index.min():
        raise ValueError("Leakage: validación debe empezar después de train.")
    return pd.concat([train, validacion]) * ESCALA


def ajustar_garch(train, validacion=None, distribucion="t"):
    """GARCH(1,1) con media constante, estimado SOLO con train.

    Si se pasa ``validacion`` el modelo la incluye en los datos pero el
    ajuste usa ``last_obs`` = fin de train, de modo que sirve para filtrar
    y pronosticar validación con los mismos parámetros.
    Retorna el resultado de ``arch``.
    """
    y = _serie_completa(train, validacion)
    modelo = arch_model(y.reset_index(drop=True), mean="Constant", vol="GARCH",
                        p=1, q=1, dist=distribucion, rescale=False)
    return modelo.fit(last_obs=len(train), disp="off")


def resumen_garch(resultado, rezagos=10):
    """Parámetros, persistencia y diagnóstico de residuos estandarizados."""
    par = resultado.params
    z = (resultado.resid / resultado.conditional_volatility).dropna()
    persistencia = float(par["alpha[1]"] + par["beta[1]"])
    return {
        "mu": float(par["mu"]),
        "omega": float(par["omega"]),
        "alpha": float(par["alpha[1]"]),
        "beta": float(par["beta[1]"]),
        "nu": float(par["nu"]) if "nu" in par else float("nan"),
        "persistencia": persistencia,
        "estacionario": persistencia < 1,
        "convergio": resultado.convergence_flag == 0,
        "loglik": float(resultado.loglikelihood),
        "bic": float(resultado.bic),
        "lb_z_pvalor": float(acorr_ljungbox(z, lags=[rezagos])["lb_pvalue"].iloc[0]),
        "lb_z2_pvalor": float(acorr_ljungbox(z ** 2, lags=[rezagos])["lb_pvalue"].iloc[0]),
    }


def pronostico_varianza_un_paso(resultado, train, validacion):
    """Varianza a un paso (en %^2) para cada fecha de validación.

    ``resultado`` debe venir de ``ajustar_garch(train, validacion)``. La fila
    de ``arch`` en el origen t es el pronóstico para t+1; se realinea a la
    fecha pronosticada.
    """
    n_train = len(train)
    if len(resultado.model.y) != n_train + len(validacion):
        raise ValueError("El resultado no se ajustó con train + validación.")
    f = resultado.forecast(horizon=1, start=n_train - 1, reindex=False).variance
    valores = f["h.1"].to_numpy()[:len(validacion)]
    return pd.Series(valores, index=validacion.index, name="varianza")


def varianza_constante(train, validacion):
    """Referencia: varianza muestral de train (en %^2), constante."""
    _validar_serie(train, "train")
    v = float((train * ESCALA).var(ddof=1))
    return pd.Series(v, index=validacion.index, name="varianza")


def varianza_ewma(train, validacion, lam=0.94):
    """Referencia RiskMetrics: h_t = lam h_{t-1} + (1-lam) r_{t-1}^2 (en %^2).

    Se inicializa con la varianza de train y se recorre train + validación;
    no estima parámetros. La varianza de t usa solo datos hasta t-1.
    """
    if not 0 < lam < 1:
        raise ValueError("lam debe estar en (0, 1).")
    y = _serie_completa(train, validacion).to_numpy()
    h = np.empty(len(y))
    h[0] = float((train * ESCALA).var(ddof=1))
    for t in range(1, len(y)):
        h[t] = lam * h[t - 1] + (1 - lam) * y[t - 1] ** 2
    return pd.Series(h[len(train):], index=validacion.index, name="varianza")
