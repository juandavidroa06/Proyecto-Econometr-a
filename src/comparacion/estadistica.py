"""
estadistica.py — Inferencia para comparar pronósticos (Fase 10, DEC-027)
=========================================================================

Responsabilidad única: pruebas que controlan el error por comparaciones
múltiples y la dependencia temporal.

    - ``holm``: corrección de Holm-Bonferroni de una familia de p-valores.
    - ``bootstrap_bloques``: índices de bootstrap por bloques móviles
      (preserva la dependencia de corto plazo).
    - ``model_confidence_set``: MCS de Hansen, Lunde y Nason (2011) con el
      estadístico T_max.
    - ``r2_fuera_de_muestra``: R² de Campbell y Thompson (2008) frente a una
      referencia, con intervalo bootstrap.
    - ``pesaran_timmermann``: prueba de capacidad direccional (1992).

Todas las funciones con aleatoriedad reciben una semilla explícita.
"""

import numpy as np
import pandas as pd
from scipy import stats


def holm(pvalores):
    """p-valores ajustados por Holm (controla el error de familia).

    Acepta Series o arreglo; los NaN se conservan y no cuentan en la familia.
    """
    p = pd.Series(pvalores, dtype=float)
    validos = p.dropna().sort_values()
    m = len(validos)
    ajustados = pd.Series(np.nan, index=p.index)
    acumulado = 0.0
    for k, (idx, valor) in enumerate(validos.items()):
        acumulado = max(acumulado, min(1.0, (m - k) * valor))
        ajustados[idx] = acumulado
    return ajustados


def bootstrap_bloques(n, n_remuestras, largo_bloque, semilla):
    """Matriz (n_remuestras, n) de índices por bloques móviles circulares."""
    if n < 2 or largo_bloque < 1:
        raise ValueError("n >= 2 y largo_bloque >= 1.")
    rng = np.random.default_rng(semilla)
    n_bloques = int(np.ceil(n / largo_bloque))
    inicios = rng.integers(0, n, size=(n_remuestras, n_bloques))
    desplazamientos = np.arange(largo_bloque)
    idx = (inicios[:, :, None] + desplazamientos[None, None, :]) % n
    return idx.reshape(n_remuestras, -1)[:, :n]


def model_confidence_set(perdidas, alfa=0.10, n_remuestras=2000, largo_bloque=10,
                         semilla=42):
    """Model Confidence Set con estadístico T_max.

    ``perdidas``: DataFrame (tiempo x modelos), sin faltantes. Elimina
    secuencialmente el peor modelo mientras se rechace igual capacidad
    predictiva. Retorna DataFrame por modelo con el p-valor MCS (máximo
    acumulado) y si pertenece al conjunto al nivel ``alfa``.
    """
    if not isinstance(perdidas, pd.DataFrame) or perdidas.isna().any().any():
        raise ValueError("Se esperaba un DataFrame de pérdidas sin faltantes.")
    L = perdidas.to_numpy(float)
    n, m = L.shape
    idx = bootstrap_bloques(n, n_remuestras, largo_bloque, semilla)
    medias_boot = L[idx].mean(axis=1)            # (B, m)
    medias = L.mean(axis=0)
    vivos = list(range(m))
    pvalores, orden, p_acumulado = {}, [], 0.0
    while len(vivos) > 1:
        sub = np.array(vivos)
        d = medias[sub] - medias[sub].mean()
        d_boot = medias_boot[:, sub] - medias_boot[:, sub].mean(axis=1, keepdims=True)
        var = ((d_boot - d) ** 2).mean(axis=0)
        var = np.where(var > 0, var, np.finfo(float).tiny)
        t = d / np.sqrt(var)
        t_boot = (d_boot - d) / np.sqrt(var)
        p = float((t_boot.max(axis=1) >= t.max()).mean())
        p_acumulado = max(p_acumulado, p)
        peor = int(sub[np.argmax(t)])
        pvalores[peor] = p_acumulado
        orden.append(peor)
        vivos.remove(peor)
    pvalores[vivos[0]] = 1.0
    orden.append(vivos[0])
    nombres = list(perdidas.columns)
    tabla = pd.DataFrame({
        "modelo": [nombres[i] for i in orden],
        "perdida_media": [float(medias[i]) for i in orden],
        "pvalor_mcs": [pvalores[i] for i in orden],
    })
    tabla["en_mcs"] = tabla["pvalor_mcs"] >= alfa
    return tabla.sort_values("perdida_media").reset_index(drop=True)


def r2_fuera_de_muestra(perdida_modelo, perdida_referencia, n_remuestras=2000,
                        largo_bloque=10, semilla=42, nivel=0.95):
    """R²_OS = 1 - sum(pérdida modelo) / sum(pérdida referencia).

    Con pérdida cuadrática es el R² de Campbell y Thompson. El intervalo se
    obtiene por bootstrap de bloques sobre el tiempo.
    """
    a = np.asarray(perdida_modelo, float)
    b = np.asarray(perdida_referencia, float)
    if a.shape != b.shape or np.isnan(a).any() or np.isnan(b).any():
        raise ValueError("Pérdidas de distinta forma o con faltantes.")
    r2 = 1 - a.sum() / b.sum()
    idx = bootstrap_bloques(len(a), n_remuestras, largo_bloque, semilla)
    r2_boot = 1 - a[idx].sum(axis=1) / b[idx].sum(axis=1)
    cola = (1 - nivel) / 2
    return {"r2_os": float(r2),
            "ic_inf": float(np.quantile(r2_boot, cola)),
            "ic_sup": float(np.quantile(r2_boot, 1 - cola))}


def pesaran_timmermann(observado, pronostico):
    """Prueba de Pesaran-Timmermann (1992) de acierto direccional.

    Usa solo observaciones con observado y pronóstico distintos de cero.
    H0: el signo pronosticado es independiente del observado. Retorna dict
    con tasa de acierto, estadístico, p-valor unilateral y n; si el
    pronóstico no varía de signo, el estadístico no está definido (NaN).
    """
    y = np.asarray(observado, float)
    f = np.asarray(pronostico, float)
    usar = (y != 0) & (f != 0)
    y, f = y[usar] > 0, f[usar] > 0
    n = len(y)
    if n < 10:
        raise ValueError("Muy pocas observaciones para Pesaran-Timmermann.")
    acierto = float((y == f).mean())
    py, pf = y.mean(), f.mean()
    p_estrella = py * pf + (1 - py) * (1 - pf)
    var_p = p_estrella * (1 - p_estrella) / n
    var_e = ((2 * py - 1) ** 2 * pf * (1 - pf) / n
             + (2 * pf - 1) ** 2 * py * (1 - py) / n
             + 4 * py * pf * (1 - py) * (1 - pf) / n ** 2)
    if var_p - var_e <= 0 or pf in (0.0, 1.0):
        return {"acierto": acierto, "pt_estadistico": float("nan"),
                "pt_pvalor": float("nan"), "n": n}
    pt = (acierto - p_estrella) / np.sqrt(var_p - var_e)
    return {"acierto": acierto, "pt_estadistico": float(pt),
            "pt_pvalor": float(stats.norm.sf(pt)), "n": n}
