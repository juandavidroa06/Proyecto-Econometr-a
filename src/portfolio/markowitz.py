"""
markowitz.py — Portafolios de Markowitz (Fase 6, modelo de referencia)
=======================================================================

Responsabilidad única: dado un conjunto de rendimientos, estimar media y
covarianza y calcular pesos de portafolio bajo restricciones.

Portafolios disponibles:
    - Igual ponderación (1/N): referencia ingenua.
    - Mínima varianza.
    - Máximo Sharpe.

Restricciones (todas explícitas y validadas):
    sum(w) = 1,   0 <= w_i <= peso_max   (sin posiciones cortas).

Reglas del proyecto que este módulo respeta:
    - NO lee archivos: recibe DataFrames ya cargados. Quien lo llame debe
      pasar solo entrenamiento (la estimación nunca usa validación ni prueba).
    - Los faltantes NO se rellenan: se descartan filas completas de forma
      explícita y se informa cuántas (AGENTS.md, sección 5).
    - Si el optimizador no converge se lanza un error; no se devuelven pesos
      "de relleno".

Notas metodológicas:
    - Se trabaja con rendimientos SIMPLES (R = exp(r) - 1), porque el
      rendimiento de un portafolio es la suma ponderada de rendimientos
      simples, no de logarítmicos.
    - Media y covarianza se anualizan con ``dias`` (252 por convención).
    - Con rendimientos de acciones poco líquidas, la covarianza puede
      subestimar la dependencia real (negociación no sincrónica).
"""

import logging

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from config.settings import (
    DIAS_BURSATILES_ANIO,
    PESO_MAXIMO_ACTIVO,
    TASA_LIBRE_RIESGO_ANUAL,
    UMBRAL_PCT_PRECIO_REPETIDO,
)

logger = logging.getLogger(__name__)

TOLERANCIA = 1e-9


# =============================================================================
# Preparación de datos
# =============================================================================

def log_a_simple(rend_log):
    """Convierte rendimientos logarítmicos a simples: R = exp(r) - 1."""
    return np.expm1(rend_log)


def _validar_rendimientos(rend):
    if not isinstance(rend, pd.DataFrame):
        raise TypeError("Se esperaba un DataFrame de rendimientos.")
    if rend.shape[1] < 2:
        raise ValueError("Se necesitan al menos 2 activos.")
    if np.isinf(rend.to_numpy(dtype=float)).any():
        raise ValueError("Los rendimientos contienen valores infinitos.")


def filas_completas(rend):
    """Descarta explícitamente las filas con algún faltante.

    Devuelve (rendimientos_completos, n_descartadas). No imputa nada.
    """
    _validar_rendimientos(rend)
    completos = rend.dropna(how="any")
    return completos, int(len(rend) - len(completos))


def estimar_parametros(rend_simple, dias=DIAS_BURSATILES_ANIO):
    """Media y covarianza anualizadas, con filas completas.

    Retorna dict con 'mu' (Series), 'cov' (DataFrame), 'n_obs' y
    'n_descartadas'. Exige más observaciones que el doble de activos.
    """
    completos, n_desc = filas_completas(rend_simple)
    n_activos = completos.shape[1]
    if len(completos) < 2 * n_activos:
        raise ValueError(
            f"Muy pocas observaciones ({len(completos)}) para {n_activos} activos.")
    return {
        "mu": completos.mean() * dias,
        "cov": completos.cov() * dias,
        "n_obs": int(len(completos)),
        "n_descartadas": n_desc,
    }


def seleccionar_universo_liquido(rend_train, umbral=UMBRAL_PCT_PRECIO_REPETIDO):
    """Separa activos líquidos de ilíquidos usando SOLO entrenamiento.

    Criterio: proporción de días con rendimiento exactamente cero (precio sin
    cambio) sobre los días con dato. Un activo es ilíquido si supera
    ``umbral`` (mismo umbral de referencia de la auditoría, DEC-018).
    Retorna (liquidos, iliquidos, tabla).
    """
    _validar_rendimientos(rend_train)
    pct = {}
    for col in rend_train.columns:
        serie = rend_train[col].dropna()
        pct[col] = float((serie == 0).mean())
    tabla = pd.Series(pct, name="pct_rendimiento_cero").to_frame()
    tabla["iliquido"] = tabla["pct_rendimiento_cero"] > umbral
    liquidos = list(tabla.index[~tabla["iliquido"]])
    iliquidos = list(tabla.index[tabla["iliquido"]])
    return liquidos, iliquidos, tabla.sort_values("pct_rendimiento_cero",
                                                  ascending=False)


# =============================================================================
# Utilidades de portafolio
# =============================================================================

def _validar_restricciones(n, peso_max):
    if not 0 < peso_max <= 1:
        raise ValueError("peso_max debe estar en (0, 1].")
    if n * peso_max < 1 - TOLERANCIA:
        raise ValueError(
            f"Restricción infactible: {n} activos con peso máximo {peso_max} "
            f"solo suman {n * peso_max:.2f} < 1.")


def _validar_entrada(mu, cov):
    if list(mu.index) != list(cov.index) or list(cov.index) != list(cov.columns):
        raise ValueError("mu y cov deben tener los mismos activos y orden.")
    if not np.isfinite(mu.to_numpy()).all() or not np.isfinite(cov.to_numpy()).all():
        raise ValueError("mu o cov contienen valores no finitos.")


def retorno_esperado(w, mu):
    return float(np.dot(w, mu.to_numpy()))


def volatilidad(w, cov):
    varianza = float(np.dot(w, cov.to_numpy() @ w))
    return float(np.sqrt(max(varianza, 0.0)))


def verificar_pesos(w, peso_max):
    """Comprueba suma 1, no negatividad y tope. Lanza ValueError si falla."""
    w = np.asarray(w, dtype=float)
    if abs(w.sum() - 1) > 1e-6:
        raise ValueError(f"Los pesos no suman 1 ({w.sum():.8f}).")
    if (w < -1e-8).any():
        raise ValueError("Hay pesos negativos (posiciones cortas).")
    if (w > peso_max + 1e-6).any():
        raise ValueError("Hay pesos por encima del peso máximo.")


def _como_series(w, columnas):
    w = np.clip(np.asarray(w, dtype=float), 0.0, None)
    w = w / w.sum()  # limpia ruido numérico (~1e-12) sin cambiar el resultado
    return pd.Series(w, index=columnas)


def _optimizar(objetivo, n, peso_max, restricciones_extra=(), x0=None):
    _validar_restricciones(n, peso_max)
    if x0 is None:
        x0 = np.full(n, 1.0 / n)
    restricciones = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    restricciones.extend(restricciones_extra)
    res = minimize(objetivo, x0, method="SLSQP",
                   bounds=[(0.0, peso_max)] * n,
                   constraints=restricciones,
                   options={"maxiter": 1000, "ftol": 1e-12})
    if not res.success:
        raise RuntimeError(f"El optimizador no convergió: {res.message}")
    return res.x


# =============================================================================
# Portafolios
# =============================================================================

def pesos_igual(columnas, peso_max=PESO_MAXIMO_ACTIVO):
    n = len(columnas)
    _validar_restricciones(n, peso_max)
    w = pd.Series(np.full(n, 1.0 / n), index=list(columnas))
    verificar_pesos(w.to_numpy(), peso_max)
    return w


def minima_varianza(cov, peso_max=PESO_MAXIMO_ACTIVO):
    """Portafolio de mínima varianza con 0 <= w <= peso_max."""
    n = cov.shape[0]
    sigma = cov.to_numpy()
    w = _optimizar(lambda x: float(x @ sigma @ x), n, peso_max)
    w = _como_series(w, cov.index)
    verificar_pesos(w.to_numpy(), peso_max)
    return w


def maximo_sharpe(mu, cov, rf=TASA_LIBRE_RIESGO_ANUAL, peso_max=PESO_MAXIMO_ACTIVO):
    """Portafolio de máximo Sharpe con 0 <= w <= peso_max.

    Si ningún portafolio factible supera la tasa libre de riesgo (Sharpe <= 0)
    el resultado es el de menor pérdida relativa, no una inversión atractiva;
    en ese caso se registra una advertencia en el log.
    """
    _validar_entrada(mu, cov)
    n = len(mu)
    m = mu.to_numpy()
    sigma = cov.to_numpy()

    def neg_sharpe(x):
        vol = np.sqrt(max(float(x @ sigma @ x), 1e-18))
        return -(float(x @ m) - rf) / vol

    # Varios puntos de partida: el máximo Sharpe no siempre es convexo.
    candidatos = [np.full(n, 1.0 / n)]
    for i in range(n):
        e = np.full(n, (1 - peso_max) / max(n - 1, 1))
        e[i] = peso_max
        candidatos.append(e / e.sum())
    mejor, mejor_val = None, np.inf
    for x0 in candidatos:
        try:
            x = _optimizar(neg_sharpe, n, peso_max, x0=x0)
        except RuntimeError:
            continue
        val = neg_sharpe(x)
        if val < mejor_val - 1e-12:
            mejor, mejor_val = x, val
    if mejor is None:
        raise RuntimeError("El optimizador no convergió desde ningún punto inicial.")
    if -mejor_val <= 0:
        logger.warning("Máximo Sharpe <= 0 (%.4f): ningún portafolio factible "
                       "supera la tasa libre de riesgo.", -mejor_val)
    w = _como_series(mejor, mu.index)
    verificar_pesos(w.to_numpy(), peso_max)
    return w


def frontera_eficiente(mu, cov, peso_max=PESO_MAXIMO_ACTIVO, puntos=30):
    """Frontera eficiente restringida: mínima varianza para cada rendimiento
    objetivo entre el de mínima varianza y el máximo factible.

    Retorna DataFrame con columnas retorno y volatilidad.
    """
    _validar_entrada(mu, cov)
    n = len(mu)
    m = mu.to_numpy()
    sigma = cov.to_numpy()
    r_min = retorno_esperado(minima_varianza(cov, peso_max).to_numpy(), mu)

    # Rendimiento máximo factible: programa lineal resuelto con SLSQP.
    w_max = _optimizar(lambda x: -float(x @ m), n, peso_max)
    r_max = float(w_max @ m)

    filas = []
    for objetivo in np.linspace(r_min, r_max, puntos):
        extra = [{"type": "eq", "fun": lambda x, o=objetivo: float(x @ m) - o}]
        try:
            x = _optimizar(lambda x: float(x @ sigma @ x), n, peso_max,
                           restricciones_extra=extra)
        except RuntimeError:
            continue
        filas.append({"retorno": float(x @ m), "volatilidad": volatilidad(x, cov)})
    return pd.DataFrame(filas)
