"""
medidas.py — VaR y Expected Shortfall a un día (Fase 11, DEC-028)
==================================================================

Responsabilidad única: calcular VaR y ES por cuatro métodos, cada día con
información hasta el día anterior.

Convenciones:
    - Se trabaja con rendimientos SIMPLES R_t; la pérdida es L_t = -R_t.
    - VaR y ES se expresan como números positivos (pérdida).
    - ``alfa`` es la probabilidad de la cola (0.01 -> VaR 99 %).
    - Media condicional cero en el horizonte de un día (la Fase 10 no
      encuentra un pronóstico de la media mejor que el cero).

Métodos:
    historica : cuantil empírico de una ventana móvil de ``ventana`` días.
    ewma_normal: normal con volatilidad EWMA (RiskMetrics).
    garch_t   : GARCH(1,1) con innovaciones t (parámetros de entrenamiento).
    fhs       : simulación histórica filtrada; residuos R/sigma_EWMA de
                entrenamiento (fijos) escalados por la volatilidad EWMA de t.
"""

import numpy as np
import pandas as pd
from scipy import stats

from src.econometrics import garch

METODOS = ("historica", "ewma_normal", "garch_t", "fhs")


def _validar(train, validacion):
    for nombre, s in (("train", train), ("validacion", validacion)):
        if not isinstance(s, pd.Series) or s.isna().any():
            raise ValueError(f"{nombre}: se esperaba una Series sin faltantes.")
    if not train.index.max() < validacion.index.min():
        raise ValueError("Leakage: validación debe empezar después de train.")


def cola_empirica(muestra, alfa):
    """(VaR, ES) empíricos de una muestra de rendimientos (o residuos).

    Se usan las k = ceil(alfa * n) peores observaciones: VaR = -x_(k) y
    ES = -media(x_(1), ..., x_(k)). A diferencia de "x <= cuantil", esta
    definición no depende de los empates, que son frecuentes porque los
    precios de la BVC se mueven en saltos discretos (DEC-031).
    """
    x = np.sort(np.asarray(muestra, float))
    if len(x) == 0 or np.isnan(x).any():
        raise ValueError("Muestra vacía o con faltantes.")
    k = max(int(np.ceil(alfa * len(x))), 1)
    return -x[k - 1], -x[:k].mean()


def historica(train, validacion, alfa, ventana=250):
    """Simulación histórica con ventana móvil de los ``ventana`` días previos."""
    _validar(train, validacion)
    if len(train) < ventana:
        raise ValueError("Entrenamiento más corto que la ventana.")
    completa = pd.concat([train, validacion]).to_numpy()
    n_tr = len(train)
    var, es = [], []
    for i in range(len(validacion)):
        fin = n_tr + i                              # excluye el día pronosticado
        v, e = cola_empirica(completa[fin - ventana:fin], alfa)
        var.append(v)
        es.append(e)
    return pd.DataFrame({"var": var, "es": es}, index=validacion.index)


def _sigma_ewma(train, validacion, lam):
    """Volatilidad EWMA (escala original) para train y validación, a un paso."""
    h_val = garch.varianza_ewma(train, validacion, lam) / garch.ESCALA ** 2
    # Para los residuos de entrenamiento se recorre train con la misma regla.
    y = train.to_numpy()
    h = np.empty(len(y))
    h[0] = y.var(ddof=1)
    for t in range(1, len(y)):
        h[t] = lam * h[t - 1] + (1 - lam) * y[t - 1] ** 2
    return pd.Series(np.sqrt(h), index=train.index), np.sqrt(h_val)


def ewma_normal(train, validacion, alfa, lam=0.94):
    _validar(train, validacion)
    _, sigma = _sigma_ewma(train, validacion, lam)
    z = stats.norm.ppf(alfa)
    return pd.DataFrame({"var": -z * sigma,
                         "es": sigma * stats.norm.pdf(z) / alfa}, index=validacion.index)


def _t_estandarizada(alfa, nu):
    """Cuantil y ES (positivos) de una t con varianza unitaria."""
    if nu <= 2:
        raise ValueError(f"nu = {nu:.3f} <= 2: varianza infinita, VaR-t no definido.")
    escala = np.sqrt((nu - 2) / nu)
    q = stats.t.ppf(alfa, nu)
    es = stats.t.pdf(q, nu) / alfa * (nu + q ** 2) / (nu - 1)
    return -q * escala, es * escala


def garch_t(train, validacion, alfa):
    """GARCH(1,1)-t estimado con train; varianza a un paso en validación."""
    _validar(train, validacion)
    res = garch.ajustar_garch(train, validacion, "t")
    if res.convergence_flag != 0:
        raise RuntimeError("El GARCH no convergió.")
    sigma = np.sqrt(garch.pronostico_varianza_un_paso(res, train, validacion)) / garch.ESCALA
    var_z, es_z = _t_estandarizada(alfa, float(res.params["nu"]))
    return pd.DataFrame({"var": var_z * sigma, "es": es_z * sigma},
                        index=validacion.index)


def fhs(train, validacion, alfa, lam=0.94):
    """Simulación histórica filtrada con residuos estandarizados de train."""
    _validar(train, validacion)
    sigma_tr, sigma = _sigma_ewma(train, validacion, lam)
    z = (train / sigma_tr).to_numpy()
    var_z, es_z = cola_empirica(z, alfa)
    return pd.DataFrame({"var": var_z * sigma, "es": es_z * sigma},
                        index=validacion.index)


def calcular(metodo, train, validacion, alfa):
    funciones = {"historica": historica, "ewma_normal": ewma_normal,
                 "garch_t": garch_t, "fhs": fhs}
    if metodo not in funciones:
        raise ValueError(f"Método desconocido: {metodo!r}")
    return funciones[metodo](train, validacion, alfa)
