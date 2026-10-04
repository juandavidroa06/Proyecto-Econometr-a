"""
externos.py — Variables externas: TRM y petróleo Brent (DEC-024)
=================================================================

Responsabilidad única: descargar UNA vez y leer las series externas.

    - La descarga usa el mismo horizonte que las acciones (FECHA_INICIO,
      FECHA_FIN fija) y guarda los crudos en ``datos/crudos/externos/``
      con la misma protección de inmutabilidad (``guardar_datos_crudos``
      lanza FileExistsError si ya existen).
    - La lectura devuelve un DataFrame ancho de ``Adj Close`` en el
      calendario PROPIO de cada serie (sin sincronizar con la BVC). La
      sincronización con el calendario bursátil se hace al construir
      variables (Fase 8), siempre con información pasada.

Ejecutar la descarga (solo con la carpeta vacía):
    python -m src.data.externos
"""

import logging

import pandas as pd

from config.environment import RUTA_CRUDOS_EXTERNOS, RUTA_METADATA_EXTERNOS
from config.settings import (
    FECHA_FIN,
    FECHA_INICIO,
    FRECUENCIA,
    PRECIO_RENDIMIENTOS,
    TICKERS_EXTERNOS,
)
from src.data.data_manager import (
    cargar_resultados_crudos,
    guardar_datos_crudos,
    nombre_archivo_crudo,
)

logger = logging.getLogger(__name__)


def descargar_externos(tickers=TICKERS_EXTERNOS, ruta=RUTA_CRUDOS_EXTERNOS,
                       ruta_metadata=RUTA_METADATA_EXTERNOS):
    """Descarga y guarda los crudos externos. Falla si ya existen.

    Lanza RuntimeError si alguna serie no se pudo descargar: no se guarda
    un conjunto incompleto.
    """
    from src.data.metadata import crear_metadatos_consolidados, guardar_metadatos
    from src.data.yahoo_downloader import descargar_varios

    existentes = [t for t in tickers.values()
                  if (ruta / nombre_archivo_crudo(t)).exists()]
    if existentes:
        raise FileExistsError(f"Los crudos externos ya existen: {existentes}.")
    resultados = descargar_varios(tickers, FECHA_INICIO, FECHA_FIN, FRECUENCIA)
    fallidos = {n: r["estado"] for n, r in resultados.items() if r["estado"] != "ok"}
    if fallidos:
        raise RuntimeError(f"Descarga externa incompleta: {fallidos}. No se guarda nada.")
    guardados = guardar_datos_crudos(resultados, ruta)
    guardar_metadatos(crear_metadatos_consolidados(resultados, FECHA_INICIO,
                                                   FECHA_FIN, FRECUENCIA),
                      ruta_metadata)
    logger.info("Crudos externos guardados: %s", guardados)
    return guardados


def cargar_externos(tickers=TICKERS_EXTERNOS, ruta=RUTA_CRUDOS_EXTERNOS,
                    columna=PRECIO_RENDIMIENTOS):
    """DataFrame ancho {nombre: precio} en el calendario de cada serie.

    Las fechas que una serie no tiene quedan NaN (no se rellenan aquí).
    """
    resultados = cargar_resultados_crudos(tickers, ruta)
    ancho = pd.DataFrame({n: r["dataframe"][columna] for n, r in resultados.items()})
    ancho = ancho.sort_index()
    ancho.index.name = "Date"
    if (ancho <= 0).any().any():
        raise ValueError("Hay precios externos no positivos.")
    return ancho


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    descargar_externos()
