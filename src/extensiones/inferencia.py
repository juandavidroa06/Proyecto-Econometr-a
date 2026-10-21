"""
inferencia.py — Pruebas estadísticas adicionales (Fase 21, plan DEC-046, bloque A)
==================================================================================

Responsabilidad única: pruebas de inferencia que complementan las de la
Fase 10 y la Fase 14. No lee datos ni escribe archivos.

    - ``bootstrap_estacionario``: índices de Politis y Romano (1994).
    - ``prueba_spa``: Superior Predictive Ability de Hansen (2005) y Reality
      Check de White (2000): ¿algún modelo supera a la referencia?
    - ``direccional_hac``: acierto direccional (núcleo de Pesaran-Timmermann)
      con varianza de Newey-West sobre sumas por fecha, robusta a la
      dependencia entre acciones del mismo día.
    - ``acerbi_szekely_z2``: prueba del Expected Shortfall (Acerbi y Székely,
      2014) con p-valor por simulación de la distribución predictiva.
    - ``sharpe_probabilistico`` y ``sharpe_deflactado``: PSR y DSR (Bailey y
      López de Prado, 2012 y 2014).
    - ``diferencia_sharpe_hac``: prueba de Ledoit y Wolf (2008) con HAC.

Toda función con aleatoriedad recibe una semilla explícita.
"""

import numpy as np
import pandas as pd
from scipy import stats

EULER_GAMMA = 0.5772156649015329


def rezago_newey_west(n):
    """Rezago automático ⌊4 (n/100)^{2/9}⌋ (Newey y West, 1994)."""
    if n < 2:
        raise ValueError("Se necesitan al menos 2 observaciones.")
    return int(np.floor(4 * (n / 100) ** (2 / 9)))


def varianza_largo_plazo(x, rezago=None):
    """Varianza de largo plazo (Bartlett) de una serie o de un arreglo (n, k).

    Para una serie devuelve un escalar; para (n, k), la matriz k x k.
    """
    x = np.asarray(x, float)
    vector = x.ndim == 1
    if vector:
        x = x[:, None]
    if np.isnan(x).any():
        raise ValueError("La serie tiene faltantes.")
    n = len(x)
    L = rezago_newey_west(n) if rezago is None else int(rezago)
    xc = x - x.mean(axis=0)
    S = xc.T @ xc / n
    for j in range(1, L + 1):
        g = xc[j:].T @ xc[:-j] / n
        S += (1 - j / (L + 1)) * (g + g.T)
    return float(S[0, 0]) if vector else S


# --- A1: SPA y Reality Check ----------------------------------------------------------

def bootstrap_estacionario(n, n_remuestras, bloque_medio, semilla):
    """Matriz (n_remuestras, n) de índices del bootstrap estacionario circular.

    Cada posición continúa el bloque anterior con probabilidad 1 - 1/bloque_medio
    o empieza un bloque nuevo en un punto al azar.
    """
    if n < 2 or bloque_medio < 1:
        raise ValueError("n >= 2 y bloque_medio >= 1.")
    rng = np.random.default_rng(semilla)
    p = 1.0 / bloque_medio
    idx = np.empty((n_remuestras, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, n_remuestras)
    nuevo = rng.random((n_remuestras, n)) < p
    inicios = rng.integers(0, n, (n_remuestras, n))
    for t in range(1, n):
        idx[:, t] = np.where(nuevo[:, t], inicios[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def prueba_spa(perdida_referencia, perdidas_modelos, n_remuestras=5000, bloque_medio=10,
               semilla=42):
    """SPA de Hansen (2005) y Reality Check de White (2000).

    ``perdida_referencia``: Series (tiempo); ``perdidas_modelos``: DataFrame
    (tiempo x modelos), mismo índice, sin faltantes. H0: ningún modelo tiene
    menor pérdida esperada que la referencia. Retorna dict con los p-valores
    SPA consistente, inferior y superior, el del Reality Check, el estadístico
    y la tabla por modelo (mejora media y t de cada modelo).
    """
    if not isinstance(perdidas_modelos, pd.DataFrame):
        raise ValueError("perdidas_modelos debe ser un DataFrame.")
    ref = pd.Series(perdida_referencia)
    if not ref.index.equals(perdidas_modelos.index):
        raise ValueError("Referencia y modelos deben tener el mismo índice.")
    d = (ref.to_numpy(float)[:, None] - perdidas_modelos.to_numpy(float))
    if np.isnan(d).any():
        raise ValueError("Pérdidas con faltantes.")
    n, m = d.shape
    if n < 10:
        raise ValueError("Muy pocas observaciones para la prueba SPA.")
    dbar = d.mean(axis=0)
    idx = bootstrap_estacionario(n, n_remuestras, bloque_medio, semilla)
    dbar_b = np.stack([d[i].mean(axis=0) for i in idx])            # (B, m)
    raiz_n = np.sqrt(n)
    omega = np.sqrt(((raiz_n * (dbar_b - dbar)) ** 2).mean(axis=0))
    omega = np.where(omega > 0, omega, np.finfo(float).tiny)
    t_obs = raiz_n * dbar / omega
    T = max(float(t_obs.max()), 0.0)
    umbral = -np.sqrt(2 * np.log(np.log(n)))
    centros = {"consistente": np.where(t_obs >= umbral, dbar, 0.0),
               "inferior": np.maximum(dbar, 0.0),
               "superior": dbar}
    pvalores = {}
    for nombre, mu in centros.items():
        t_b = raiz_n * (dbar_b - mu) / omega
        T_b = np.maximum(t_b.max(axis=1), 0.0)
        pvalores[nombre] = float((T_b >= T).mean())
    # Reality Check de White: estadístico sin estandarizar, centrado en dbar.
    v = raiz_n * dbar.max()
    v_b = (raiz_n * (dbar_b - dbar)).max(axis=1)
    p_rc = float((v_b >= v).mean())
    tabla = pd.DataFrame({"modelo": perdidas_modelos.columns, "mejora_media": dbar,
                          "t_spa": t_obs}).sort_values("t_spa", ascending=False)
    return {"estadistico": T, "pvalor_spa_consistente": pvalores["consistente"],
            "pvalor_spa_inferior": pvalores["inferior"],
            "pvalor_spa_superior": pvalores["superior"], "pvalor_reality_check": p_rc,
            "n": n, "modelos": tabla.reset_index(drop=True)}


# --- A2: acierto direccional robusto ------------------------------------------------

def direccional_hac(fechas, observado, pronostico):
    """Acierto direccional con dependencia entre acciones del mismo día.

    Usa las filas con observado y pronóstico distintos de cero (como
    Pesaran-Timmermann). u = (1{y>0} - p_y)(1{f>0} - p_f) se suma por fecha y
    se prueba E[u] = 0 frente a E[u] > 0 con la varianza de Newey-West de las
    sumas diarias. Retorna dict con acierto, estadístico, p-valor unilateral,
    número de filas y de fechas; NaN si el pronóstico no cambia de signo.
    """
    df = pd.DataFrame({"fecha": pd.to_datetime(pd.Series(fechas).to_numpy()),
                       "y": np.asarray(observado, float), "f": np.asarray(pronostico, float)})
    if df[["y", "f"]].isna().any().any():
        raise ValueError("Observado o pronóstico con faltantes.")
    df = df[(df["y"] != 0) & (df["f"] != 0)]
    Y, F = (df["y"] > 0).astype(float), (df["f"] > 0).astype(float)
    n = len(df)
    if n < 10:
        raise ValueError("Muy pocas observaciones para la prueba direccional.")
    acierto = float((Y == F).mean())
    py, pf = Y.mean(), F.mean()
    sin_variacion = pf in (0.0, 1.0) or py in (0.0, 1.0)
    u = (Y - py) * (F - pf)
    U = u.groupby(df["fecha"]).sum().sort_index()
    T = len(U)
    if sin_variacion or T < 10:
        return {"acierto": acierto, "estadistico": np.nan, "pvalor": np.nan, "n": n, "fechas": T}
    lrv = varianza_largo_plazo(U.to_numpy())
    if lrv <= 0:
        return {"acierto": acierto, "estadistico": np.nan, "pvalor": np.nan, "n": n, "fechas": T}
    z = U.mean() / np.sqrt(lrv / T)
    return {"acierto": acierto, "estadistico": float(z), "pvalor": float(stats.norm.sf(z)),
            "n": n, "fechas": T}


# --- A3: prueba del Expected Shortfall -------------------------------------------------

def z2(rendimiento, var, es, alfa):
    """Estadístico Z2 de Acerbi y Székely. Acepta arreglos (T,) o (S, T)."""
    x = np.asarray(rendimiento, float)
    v = np.asarray(var, float)
    e = np.asarray(es, float)
    if (v <= 0).any() or (e <= 0).any():
        raise ValueError("VaR y ES deben ser positivos (pérdidas).")
    T = x.shape[-1]
    exceso = x < -v
    return (x * exceso / e).sum(axis=-1) / (T * alfa) + 1


def acerbi_szekely_z2(rendimiento, var, es, alfa, simular, n_sim=5000, semilla=42):
    """Z2 observado y p-valor unilateral (ES subestimado si Z2 << 0).

    ``simular(rng, n_sim)`` devuelve una matriz (n_sim, T) de rendimientos
    simulados de la distribución predictiva del método, día por día.
    """
    x = np.asarray(rendimiento, float)
    if np.isnan(x).any() or not (len(x) == len(var) == len(es)):
        raise ValueError("Series de distinta longitud o con faltantes.")
    obs = float(z2(x, var, es, alfa))
    rng = np.random.default_rng(semilla)
    sim = np.asarray(simular(rng, n_sim), float)
    if sim.shape != (n_sim, len(x)):
        raise ValueError(f"El simulador devolvió {sim.shape}, se esperaba {(n_sim, len(x))}.")
    z_sim = z2(sim, np.broadcast_to(var, sim.shape), np.broadcast_to(es, sim.shape), alfa)
    return {"z2": obs, "pvalor": float((z_sim <= obs).mean()),
            "z2_sim_medio": float(z_sim.mean())}


# --- A4: Sharpe ----------------------------------------------------------------------

def sharpe_probabilistico(exceso, umbral=0.0):
    """PSR: probabilidad de que el Sharpe (diario) verdadero supere ``umbral``."""
    x = np.asarray(exceso, float)
    if np.isnan(x).any() or len(x) < 10:
        raise ValueError("Serie corta o con faltantes.")
    sd = x.std(ddof=1)
    if sd <= 0:
        return float("nan")
    sr = x.mean() / sd
    g3 = stats.skew(x)
    g4 = stats.kurtosis(x, fisher=False)
    denom = 1 - g3 * sr + (g4 - 1) / 4 * sr ** 2
    if denom <= 0:
        return float("nan")
    return float(stats.norm.cdf((sr - umbral) * np.sqrt(len(x) - 1) / np.sqrt(denom)))


def umbral_deflactado(sharpes_diarios):
    """Sharpe esperado del máximo de N pruebas sin habilidad (Bailey y López de Prado)."""
    s = np.asarray(sharpes_diarios, float)
    N = len(s)
    if N < 2:
        raise ValueError("El Sharpe deflactado necesita al menos 2 estrategias.")
    v = s.var(ddof=1)
    return float(np.sqrt(v) * ((1 - EULER_GAMMA) * stats.norm.ppf(1 - 1 / N)
                               + EULER_GAMMA * stats.norm.ppf(1 - 1 / (N * np.e))))


def sharpe_deflactado(exceso, sharpes_diarios_familia):
    """DSR: PSR con el umbral del máximo esperado de la familia de estrategias."""
    return sharpe_probabilistico(exceso, umbral_deflactado(sharpes_diarios_familia))


def diferencia_sharpe_hac(exceso_a, exceso_b, dias=252, rezago=None):
    """Prueba de Ledoit y Wolf (2008) de igualdad de Sharpe con varianza HAC.

    Retorna la diferencia anualizada, su error estándar y el p-valor bilateral.
    """
    a = np.asarray(exceso_a, float)
    b = np.asarray(exceso_b, float)
    if a.shape != b.shape or np.isnan(a).any() or np.isnan(b).any():
        raise ValueError("Series de distinta longitud o con faltantes.")
    n = len(a)
    mu_a, mu_b = a.mean(), b.mean()
    g_a, g_b = (a ** 2).mean(), (b ** 2).mean()
    va, vb = g_a - mu_a ** 2, g_b - mu_b ** 2
    if va <= 0 or vb <= 0:
        raise ValueError("Varianza nula en alguna serie.")
    dif = mu_a / np.sqrt(va) - mu_b / np.sqrt(vb)
    grad = np.array([g_a / va ** 1.5, -g_b / vb ** 1.5,
                     -mu_a / (2 * va ** 1.5), mu_b / (2 * vb ** 1.5)])
    y = np.column_stack([a - mu_a, b - mu_b, a ** 2 - g_a, b ** 2 - g_b])
    psi = varianza_largo_plazo(y, rezago)
    se = float(np.sqrt(grad @ psi @ grad / n))
    p = float(2 * stats.norm.sf(abs(dif / se))) if se > 0 else float("nan")
    return {"dif_sharpe": float(dif * np.sqrt(dias)), "error_estandar": se * np.sqrt(dias),
            "pvalor": p}
