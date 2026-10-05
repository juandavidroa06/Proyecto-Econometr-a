"""
arima.py — Modelos ARMA para la media de los rendimientos (Fase 7)
===================================================================

Responsabilidad única: seleccionar, ajustar, diagnosticar y pronosticar
ARIMA(p, 0, q) con constante sobre rendimientos logarítmicos.

Reglas del proyecto que este módulo respeta:
    - Los parámetros se estiman SOLO con la serie de entrenamiento.
    - El pronóstico de validación es a un paso con parámetros FIJOS: el
      valor de t usa solo datos hasta t-1 (filtro de Kalman), sin
      reestimar (la reestimación periódica es el backtesting, Fase 14).
    - d = 0: las pruebas ADF/KPSS de la Fase 4 (entrenamiento) indican que
      los rendimientos son estacionarios.
    - Los avisos de convergencia no se ocultan: se registran por modelo.

Escala: el ajuste se hace sobre rendimientos en % (x 100). Con rendimientos
en proporción (varianza ~ 4e-4) el optimizador declaraba no convergencia en
modelos simples por tolerancia numérica, con los mismos parámetros (DEC-023).
Los pronósticos se devuelven en la escala original; AIC/BIC y la constante
quedan en la escala %.
"""

import itertools
import warnings

import numpy as np
import pandas as pd
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.tsa.arima.model import ARIMA

ESCALA = 100.0


def _validar_serie(serie, nombre="serie"):
    if not isinstance(serie, pd.Series):
        raise TypeError(f"{nombre}: se esperaba una Series.")
    if not isinstance(serie.index, pd.DatetimeIndex):
        raise TypeError(f"{nombre}: el índice debe ser DatetimeIndex.")
    if not serie.index.is_monotonic_increasing or serie.index.has_duplicates:
        raise ValueError(f"{nombre}: índice no cronológico o con duplicados.")
    if serie.isna().any() or not np.isfinite(serie.to_numpy(float)).all():
        raise ValueError(f"{nombre}: contiene faltantes o infinitos.")


def _ajustar(serie, orden):
    """Ajusta ARIMA(p,0,q) con constante y captura (no oculta) los avisos."""
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        # Índice sin frecuencia (días hábiles con huecos): se usa posición.
        modelo = ARIMA(serie.reset_index(drop=True) * ESCALA,
                       order=(orden[0], 0, orden[1]), trend="c")
        res = modelo.fit()
    mensajes = sorted({str(a.message).splitlines()[0] for a in avisos
                       if "frequency" not in str(a.message)})
    return res, mensajes


def seleccionar_orden(train, max_p=3, max_q=3, criterio="bic"):
    """Ajusta todos los ARIMA(p,0,q) con p<=max_p, q<=max_q sobre train.

    Retorna (orden_elegido, tabla) donde la tabla tiene p, q, aic, bic,
    convergencia y avisos. Se elige el menor ``criterio`` entre los que
    convergieron; si ninguno convergió se lanza RuntimeError.
    """
    _validar_serie(train, "train")
    if criterio not in ("aic", "bic"):
        raise ValueError("criterio debe ser 'aic' o 'bic'.")
    filas = []
    for p, q in itertools.product(range(max_p + 1), range(max_q + 1)):
        try:
            res, avisos = _ajustar(train, (p, q))
        except (np.linalg.LinAlgError, ValueError) as exc:
            # Fallo numérico de un candidato: se registra como no convergido
            # (no se oculta ni se detiene la selección; DEC-038).
            filas.append({"p": p, "q": q, "aic": np.nan, "bic": np.nan, "convergio": False,
                          "avisos": f"Error de ajuste: {type(exc).__name__}: {exc}"})
            continue
        convergio = bool(res.mle_retvals.get("converged", True)) if res.mle_retvals else True
        filas.append({"p": p, "q": q, "aic": float(res.aic), "bic": float(res.bic),
                      "convergio": convergio, "avisos": " | ".join(avisos)})
    tabla = pd.DataFrame(filas)
    candidatos = tabla[tabla["convergio"]]
    if candidatos.empty:
        raise RuntimeError("Ningún ARIMA convergió.")
    mejor = candidatos.loc[candidatos[criterio].idxmin()]
    return (int(mejor["p"]), int(mejor["q"])), tabla


def ajustar_arima(train, orden):
    """Ajusta el ARIMA elegido sobre train. Retorna (resultado, avisos)."""
    _validar_serie(train, "train")
    return _ajustar(train, orden)


def diagnostico_residuos(resultado, rezagos=10):
    """Ljung-Box sobre residuos y residuos^2 (H0: sin autocorrelación)."""
    resid = pd.Series(resultado.resid).iloc[max(resultado.model.k_ar, 1):]
    lb = acorr_ljungbox(resid, lags=[rezagos])["lb_pvalue"].iloc[0]
    lb2 = acorr_ljungbox(resid ** 2, lags=[rezagos])["lb_pvalue"].iloc[0]
    return {"lb_resid_pvalor": float(lb), "lb_resid2_pvalor": float(lb2)}


def pronostico_un_paso(train, validacion, resultado):
    """Pronóstico a un paso sobre validación con parámetros fijos de train.

    Para cada fecha t de validación usa solo observaciones hasta t-1.
    Retorna Series indexada por las fechas de validación.
    """
    _validar_serie(train, "train")
    _validar_serie(validacion, "validacion")
    if not train.index.max() < validacion.index.min():
        raise ValueError("Leakage: validación debe empezar después de train.")
    orden = resultado.model.order
    completa = pd.concat([train, validacion]).reset_index(drop=True) * ESCALA
    filtrado = ARIMA(completa, order=orden, trend="c").filter(resultado.params)
    pred = filtrado.get_prediction(start=len(train)).predicted_mean / ESCALA
    return pd.Series(pred.to_numpy(), index=validacion.index, name="pronostico")
