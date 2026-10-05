"""
invalid_data.py — Precios inválidos por error de la fuente (DEC-022)
=====================================================================

Responsabilidad única: marcar como inválidas fechas cuyo precio se
demostró erróneo en la fuente y calcular rendimientos que las salten.

Reglas (AGENTS.md, sección 5):
    - No se inventa ningún valor: el precio inválido queda NaN con bandera.
    - No se usa información futura: el rendimiento del primer día válido
      posterior es el rendimiento acumulado desde el último día válido
      anterior (p. ej. 2 -> 6 de mayo de 2024), igual al que observaría un
      inversor que descarta el precio erróneo.
    - Los NaN que ya existían (días sin precio) se conservan como estaban.
"""

import numpy as np
import pandas as pd


def bandera_dato_invalido(precios, fechas):
    """DataFrame booleano (mismo índice y columnas que ``precios``).

    Cada fecha de ``fechas`` se marca como inválida para todas las empresas.
    Las fechas fuera del rango de ``precios`` no aplican y se ignoran; una
    fecha DENTRO del rango que no esté en el índice lanza ValueError (evita
    que una fecha mal escrita pase sin efecto).
    """
    if not isinstance(precios, pd.DataFrame):
        raise TypeError("Se esperaba un DataFrame de precios.")
    fechas = pd.DatetimeIndex(pd.to_datetime(list(fechas)))
    if len(precios.index):
        fechas = fechas[(fechas >= precios.index.min())
                        & (fechas <= precios.index.max())]
    faltan = fechas.difference(precios.index)
    if len(faltan):
        raise ValueError(f"Fechas inválidas que no están en los datos: "
                         f"{[str(f.date()) for f in faltan]}")
    bandera = pd.DataFrame(False, index=precios.index, columns=precios.columns)
    bandera.loc[fechas, :] = True
    return bandera


def rendimientos_saltando_invalidos(precios, bandera):
    """Rendimientos (simples, log) ignorando las filas marcadas en ``bandera``.

    Para cada empresa se excluyen sus fechas inválidas, se calculan los
    rendimientos sobre el resto y se reindexa al índice original: la fecha
    inválida queda NaN y la siguiente fecha válida recibe el rendimiento
    acumulado desde la última válida.

    Retorna también ``abarca_invalido``: True en los rendimientos que cubren
    una fecha inválida (más de un día de negociación).
    """
    if not precios.index.equals(bandera.index) or not precios.columns.equals(bandera.columns):
        raise ValueError("precios y bandera deben tener el mismo índice y columnas.")
    simples, logs, abarca = {}, {}, {}
    for col in precios.columns:
        validos = precios.loc[~bandera[col], col]
        anterior = validos.shift(1)
        simples[col] = (validos / anterior - 1).reindex(precios.index)
        logs[col] = np.log(validos / anterior).reindex(precios.index)
        # Fecha válida inmediatamente posterior a una o más inválidas.
        siguiente = bandera[col].shift(1, fill_value=False) & ~bandera[col]
        abarca[col] = siguiente
    a_df = lambda d: pd.DataFrame(d, index=precios.index)[list(precios.columns)]
    return a_df(simples), a_df(logs), a_df(abarca)


# =============================================================================
# Regla mecánica para fechas sospechosas del bloque de prueba (DEC-034)
# =============================================================================

def detectar_reversiones_simultaneas(rend_log, umbral=0.05, tolerancia=0.25, min_acciones=2):
    """Días en que ``min_acciones`` o más acciones tienen un salto |r_t| >= umbral
    que se revierte al día siguiente (signo contrario y |r_t + r_{t+1}| <=
    tolerancia * |r_t|). Es el barrido de DEC-022 convertido en regla.

    Retorna DataFrame (fecha, n_acciones, acciones) ordenado por fecha.
    """
    if not isinstance(rend_log, pd.DataFrame):
        raise TypeError("Se esperaba un DataFrame de rendimientos log.")
    eventos = {}
    for col in rend_log.columns:
        s = rend_log[col].dropna()
        v = s.to_numpy()
        for i in range(len(v) - 1):
            if (abs(v[i]) >= umbral and np.sign(v[i + 1]) == -np.sign(v[i])
                    and abs(v[i] + v[i + 1]) <= tolerancia * abs(v[i])):
                eventos.setdefault(s.index[i], []).append(col)
    filas = [{"fecha": f, "n_acciones": len(a), "acciones": ", ".join(sorted(a))}
             for f, a in sorted(eventos.items()) if len(a) >= min_acciones]
    return pd.DataFrame(filas, columns=["fecha", "n_acciones", "acciones"])


def invalidar_fechas_rendimientos(rend_log, volumen, fechas):
    """Aplica DEC-022 a ``fechas`` sobre rendimientos log ya calculados.

    Para TODAS las columnas: r(fecha) pasa a NaN y el siguiente día del
    índice recibe r(fecha) + r(siguiente) (rendimiento de dos días; equivale
    a anular el precio de esa fecha). El volumen de la fecha queda NaN.
    No inventa valores. Retorna (rend_log, volumen) nuevos.
    """
    r = rend_log.copy()
    v = volumen.copy()
    for fecha in pd.DatetimeIndex(fechas):
        if fecha not in r.index:
            raise ValueError(f"La fecha {fecha.date()} no está en los rendimientos.")
        pos = r.index.get_loc(fecha)
        if pos + 1 < len(r.index):
            siguiente = r.index[pos + 1]
            r.loc[siguiente] = r.loc[fecha] + r.loc[siguiente]
        r.loc[fecha] = np.nan
        if fecha in v.index:
            v.loc[fecha] = np.nan
    return r, v
