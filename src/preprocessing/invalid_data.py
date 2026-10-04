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
