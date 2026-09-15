"""
data_validator.py — Validación de calidad de datos
===================================================

Este módulo revisa la calidad de los datos descargados y genera un reporte
consolidado. Sigue el principio del proyecto:

    - NO elimina observaciones automáticamente;
    - solo IDENTIFICA y DOCUMENTA problemas.

Chequeos por empresa:
    - estructura (DataFrame, columnas, índice, tipos);
    - fechas (mínima, máxima, orden, duplicados);
    - valores faltantes (cantidad y porcentaje por columna);
    - valores inválidos (precios <= 0, volumen negativo, filas duplicadas);
    - continuidad (solo informativa: no se marcan fines de semana ni festivos).
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

COLUMNAS_ESPERADAS = [
    "Open",
    "High",
    "Low",
    "Close",
    "Adj Close",
    "Volume",
]
COLUMNAS_PRECIO = ["Open", "High", "Low", "Close", "Adj Close"]


def validar_dataframe(df, nombre=None):
    """Ejecuta todas las validaciones sobre un único DataFrame.

    Retorna:
        dict con los resultados de cada chequeo.
    """
    checks = {}

    # --- Estructura ---
    checks["existe"] = df is not None and not df.empty
    if not checks["existe"]:
        checks["estado"] = "vacio"
        return checks

    checks["n_observaciones"] = int(len(df))
    checks["columnas_disponibles"] = list(df.columns)
    checks["columnas_faltantes"] = [c for c in COLUMNAS_ESPERADAS if c not in df.columns]

    # Índice de fechas
    checks["indice_es_fecha"] = isinstance(df.index, pd.DatetimeIndex)

    # --- Fechas ---
    if checks["indice_es_fecha"]:
        checks["fecha_minima"] = str(df.index.min())
        checks["fecha_maxima"] = str(df.index.max())
        checks["fechas_ordenadas"] = bool(df.index.is_monotonic_increasing)
        checks["fechas_duplicadas"] = int(df.index.duplicated().sum())
    else:
        checks["fecha_minima"] = None
        checks["fecha_maxima"] = None
        checks["fechas_ordenadas"] = None
        checks["fechas_duplicadas"] = None

    # --- Continuidad (informativa, no se marca como error) ---
    if checks["indice_es_fecha"] and checks["fechas_ordenadas"]:
        gaps = df.index.to_series().diff().dt.days.dropna()
        checks["gap_maximo_dias"] = int(gaps.max()) if len(gaps) else 0
        checks["gap_promedio_dias"] = float(gaps.mean()) if len(gaps) else 0.0
    else:
        checks["gap_maximo_dias"] = None
        checks["gap_promedio_dias"] = None

    # --- Tipos de datos ---
    try:
        checks["contiene_na_precios"] = bool(df[COLUMNAS_PRECIO].isna().any().any())
    except KeyError:
        checks["contiene_na_precios"] = None
    try:
        checks["contiene_na_volumen"] = bool(df["Volume"].isna().any())
    except KeyError:
        checks["contiene_na_volumen"] = None

    # --- Valores faltantes ---
    faltantes_por_columna = df.isna().sum().astype(int)
    checks["faltantes_por_columna"] = faltantes_por_columna.to_dict()
    checks["total_faltantes"] = int(faltantes_por_columna.sum())
    checks["porcentaje_faltantes"] = round(
        100.0 * checks["total_faltantes"] / max(1, df.size), 4
    )

    # --- Valores inválidos ---
    precios_invalidos = 0
    for col in COLUMNAS_PRECIO:
        if col in df.columns:
            precios_invalidos += int((df[col] <= 0).sum())
    checks["precios_invalidos"] = int(precios_invalidos)

    volumen_invalido = 0
    if "Volume" in df.columns:
        volumen_invalido = int((df["Volume"] < 0).sum())
    checks["volumen_invalido"] = int(volumen_invalido)

    # Filas duplicadas (misma combinación precio/volumen, ignorando el índice)
    checks["filas_duplicadas"] = int(df.duplicated().sum())

    # Estado global
    problemas = []
    if checks["columnas_faltantes"]:
        problemas.append("columnas faltantes")
    if checks["fechas_duplicadas"] not in (None, 0):
        problemas.append("fechas duplicadas")
    if checks["fechas_ordenadas"] is False:
        problemas.append("fechas no ordenadas")
    if checks["precios_invalidos"] > 0:
        problemas.append("precios inválidos (<=0)")
    if checks["volumen_invalido"] > 0:
        problemas.append("volumen negativo")
    checks["estado"] = "ok" if not problemas else "advertencia"
    checks["problemas"] = problemas

    return checks


def validar_varios(datos_dict):
    """Valida todas las empresas y devuelve un reporte consolidado.

    Parámetros:
        datos_dict: dict {nombre_empresa: DataFrame} (o el resultado de
        ``descargar_varios`` si tiene la clave "dataframe").

    Retorna:
        pd.DataFrame con una fila por empresa.
    """
    filas = []
    for nombre, elemento in datos_dict.items():
        if isinstance(elemento, dict):
            df = elemento.get("dataframe")
        else:
            df = elemento

        checks = validar_dataframe(df, nombre)

        filas.append({
            "empresa": nombre,
            "ticker": elemento.get("ticker", "") if isinstance(elemento, dict) else "",
            "observaciones": checks.get("n_observaciones", 0),
            "fecha_inicio": checks.get("fecha_minima"),
            "fecha_fin": checks.get("fecha_maxima"),
            "faltantes": checks.get("total_faltantes", 0),
            "porcentaje_faltantes": checks.get("porcentaje_faltantes", 0.0),
            "duplicados": checks.get("filas_duplicadas", 0),
            "fechas_duplicadas": checks.get("fechas_duplicadas", 0),
            "precios_invalidos": checks.get("precios_invalidos", 0),
            "volumen_invalido": checks.get("volumen_invalido", 0),
            "columnas_faltantes": ", ".join(checks.get("columnas_faltantes", [])),
            "estado": checks.get("estado"),
            "observaciones_calidad": "; ".join(checks.get("problemas", [])),
        })

    reporte = pd.DataFrame(filas)
    return reporte


def guardar_reporte_calidad(reporte, ruta_archivo):
    """Guarda el reporte de calidad como CSV."""
    reporte.to_csv(ruta_archivo, index=False, encoding="utf-8")
    return str(ruta_archivo)