"""
split.py — Partición temporal entrenamiento / validación / prueba
==================================================================

Divide un DataFrame indexado por fecha en tres bloques CONSECUTIVOS y sin
solapamiento. Nunca se mezclan observaciones (no hay ``train_test_split``
aleatorio), para evitar data leakage (AGENTS.md, sección 6).

Las fechas de corte se definen en ``config/settings.py`` (DEC-017).
"""

import pandas as pd


def _validar_indice(df):
    if not isinstance(df, (pd.DataFrame, pd.Series)):
        raise TypeError("Se esperaba un DataFrame o Series de pandas.")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("El índice debe ser un DatetimeIndex.")
    if df.index.has_duplicates:
        raise ValueError("El índice tiene fechas duplicadas.")
    if not df.index.is_monotonic_increasing:
        raise ValueError("El índice no está ordenado cronológicamente.")


def particion_temporal(df, fin_train, fin_validacion):
    """Devuelve dict con 'train', 'validacion' y 'test'.

    Reglas:
        train      : fecha <= fin_train
        validacion : fin_train < fecha <= fin_validacion
        test       : fecha > fin_validacion

    Lanza ValueError si las fechas de corte no son crecientes o si algún
    bloque queda vacío (no se devuelven particiones silenciosamente vacías).
    """
    _validar_indice(df)
    fin_train = pd.Timestamp(fin_train)
    fin_validacion = pd.Timestamp(fin_validacion)
    if not fin_train < fin_validacion:
        raise ValueError("fin_train debe ser anterior a fin_validacion.")

    train = df.loc[df.index <= fin_train]
    validacion = df.loc[(df.index > fin_train) & (df.index <= fin_validacion)]
    test = df.loc[df.index > fin_validacion]

    for nombre, bloque in (("train", train), ("validacion", validacion),
                           ("test", test)):
        if len(bloque) == 0:
            raise ValueError(f"La partición '{nombre}' quedó vacía.")

    return {"train": train, "validacion": validacion, "test": test}


def resumen_particion(particion):
    """Tabla con inicio, fin y número de observaciones de cada bloque."""
    filas = []
    for nombre, bloque in particion.items():
        filas.append({
            "bloque": nombre,
            "inicio": bloque.index.min(),
            "fin": bloque.index.max(),
            "observaciones": len(bloque),
        })
    return pd.DataFrame(filas)
