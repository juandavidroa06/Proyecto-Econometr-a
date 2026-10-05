"""
motor.py — Simulación walk-forward de portafolios (Fase 14, DEC-032)
====================================================================

Responsabilidad única: dado un calendario de rebalanceo y pesos objetivo
ya calculados con información pasada, simular la riqueza diaria con deriva
de pesos y costos de transacción.

Reglas (DEC-032):
    - Los pesos objetivo de la fecha d se calculan con datos hasta d y rigen
      desde el día siguiente.
    - Entre rebalanceos los pesos derivan con los precios.
    - Costo del día de rebalanceo = c x rotación, con rotación =
      sum |w_objetivo - w_derivado|; la compra inicial cuenta como rotación 1.
    - Rendimientos faltantes (días sin precio) valen 0 para la valoración.
"""

import numpy as np
import pandas as pd


def fechas_rebalanceo(indice, inicio, fin, frecuencia="M"):
    """Último día bursátil de cada mes (``M``) o trimestre (``Q``) en [inicio, fin]."""
    idx = pd.DatetimeIndex(indice)
    idx = idx[(idx >= pd.Timestamp(inicio)) & (idx <= pd.Timestamp(fin))]
    if frecuencia not in ("M", "Q"):
        raise ValueError("frecuencia debe ser 'M' o 'Q'.")
    periodo = idx.to_period("M" if frecuencia == "M" else "Q")
    ultimos = pd.Series(idx, index=idx).groupby(periodo).max()
    return pd.DatetimeIndex(ultimos.to_numpy())


def ventana_estimacion(rend, fecha, largo):
    """Las ``largo`` filas del índice que terminan en ``fecha`` (inclusive)."""
    pos = rend.index.get_loc(fecha)
    if pos + 1 < largo:
        raise ValueError(f"No hay {largo} días de historia antes de {fecha.date()}.")
    return rend.iloc[pos + 1 - largo:pos + 1]


def simular(rend, pesos_objetivo, costo, fin):
    """Simula la estrategia.

    ``rend``: rendimientos SIMPLES diarios (DataFrame, puede tener NaN).
    ``pesos_objetivo``: dict {fecha_rebalanceo: Series de pesos}.
    ``costo``: costo por lado (proporción, p. ej. 0.002 = 20 pb).
    Retorna (DataFrame diario con rendimiento neto, bruto, costo y rotación;
    Series de rotación por rebalanceo).
    """
    fechas = sorted(pesos_objetivo)
    if not fechas:
        raise ValueError("No hay fechas de rebalanceo.")
    activos = list(pesos_objetivo[fechas[0]].index)
    for f in fechas:
        w = pesos_objetivo[f]
        if list(w.index) != activos or abs(w.sum() - 1) > 1e-6 or (w < -1e-9).any():
            raise ValueError(f"Pesos inválidos en {f.date()}.")
    r = rend[activos].fillna(0.0)
    dias = r.index[(r.index > fechas[0]) & (r.index <= pd.Timestamp(fin))]
    if len(dias) == 0:
        raise ValueError("No hay días para simular después del primer rebalanceo.")

    w = pesos_objetivo[fechas[0]].to_numpy(float)
    rotaciones = {fechas[0]: 1.0}                    # compra inicial desde efectivo
    # La compra inicial ocurre al cierre de fechas[0], que no se simula: su
    # costo se descuenta en el primer día simulado.
    costo_inicial = costo * 1.0
    siguiente = iter(fechas[1:])
    proximo = next(siguiente, None)
    filas = []
    for dia in dias:
        ri = r.loc[dia].to_numpy(float)
        bruto = float(w @ ri)                        # se gana con los pesos vigentes
        w = w * (1 + ri) / (1 + bruto)               # deriva de pesos
        c_dia = costo_inicial
        costo_inicial = 0.0
        if proximo is not None and dia == proximo:
            # Rebalanceo al cierre del día: el costo se descuenta ESE día.
            objetivo = pesos_objetivo[proximo].to_numpy(float)
            rot = float(np.abs(objetivo - w).sum())
            rotaciones[proximo] = rot
            c_dia += costo * rot
            w = objetivo
            proximo = next(siguiente, None)
        neto = (1 + bruto) * (1 - c_dia) - 1
        filas.append({"Date": dia, "bruto": bruto, "costo": c_dia, "neto": neto})
    diario = pd.DataFrame(filas).set_index("Date")
    return diario, pd.Series(rotaciones, name="rotacion")


def metricas(neto, rf_diario, dias=252):
    """Métricas de una serie de rendimientos netos diarios."""
    rf = rf_diario.reindex(neto.index)
    if rf.isna().any():
        raise ValueError("Falta la tasa libre de riesgo en algunos días.")
    exceso = neto - rf
    riqueza = (1 + neto).cumprod()
    pico = riqueza.cummax()
    x = np.sort(neto.to_numpy())
    k = max(int(np.ceil(0.05 * len(x))), 1)
    return {
        "dias": int(len(neto)),
        "retorno_anual": float((1 + neto).prod() ** (dias / len(neto)) - 1),
        "volatilidad_anual": float(neto.std(ddof=1) * np.sqrt(dias)),
        # Sin variación del exceso (p. ej. la propia tasa libre) el Sharpe no está definido.
        "sharpe": (float(exceso.mean() / exceso.std(ddof=1) * np.sqrt(dias))
                   if exceso.std(ddof=1) > 0 else float("nan")),
        "max_drawdown": float((riqueza / pico - 1).min()),
        "cvar95_diario": float(-x[:k].mean()),
        "valor_final": float(riqueza.iloc[-1]),
    }


def diferencia_sharpe(exceso_a, exceso_b, n_remuestras, largo_bloque, semilla, dias=252):
    """Sharpe(a) - Sharpe(b) con bootstrap por bloques sobre los mismos días.

    Retorna dict con la diferencia, IC 95 % percentil y p-valor bilateral
    (proporción de réplicas del lado contrario de cero, x2).
    """
    from src.comparacion.estadistica import bootstrap_bloques

    a = np.asarray(exceso_a, float)
    b = np.asarray(exceso_b, float)
    if a.shape != b.shape:
        raise ValueError("Series de distinta longitud.")
    sh = lambda x: x.mean(axis=-1) / x.std(axis=-1, ddof=1) * np.sqrt(dias)
    diff = float(sh(a) - sh(b))
    idx = bootstrap_bloques(len(a), n_remuestras, largo_bloque, semilla)
    d_boot = sh(a[idx]) - sh(b[idx])
    p = 2 * min(float((d_boot <= 0).mean()), float((d_boot >= 0).mean()))
    return {"dif_sharpe": diff, "ic95_inf": float(np.quantile(d_boot, 0.025)),
            "ic95_sup": float(np.quantile(d_boot, 0.975)), "pvalor": min(p, 1.0)}
