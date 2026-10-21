"""
portafolios_pronostico.py — Portafolios construidos con pronósticos (Fase 21, DEC-046, bloque B)
================================================================================================

Responsabilidad única: pesos y simulación de estrategias que usan pronósticos
de covarianza, de volatilidad o de rendimiento. Reutiliza el motor de la
Fase 14 (DEC-032) sin cambiar sus reglas.

    B1: mínima varianza y paridad de riesgo con covarianza EWMA (λ = 0,97);
        mínima varianza con covarianza CCC-GARCH (solo universo líquido).
    B2: volatility targeting del 1/N con el resto al IBR.
    B3: cada día, las k acciones con mayor pronóstico del rendimiento del día
        siguiente, frente al 1/N diario entre las mismas acciones.

Toda estimación usa solo información hasta la fecha de rebalanceo.
"""

import logging

import numpy as np
import pandas as pd

from config.settings import DIAS_BURSATILES_ANIO, PESO_MAXIMO_ACTIVO, SECTORES
from src.backtesting import motor
from src.backtesting.fase14 import pesos_estrategia
from src.econometrics import garch
from src.optimizacion import optimizadores as opt

logger = logging.getLogger(__name__)

LAMBDA_COV = 0.97          # RiskMetrics, horizonte mensual
LAMBDA_VOL = 0.94          # RiskMetrics, horizonte diario
HORIZONTE_GARCH = 21       # días hasta el siguiente rebalanceo mensual
IBR = "IBR"


# --- B1: covarianzas pronosticadas ----------------------------------------------------

def covarianza_ewma(ventana, lam=LAMBDA_COV):
    """Covarianza EWMA de media cero (RiskMetrics), anualizada, con filas completas."""
    completos = ventana.dropna(how="any")
    n, k = completos.shape
    if n < 2 * k:
        raise ValueError("Muy pocas filas completas para la covarianza EWMA.")
    pesos = lam ** np.arange(n - 1, -1, -1, dtype=float)
    pesos /= pesos.sum()
    x = completos.to_numpy(float)
    cov = (x * pesos[:, None]).T @ x * DIAS_BURSATILES_ANIO
    return pd.DataFrame(cov, index=completos.columns, columns=completos.columns)


def varianza_garch_horizonte(historia, horizonte=HORIZONTE_GARCH):
    """Varianza diaria media de los próximos ``horizonte`` días con un GARCH(1,1)-t
    estimado con toda la ``historia`` (rendimientos simples; se ajusta en log).

    Retorna (varianza en proporción², convergió).
    """
    y = np.log1p(historia.dropna())
    res = garch.ajustar_garch(y, None, "t")
    if res.convergence_flag != 0:
        return float(historia.var(ddof=1)), False
    f = res.forecast(horizon=horizonte, reindex=False).variance.to_numpy()[-1]
    return float(f.mean()) / garch.ESCALA ** 2, True


def covarianza_ccc_garch(rend_hasta, ventana, registro=None):
    """D·R·D: varianzas GARCH (historia completa hasta la fecha) y correlación de la ventana."""
    completos = ventana.dropna(how="any")
    corr = completos.corr().to_numpy()
    var = []
    for a in completos.columns:
        v, ok = varianza_garch_horizonte(rend_hasta[a])
        if not ok:
            v = float(completos[a].var(ddof=1))
            logger.warning("GARCH sin converger (%s, %s): varianza muestral de la ventana.",
                           a, rend_hasta.index.max().date())
        if registro is not None:
            registro.append({"fecha": rend_hasta.index.max(), "activo": a, "garch_convergio": ok})
        var.append(v)
    d = np.sqrt(np.array(var) * DIAS_BURSATILES_ANIO)
    return pd.DataFrame(corr * np.outer(d, d), index=completos.columns, columns=completos.columns)


# --- B2: volatility targeting ----------------------------------------------------------

def exposicion_vol_target(rend_1n_hasta, ventana=252, lam=LAMBDA_VOL):
    """x = min(1, σ_obj / σ̂): σ̂ EWMA a un paso del 1/N con toda la historia;
    σ_obj = desviación del 1/N en los ``ventana`` días previos."""
    r = rend_1n_hasta.to_numpy(float)
    if len(r) < ventana:
        raise ValueError("Historia más corta que la ventana del volatility targeting.")
    # Se inicia con la varianza de los primeros ``ventana`` días (pronóstico del
    # día siguiente a ellos) y se actualiza con cada rendimiento posterior: al
    # final, h es la varianza pronosticada para el día siguiente al último dato.
    h = float(np.var(r[:ventana], ddof=1))
    for x in r[ventana:]:
        h = lam * h + (1 - lam) * x ** 2
    sigma_hat = float(np.sqrt(h))
    sigma_obj = float(np.std(r[-ventana:], ddof=1))
    if sigma_hat <= 0:
        raise ValueError("Volatilidad pronosticada nula.")
    return float(min(1.0, sigma_obj / sigma_hat)), sigma_obj, sigma_hat


# --- Estrategias B1–B2 en walk-forward ---------------------------------------------------

ESTRATEGIAS_B12 = ("igual", "min_var_ewma", "paridad_riesgo_ewma", "min_var_ccc_garch",
                   "vol_target_1n")


def pesos_b(estrategia, rend, activos, fecha, ventana_dias, restr, registro):
    """Pesos objetivo de la estrategia en ``fecha`` con datos hasta ``fecha``.

    Las estrategias con IBR devuelven una Series que incluye la columna ``IBR``.
    """
    ventana = motor.ventana_estimacion(rend[activos], fecha, ventana_dias)
    if estrategia == "igual":
        return pesos_estrategia("igual", ventana, restr)
    if estrategia == "min_var_ewma":
        return opt.minima_varianza(covarianza_ewma(ventana), restr)
    if estrategia == "paridad_riesgo_ewma":
        return opt.paridad_riesgo(covarianza_ewma(ventana), restr)
    if estrategia == "min_var_ccc_garch":
        hasta = rend.loc[:fecha, activos]
        return opt.minima_varianza(covarianza_ccc_garch(hasta, ventana, registro), restr)
    if estrategia == "vol_target_1n":
        w = pesos_estrategia("igual", ventana, restr)
        r_1n = rend.loc[:fecha, activos].fillna(0.0) @ w
        x, s_obj, s_hat = exposicion_vol_target(r_1n, ventana_dias)
        registro.append({"fecha": fecha, "activo": "exposicion_1n", "valor": x,
                         "sigma_obj": s_obj, "sigma_hat": s_hat})
        return pd.concat([w * x, pd.Series({IBR: 1 - x})])
    raise ValueError(f"Estrategia desconocida: {estrategia!r}")


def correr_b12(rend, rf, universos, inicio, fin, periodos, costos, ventana_dias=252):
    """Backtesting de B1–B2 con las reglas de DEC-032.

    ``universos``: {nombre: (activos, limite_sector, estrategias)}.
    Retorna dict con metricas, series netas {(universo, estrategia, costo): Series},
    pesos y registro (exposiciones del volatility targeting y convergencia GARCH).
    """
    rend = rend.copy()
    rend[IBR] = rf.reindex(rend.index)
    filas, series, pesos_g, registro = [], {}, [], []
    for nombre_u, (activos, limite, estrategias) in universos.items():
        restr = opt.Restricciones(activos, PESO_MAXIMO_ACTIVO, SECTORES, limite)
        fechas = motor.fechas_rebalanceo(rend.index, inicio, fin, "M")
        for estrategia in estrategias:
            objetivos = {}
            for f in fechas:
                w = pesos_b(estrategia, rend, activos, f, ventana_dias, restr, registro)
                objetivos[f] = w.reindex(activos + [IBR]).fillna(0.0)
                pesos_g.append({"universo": nombre_u, "estrategia": estrategia, "fecha": f,
                                **objetivos[f].to_dict()})
            for nombre_c, c in costos.items():
                diario, _ = motor.simular(rend, objetivos, c, fin, sin_costo=(IBR,))
                series[(nombre_u, estrategia, nombre_c)] = diario["neto"]
                for periodo, (ini, fin_p) in periodos.items():
                    filas.append({"universo": nombre_u, "estrategia": estrategia,
                                  "costo": nombre_c, "periodo": periodo,
                                  **motor.metricas(diario["neto"].loc[ini:fin_p], rf)})
    return {"metricas": pd.DataFrame(filas), "series": series,
            "pesos": pd.DataFrame(pesos_g), "registro": pd.DataFrame(registro)}


# --- B3: señales diarias de rendimiento ---------------------------------------------------

def simular_senales(pron, modelo, k, costo):
    """Cartera diaria: k acciones con mayor pronóstico (o todas, si ``modelo`` es None).

    ``pron``: DataFrame con fecha_objetivo, empresa, objetivo (rendimiento log
    realizado ese día) y la columna del modelo (pronóstico hecho al cierre
    anterior). Retorna Series de rendimiento neto por fecha y la rotación media.
    """
    netos, rotaciones = {}, []
    w_prev = pd.Series(dtype=float)
    for fecha, g in pron.sort_values("fecha_objetivo").groupby("fecha_objetivo", sort=True):
        g = g.set_index("empresa")
        if modelo is None:
            elegidas = list(g.index)
        else:
            orden = g[modelo].sort_values(ascending=False, kind="mergesort")
            elegidas = list(orden.index[:k])
        w = pd.Series(1.0 / len(elegidas), index=elegidas)
        rot = float(w.sub(w_prev, fill_value=0.0).abs().sum()) if len(w_prev) else 1.0
        r = np.expm1(g.loc[elegidas, "objetivo"])
        bruto = float((w * r).sum())
        netos[pd.Timestamp(fecha)] = (1 + bruto) * (1 - costo * rot) - 1
        rotaciones.append(rot)
        # Deriva de pesos tras el rendimiento del día (base de la rotación siguiente).
        w_prev = w * (1 + r) / (1 + bruto)
    return pd.Series(netos).sort_index(), float(np.mean(rotaciones[1:])) if len(rotaciones) > 1 else 1.0
