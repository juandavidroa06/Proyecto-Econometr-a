"""
yahoo_downloader.py — Descarga de datos desde Yahoo Finance
============================================================

Este módulo es el único responsable de *adquirir* los datos. No realiza
limpieza ni transformaciones: solo descarga y devuelve los datos tal como
Yahoo Finance los proporciona.

Uso:
    from src.data.yahoo_downloader import descargar_varios
    resultados = descargar_varios(TICKERS, "2020-01-01", interval="1d")

Decisiones de diseño:
    - ``auto_adjust=False`` para conservar la columna "Adj Close" separada
      del precio de cierre original "Close". Así se mantiene clara la
      distinción entre precio original y precio ajustado.
    - El índice del DataFrame se normaliza a fechas sin zona horaria.
"""

import logging
from datetime import datetime

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Columnas que Yahoo Finance entrega cuando usa auto_adjust=False.
COLUMNAS_YAHOO = [
    "Open",
    "High",
    "Low",
    "Close",
    "Adj Close",
    "Volume",
    "Dividends",
    "Stock Splits",
]


def _normalizar_indice(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza el índice a fechas sin zona horaria ni componente de hora.

    Yahoo Finance devuelve un índice con zona horaria ("2020-01-01 00:00:00-05:00").
    Para facilitar el análisis posterior, se elimina la zona horaria y la hora.
    """
    if df is None or df.empty:
        return df
    df = df.copy()
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df.index = df.index.normalize()
    df.index.name = "Date"
    return df


def descargar_serie(ticker, fecha_inicio, fecha_fin=None, intervalo="1d"):
    """Descarga la serie histórica de un ticker y la devuelve como DataFrame.

    Parámetros:
        ticker: símbolo del activo en Yahoo Finance (ej: "ECOPETROL.CL").
        fecha_inicio: fecha inicial ("YYYY-MM-DD").
        fecha_fin: fecha final ("YYYY-MM-DD"). Si es None, usa el día actual.
        intervalo: intervalo de datos ("1d", "1wk", "1mo").

    Retorna:
        pd.DataFrame con índice "Date" y columnas OHLCV. Puede estar vacío.
    """
    data = yf.Ticker(ticker).history(
        start=fecha_inicio,
        end=fecha_fin,
        interval=intervalo,
        auto_adjust=False,
    )
    return _normalizar_indice(data)


def descargar_ticker(ticker, fecha_inicio, fecha_fin=None, intervalo="1d"):
    """Descarga un ticker y devuelve un DataFrame (o None si falla).

    A diferencia de ``descargar_serie``, esta función captura errores y
    devuelve ``None`` en caso de fallo, registrando una advertencia.
    """
    try:
        data = descargar_serie(ticker, fecha_inicio, fecha_fin, intervalo)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Error al descargar %s: %s", ticker, exc)
        return None
    if data is None or data.empty:
        logger.warning("Sin datos para %s", ticker)
        return None
    return data


def descargar_varios(tickers, fecha_inicio, fecha_fin=None, intervalo="1d"):
    """Descarga múltiples tickers de forma tolerante a fallos.

    Si una empresa falla, se registra el error y se continúa con las demás.
    Nunca se inventan ni se rellenan datos.

    Parámetros:
        tickers: dict {nombre_empresa: ticker}.
        fecha_inicio / fecha_fin / intervalo: configuración de la descarga.

    Retorna:
        dict {nombre_empresa: dict} donde cada dict tiene:
            - "empresa": nombre
            - "ticker": símbolo
            - "estado": "ok" | "vacio" | "error"
            - "dataframe": pd.DataFrame o None
            - "advertencias": lista de textos
            - "error": mensaje de error o None
    """
    resultados = {}
    for nombre, ticker in tickers.items():
        item = {
            "empresa": nombre,
            "ticker": ticker,
            "estado": "ok",
            "dataframe": None,
            "advertencias": [],
            "error": None,
        }
        try:
            data = descargar_serie(ticker, fecha_inicio, fecha_fin, intervalo)
            if data is None or data.empty:
                item["estado"] = "vacio"
                item["advertencias"].append(
                    "Yahoo Finance no devolvió datos para este ticker."
                )
            else:
                item["dataframe"] = data
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error descargando %s (%s): %s", nombre, ticker, exc)
            item["estado"] = "error"
            item["error"] = str(exc)
            item["advertencias"].append(f"Excepción durante la descarga: {exc}")
        resultados[nombre] = item
    return resultados


def fecha_fin_resuelta(fecha_fin):
    """Devuelve la fecha fin como texto; si es None, usa el día actual."""
    if fecha_fin is None:
        return datetime.now().strftime("%Y-%m-%d")
    return fecha_fin