"""
optimizadores.py — Portafolios con restricciones realistas (Fases 12–13, DEC-031)
==================================================================================

Responsabilidad única: calcular pesos óptimos dados insumos YA estimados
(media, covarianza o escenarios). No lee archivos ni estima parámetros.

Restricciones comunes (todas verificadas al final; si no se cumplen o el
optimizador no converge, se lanza un error en vez de devolver pesos):
    sum(w) = 1,  0 <= w_i <= peso_max,  sum(w_i, i en sector s) <= limite_s.

Portafolios:
    minima_varianza, maximo_sharpe, minimo_cvar (programa lineal de
    Rockafellar-Uryasev), paridad_riesgo (contribuciones al riesgo lo más
    iguales posible dentro de las restricciones) y maximo_retorno con
    volatilidad acotada.
"""

import numpy as np
import pandas as pd
from scipy.optimize import linprog, minimize

TOL = 1e-6


class Restricciones:
    """Peso máximo por activo y límites por sector, validados contra los activos."""

    def __init__(self, activos, peso_max, sectores=None, limite_sector=None):
        self.activos = list(activos)
        self.peso_max = float(peso_max)
        self.sectores = dict(sectores or {})
        self.limite_sector = limite_sector
        faltan = [a for a in self.activos if self.sectores and a not in self.sectores]
        if faltan:
            raise ValueError(f"Activos sin sector asignado: {faltan}")
        if not 0 < self.peso_max <= 1:
            raise ValueError("peso_max debe estar en (0, 1].")
        if len(self.activos) * self.peso_max < 1 - TOL:
            raise ValueError("Infactible: el peso máximo no permite sumar 1.")

    @property
    def n(self):
        return len(self.activos)

    def grupos(self):
        """{sector: índices} de los sectores con límite efectivo (< 1)."""
        if self.limite_sector is None:
            return {}
        g = {}
        for i, a in enumerate(self.activos):
            g.setdefault(self.sectores[a], []).append(i)
        return {s: idx for s, idx in g.items() if self.limite_sector < 1}

    def slsqp(self):
        cons = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
        for idx in self.grupos().values():
            cons.append({"type": "ineq",
                         "fun": lambda w, idx=idx: self.limite_sector - np.sum(w[idx])})
        return cons

    def cotas(self):
        return [(0.0, self.peso_max)] * self.n

    def verificar(self, w):
        w = np.asarray(w, float)
        if abs(w.sum() - 1) > 1e-6 or (w < -1e-8).any() or (w > self.peso_max + 1e-6).any():
            raise ValueError("Los pesos violan suma 1, no negatividad o el peso máximo.")
        for s, idx in self.grupos().items():
            if w[idx].sum() > self.limite_sector + 1e-6:
                raise ValueError(f"El sector {s} supera su límite.")

    def exposicion_sectorial(self, w):
        expo = {}
        for a, peso in zip(self.activos, np.asarray(w, float)):
            s = self.sectores.get(a, "sin_sector")
            expo[s] = expo.get(s, 0.0) + float(peso)
        return expo

    def punto_inicial(self):
        """Punto factible: 1/N si lo es; si no, se resuelve un PL de factibilidad."""
        w = np.full(self.n, 1.0 / self.n)
        try:
            self.verificar(w)
            return w
        except ValueError:
            pass
        A_ub, b_ub = self._ineq_lineales()
        res = linprog(np.zeros(self.n), A_ub=A_ub, b_ub=b_ub,
                      A_eq=np.ones((1, self.n)), b_eq=[1.0], bounds=self.cotas(),
                      method="highs")
        if not res.success:
            raise ValueError("Las restricciones son infactibles.")
        return res.x

    def _ineq_lineales(self, n_extra=0):
        filas, b = [], []
        for idx in self.grupos().values():
            fila = np.zeros(self.n + n_extra)
            fila[idx] = 1.0
            filas.append(fila)
            b.append(self.limite_sector)
        return (np.array(filas) if filas else None), (np.array(b) if b else None)


def _resolver(objetivo, r, restricciones_extra=(), x0=None):
    x0 = r.punto_inicial() if x0 is None else x0
    res = minimize(objetivo, x0, method="SLSQP", bounds=r.cotas(),
                   constraints=r.slsqp() + list(restricciones_extra),
                   options={"maxiter": 2000, "ftol": 1e-12})
    if not res.success:
        raise RuntimeError(f"El optimizador no convergió: {res.message}")
    w = np.clip(res.x, 0, None)
    w = w / w.sum()
    r.verificar(w)
    return pd.Series(w, index=r.activos)


def _validar_cov(cov, r):
    if list(cov.index) != r.activos or list(cov.columns) != r.activos:
        raise ValueError("La covarianza no coincide con los activos de las restricciones.")
    if not np.isfinite(cov.to_numpy()).all():
        raise ValueError("Covarianza con valores no finitos.")
    return cov.to_numpy()


def minima_varianza(cov, r):
    S = _validar_cov(cov, r)
    return _resolver(lambda w: float(w @ S @ w), r)


def maximo_sharpe(mu, cov, rf, r):
    """Máximo (mu'w - rf) / sqrt(w'Σw) con varios puntos de partida."""
    S = _validar_cov(cov, r)
    m = mu.reindex(r.activos).to_numpy()

    def neg(w):
        return -(float(w @ m) - rf) / np.sqrt(max(float(w @ S @ w), 1e-18))

    candidatos = [r.punto_inicial()]
    for i in range(r.n):
        e = np.full(r.n, (1 - r.peso_max) / max(r.n - 1, 1))
        e[i] = r.peso_max
        candidatos.append(e / e.sum())
    mejor, valor = None, np.inf
    for x0 in candidatos:
        try:
            w = _resolver(neg, r, x0=x0)
        except (RuntimeError, ValueError):
            continue
        if neg(w.to_numpy()) < valor - 1e-12:
            mejor, valor = w, neg(w.to_numpy())
    if mejor is None:
        raise RuntimeError("Máximo Sharpe: ningún punto de partida convergió.")
    return mejor


def minimo_cvar(escenarios, beta, r):
    """Mínimo CVaR_beta de la pérdida -R w (Rockafellar y Uryasev, 2000).

    Variables: w (n), zeta (VaR), u_t >= 0 (T). Programa lineal con HiGHS.
    """
    if list(escenarios.columns) != r.activos or escenarios.isna().any().any():
        raise ValueError("Escenarios incompletos o con activos distintos.")
    R = escenarios.to_numpy(float)
    T, n = R.shape
    c = np.concatenate([np.zeros(n), [1.0], np.full(T, 1.0 / ((1 - beta) * T))])
    # u_t >= -R_t w - zeta  <=>  -R_t w - zeta - u_t <= 0
    A_cvar = np.hstack([-R, -np.ones((T, 1)), -np.eye(T)])
    A_sec, b_sec = r._ineq_lineales(n_extra=1 + T)
    A_ub = A_cvar if A_sec is None else np.vstack([A_cvar, A_sec])
    b_ub = np.zeros(T) if b_sec is None else np.concatenate([np.zeros(T), b_sec])
    A_eq = np.concatenate([np.ones(n), [0.0], np.zeros(T)])[None, :]
    cotas = r.cotas() + [(None, None)] + [(0, None)] * T
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=[1.0], bounds=cotas,
                  method="highs")
    if not res.success:
        raise RuntimeError(f"Mínimo CVaR: {res.message}")
    w = np.clip(res.x[:n], 0, None)
    w = w / w.sum()
    r.verificar(w)
    return pd.Series(w, index=r.activos)


def contribuciones_riesgo(w, cov):
    """Proporción de la varianza del portafolio aportada por cada activo."""
    w = np.asarray(w, float)
    S = cov.to_numpy()
    total = float(w @ S @ w)
    return w * (S @ w) / total


def paridad_riesgo(cov, r):
    """Contribuciones al riesgo lo más cercanas a 1/n dentro de las restricciones."""
    S = _validar_cov(cov, r)
    objetivo = np.full(r.n, 1.0 / r.n)

    def desviacion(w):
        total = float(w @ S @ w)
        rc = w * (S @ w) / max(total, 1e-18)
        return float(((rc - objetivo) ** 2).sum())

    return _resolver(desviacion, r)


def maximo_retorno(mu, cov, vol_max, r):
    """Máximo mu'w con volatilidad anual <= vol_max."""
    S = _validar_cov(cov, r)
    m = mu.reindex(r.activos).to_numpy()
    extra = [{"type": "ineq", "fun": lambda w: vol_max ** 2 - float(w @ S @ w)}]
    x0 = minima_varianza(cov, r).to_numpy()   # factible si vol_max >= vol mínima
    if np.sqrt(x0 @ S @ x0) > vol_max + 1e-9:
        raise ValueError("vol_max es menor que la volatilidad mínima alcanzable.")
    return _resolver(lambda w: -float(w @ m), r, restricciones_extra=extra, x0=x0)
