"""
correlations.py — Matriz de correlación entre rendimientos
===========================================================

Calcula la matriz de correlación (Pearson por defecto) entre los
rendimientos de los activos. Esta matriz se usará *más adelante* para
estudiar diversificación y construir la matriz de covarianzas; por ahora
solo se calcula y se guarda como resultado descriptivo.

Interpretación de "mayor" y "menor" correlación (para el resumen):
    - Mayor correlación: pares con |r| más alto (relación lineal fuerte,
      sea positiva o negativa).
    - Menor correlación: pares con |r| más bajo (más cercanos a cero,
      mayor potencial de diversificación).
"""

import numpy as np
import pandas as pd


def matriz_correlacion(df_rendimientos, metodo="pearson"):
    """Matriz de correlación entre las columnas de rendimientos.

    Descarta las filas con NaN (p. ej., la primera observación de cada
    activo) antes de calcular la correlación.

    Parámetros:
        df_rendimientos: DataFrame ancho, columnas = activos.
        metodo: "pearson", "spearman" o "kendall".

    Retorna:
        pd.DataFrame simétrico con la matriz de correlación.
    """
    datos = df_rendimientos.dropna()
    return datos.corr(method=metodo)


def _pares_ordenados(matriz, n, descendente):
    """Extrae pares únicos (sin diagonal) ordenados según su correlación.

    ``descendente=True`` ordena por |r| de mayor a menor;
    ``descendente=False`` ordena por |r| de menor a mayor.
    """
    vals = matriz.to_numpy(copy=True)
    np.fill_diagonal(vals, np.nan)
    m = pd.DataFrame(vals, index=matriz.index, columns=matriz.columns)

    stacked = m.unstack().dropna()
    stacked = stacked[stacked.index.get_level_values(0)
                      != stacked.index.get_level_values(1)]

    # Ordenar por valor absoluto de la correlación.
    orden = np.abs(stacked).sort_values(ascending=not descendente)
    orden = stacked.reindex(orden.index)

    resultado = []
    vistos = set()
    for (a, b), valor in orden.items():
        pareja = tuple(sorted((a, b)))
        if pareja in vistos:
            continue
        vistos.add(pareja)
        resultado.append((a, b, float(valor)))
        if len(resultado) >= n:
            break
    return resultado


def pares_mayor_correlacion(matriz, n=1):
    """Pares con mayor |correlación| (relación lineal fuerte)."""
    return _pares_ordenados(matriz, n, descendente=True)


def pares_menor_correlacion(matriz, n=1):
    """Pares con menor |correlación| (mayor potencial de diversificación)."""
    return _pares_ordenados(matriz, n, descendente=False)