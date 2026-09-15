"""
metadata.py — Registro de metadatos de la descarga
===================================================

Genera y guarda metadatos que documentan *cómo y cuándo* se obtuvieron
los datos. Esto es clave para la reproducibilidad del proyecto.

Los metadatos se guardan en ``datos/metadata/`` como JSON:
    - un archivo por empresa (``<NOMBRE>.json``);
    - un archivo consolidado (``metadatos_descarga.json``).
"""

import json
from datetime import datetime, timezone

from config.environment import RUTA_DATOS_METADATA


def crear_metadata(empresa, ticker, resultado, fecha_inicio, fecha_fin_solicitada,
                   intervalo, fecha_descarga=None):
    """Construye el diccionario de metadatos de una empresa.

    Parámetros:
        resultado: dict producido por ``descargar_varios``.
        fecha_inicio: fecha inicial solicitada.
        fecha_fin_solicitada: fecha final solicitada (texto).
        intervalo: frecuencia solicitada.

    Retorna:
        dict con los metadatos (nunca se inventan valores).
    """
    df = resultado.get("dataframe")
    meta = {
        "empresa": empresa,
        "ticker": ticker,
        "fuente": "Yahoo Finance",
        "frecuencia": intervalo,
        "fecha_inicio_solicitada": fecha_inicio,
        "fecha_fin_solicitada": fecha_fin_solicitada,
        "fecha_descarga": fecha_descarga
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "estado": resultado.get("estado"),
        "error": resultado.get("error"),
        "advertencias": resultado.get("advertencias", []),
    }

    if df is not None and len(df) > 0:
        meta["observaciones"] = int(len(df))
        meta["fecha_minima"] = str(df.index.min())
        meta["fecha_maxima"] = str(df.index.max())
        meta["columnas"] = list(df.columns)
    else:
        meta["observaciones"] = 0
        meta["fecha_minima"] = None
        meta["fecha_maxima"] = None
        meta["columnas"] = []

    return meta


def crear_metadatos_consolidados(resultados, fecha_inicio, fecha_fin_solicitada,
                                  intervalo, fecha_descarga=None):
    """Crea metadatos para todas las empresas descargadas."""
    return {
        nombre: crear_metadata(
            nombre,
            res["ticker"],
            res,
            fecha_inicio,
            fecha_fin_solicitada,
            intervalo,
            fecha_descarga,
        )
        for nombre, res in resultados.items()
    }


def guardar_metadatos(metadatos, ruta=RUTA_DATOS_METADATA):
    """Guarda los metadatos en disco: un JSON por empresa + uno consolidado.

    Parámetros:
        metadatos: dict {nombre_empresa: dict_metadatos}.

    Retorna:
        lista de rutas guardadas.
    """
    from pathlib import Path

    ruta = Path(ruta)
    ruta.mkdir(parents=True, exist_ok=True)

    guardados = []
    for nombre, meta in metadatos.items():
        archivo = ruta / f"{nombre.replace(' ', '_')}.json"
        with open(archivo, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=4)
        guardados.append(str(archivo))

    consolidado = ruta / "metadatos_descarga.json"
    with open(consolidado, "w", encoding="utf-8") as f:
        json.dump(metadatos, f, ensure_ascii=False, indent=4)
    guardados.append(str(consolidado))

    return guardados


def cargar_metadatos(ruta=RUTA_DATOS_METADATA):
    """Carga todos los metadatos guardados y los devuelve como dict."""
    from pathlib import Path

    ruta = Path(ruta)
    if not ruta.exists():
        return {}
    metadatos = {}
    for archivo in sorted(ruta.glob("*.json")):
        with open(archivo, "r", encoding="utf-8") as f:
            datos = json.load(f)
        if "metadatos_descarga" not in archivo.name:
            metadatos[datos.get("empresa", archivo.stem)] = datos
    return metadatos