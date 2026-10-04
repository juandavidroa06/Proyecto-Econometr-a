"""
data_manager.py — Gestión de archivos de datos (crudos y procesados)
=====================================================================

Responsabilidades:
    - Guardar los datos crudos descargados SIN modificarlos (un CSV por empresa).
    - Guardar y cargar los datasets procesados.

Los datos crudos NUNCA se sobrescriben con datos transformados. Para cada
descarga se genera un archivo nuevo en ``datos/crudos/``.

Decisiones de diseño:
    - El nombre del archivo crudo deriva del ticker sin caracteres problemáticos
      (se reemplaza "." por "_").
    - Los datasets procesados se guardan en formato "ancho" (una columna por
      empresa) para facilitar el análisis posterior.
"""

import logging
from pathlib import Path

import pandas as pd

from config.settings import FECHAS_DATO_INVALIDO_FUENTE, PRECIO_RENDIMIENTOS
from config.environment import RUTA_DATOS_CRUDOS, RUTA_DATOS_PROCESADOS

logger = logging.getLogger(__name__)

# Nombres de archivo procesados.
ARCHIVO_PRECIOS = "precios.csv"
ARCHIVO_REND_SIMPLES = "rendimientos_simples.csv"
ARCHIVO_REND_LOG = "rendimientos_log.csv"
ARCHIVO_DATASET = "dataset_analisis.csv"


def nombre_archivo_crudo(ticker):
    """Convierte un ticker en un nombre de archivo seguro.

    Ejemplo: "ECOPETROL.CL" -> "ECOPETROL_CL.csv"
    """
    limpio = ticker.replace(".", "_").replace("/", "_").replace(" ", "_")
    return f"{limpio}.csv"


def guardar_datos_crudos(datos_dict, ruta=RUTA_DATOS_CRUDOS):
    """Guarda un DataFrame por empresa en formato CSV (datos crudos intactos).

    Los crudos son inmutables (AGENTS.md, sección 5; DEC-021): si ya existe
    alguno de los archivos de destino se lanza ``FileExistsError`` ANTES de
    escribir nada. Para reemplazarlos hay que moverlos manualmente y
    registrar la decisión en el diario.

    Parámetros:
        datos_dict: dict {nombre_empresa: dict_resultado} (con clave "dataframe")
        o {nombre_empresa: DataFrame}.

    Retorna:
        lista de rutas guardadas.
    """
    ruta = Path(ruta)
    ruta.mkdir(parents=True, exist_ok=True)

    pendientes = []
    for nombre, elemento in datos_dict.items():
        if isinstance(elemento, dict):
            ticker = elemento.get("ticker", nombre)
            df = elemento.get("dataframe")
        else:
            ticker = nombre
            df = elemento

        if df is None or df.empty:
            logger.warning("No se guarda %s: sin datos disponibles.", nombre)
            continue
        pendientes.append((ruta / nombre_archivo_crudo(ticker), df))

    existentes = [str(archivo) for archivo, _ in pendientes if archivo.exists()]
    if existentes:
        raise FileExistsError(
            "Los datos crudos son inmutables y ya existen: "
            f"{existentes}. No se sobrescribe ningún archivo.")

    guardados = []
    for archivo, df in pendientes:
        df.to_csv(archivo, index=True, encoding="utf-8")
        guardados.append(str(archivo))

    return guardados


def cargar_resultados_crudos(tickers, ruta=RUTA_DATOS_CRUDOS):
    """Lee los crudos guardados con la misma estructura que ``descargar_varios``.

    Permite reejecutar el pipeline sin volver a descargar (DEC-021). Exige
    que exista el archivo de cada ticker: si falta alguno lanza
    ``FileNotFoundError`` (no se continúa con un universo incompleto).

    Retorna:
        dict {nombre_empresa: {"empresa", "ticker", "estado", "dataframe",
        "advertencias", "error"}}.
    """
    ruta = Path(ruta)
    faltantes = [ticker for ticker in tickers.values()
                 if not (ruta / nombre_archivo_crudo(ticker)).exists()]
    if faltantes:
        raise FileNotFoundError(
            f"Faltan datos crudos en {ruta} para: {faltantes}. "
            "Para las acciones: 'python -m src.pipeline --descargar'; para las "
            "externas: 'python -m src.data.externos' (solo con la carpeta vacía).")

    resultados = {}
    for nombre, ticker in tickers.items():
        # round_trip: relee los floats bit a bit iguales a como se guardaron
        # (el parser por defecto difiere en el último dígito, ~1e-16).
        df = pd.read_csv(ruta / nombre_archivo_crudo(ticker), index_col=0,
                         parse_dates=True, float_precision="round_trip")
        df.index.name = "Date"
        if df.empty:
            raise ValueError(f"El archivo crudo de {nombre} ({ticker}) está vacío.")
        resultados[nombre] = {
            "empresa": nombre,
            "ticker": ticker,
            "estado": "ok",
            "dataframe": df,
            "advertencias": [],
            "error": None,
        }
    return resultados


def cargar_datos_crudos(ruta=RUTA_DATOS_CRUDOS):
    """Carga los CSV crudos guardados y los devuelve como dict {ticker: DataFrame}.

    El nombre de la clave es el nombre del archivo sin extensión (p. ej.
    "ECOPETROL_CL"). Brinda una función de lectura consistente para el notebook.
    """
    ruta = Path(ruta)
    if not ruta.exists():
        return {}
    datos = {}
    for archivo in sorted(ruta.glob("*.csv")):
        df = pd.read_csv(archivo, index_col=0, parse_dates=True)
        df.index.name = "Date"
        datos[archivo.stem] = df
    return datos


def _dataframe_precios_anchos(datos_dict, columna_precio):
    """Construye un DataFrame 'ancho': filas=fechas, columnas=empresas."""
    series = {}
    for nombre, elemento in datos_dict.items():
        df = elemento.get("dataframe") if isinstance(elemento, dict) else elemento
        if df is None or df.empty or columna_precio not in df.columns:
            continue
        series[nombre] = df[columna_precio]
    if not series:
        return pd.DataFrame()
    ancho = pd.DataFrame(series)
    ancho = ancho.sort_index()
    ancho.index.name = "Date"
    return ancho


def _dataframe_rendimientos_anchos(datos_dict):
    """Calcula rendimientos (simple y log) en formato ancho a partir de los datos.

    Retorna:
        (rendimientos_simples, rendimientos_log) como DataFrames anchos.
    """
    from src.preprocessing.returns import calcular_rendimientos

    precios = _dataframe_precios_anchos(datos_dict, PRECIO_RENDIMIENTOS)
    return calcular_rendimientos(precios)


def guardar_datos_procesados(datos_dict, ruta=RUTA_DATOS_PROCESADOS,
                              precios=None, rend_simples=None, rend_log=None):
    """Guarda los datasets procesados (precios y rendimientos).

    Parámetros:
        precios / rend_simples / rend_log: DataFrames ya calculados.
        Si son None, se derivan de ``datos_dict`` usando la columna configurada
        ``PRECIO_RENDIMIENTOS`` (por defecto "Adj Close").
    """
    from src.preprocessing.returns import calcular_rendimientos

    ruta = Path(ruta)
    ruta.mkdir(parents=True, exist_ok=True)

    if precios is None:
        precios = _dataframe_precios_anchos(datos_dict, PRECIO_RENDIMIENTOS)
    if rend_simples is None or rend_log is None:
        simp, logr = calcular_rendimientos(precios)
        rend_simples = rend_simples if rend_simples is not None else simp
        rend_log = rend_log if rend_log is not None else logr

    guardados = []

    if not precios.empty:
        ruta_precios = ruta / ARCHIVO_PRECIOS
        precios.to_csv(ruta_precios, index=True, encoding="utf-8")
        guardados.append(str(ruta_precios))

    if rend_simples is not None and not rend_simples.empty:
        ruta_simples = ruta / ARCHIVO_REND_SIMPLES
        rend_simples.to_csv(ruta_simples, index=True, encoding="utf-8")
        guardados.append(str(ruta_simples))

    if rend_log is not None and not rend_log.empty:
        ruta_log = ruta / ARCHIVO_REND_LOG
        rend_log.to_csv(ruta_log, index=True, encoding="utf-8")
        guardados.append(str(ruta_log))

    return guardados


def construir_dataset_analisis(datos_dict, precios=None, rend_simples=None,
                               rend_log=None):
    """Construye un dataset 'largo' (tidy) para análisis.

    Una fila por (fecha, empresa) con:
        - precio (configurado, por defecto "Adj Close")
        - precio_original ("Close") si está disponible
        - rendimiento_simple
        - rendimiento_log

    Retorna:
        pd.DataFrame con índice RangeIndex y columnas claras.
    """
    from src.preprocessing.returns import calcular_rendimientos

    if precios is None:
        precios = _dataframe_precios_anchos(datos_dict, PRECIO_RENDIMIENTOS)
    if rend_simples is None or rend_log is None:
        rend_simples, rend_log = calcular_rendimientos(precios)

    regs = []
    for nombre, elemento in datos_dict.items():
        df = elemento.get("dataframe") if isinstance(elemento, dict) else elemento
        if df is None or df.empty:
            continue
        for fecha in precios.index:
            if fecha not in df.index:
                continue
            registro = {
                "empresa": nombre,
                "fecha": fecha,
                "precio": precios.loc[fecha, nombre]
                if nombre in precios.columns else None,
                "rendimiento_simple": rend_simples.loc[fecha, nombre]
                if nombre in rend_simples.columns else None,
                "rendimiento_log": rend_log.loc[fecha, nombre]
                if nombre in rend_log.columns else None,
            }
            if "Close" in df.columns:
                registro["precio_original"] = df.loc[fecha, "Close"]
            regs.append(registro)

    dataset = pd.DataFrame(regs)
    dataset = dataset.sort_values(["fecha", "empresa"]).reset_index(drop=True)
    return dataset


def guardar_dataset_analisis(dataset, ruta=RUTA_DATOS_PROCESADOS):
    """Guarda el dataset de análisis en formato CSV."""
    ruta = Path(ruta)
    ruta.mkdir(parents=True, exist_ok=True)
    archivo = ruta / ARCHIVO_DATASET
    dataset.to_csv(archivo, index=False, encoding="utf-8")
    return str(archivo)


# =============================================================================
# Procesamiento con imputación (Filtro de Kalman) y trazabilidad
# =============================================================================
# Estas funciones generan una versión procesada que incorpora la imputación
# de valores faltantes Y conserva banderas que indican qué valores fueron
# imputados y qué rendimientos dependen de una imputación.

ARCHIVO_BANDERA_IMPUTACION = "banderas_imputacion.csv"
ARCHIVO_RETORNO_DEPENDE = "retorno_depende_imputacion.csv"
ARCHIVO_BANDERA_INVALIDO = "banderas_dato_invalido.csv"
ARCHIVO_VOLUMEN = "volumen.csv"


def procesar_con_imputacion(datos_dict, columna=PRECIO_RENDIMIENTOS,
                            fechas_invalidas=FECHAS_DATO_INVALIDO_FUENTE):
    """Procesa los datos crudos e incorpora imputación de faltantes.

    Pasos:
        1. Itera por empresa sobre su propia serie (índice continuo) y aplica
           el Filtro de Kalman solo a los NaN reales de esa serie.
        2. Construye DataFrames anchos de precios imputados y de banderas.
        3. Anula (NaN + bandera) los precios de ``fechas_invalidas`` (DEC-022)
           DESPUÉS de imputar, para que Kalman no los rellene, y calcula
           rendimientos (simple y log) saltando esas fechas.
        4. Calcula la bandera ``retorno_depende_imputacion``.
        5. Construye el dataset largo con trazabilidad.

    Retorna:
        dict con claves: precios (imputados), bandera (ancho), rend_simples,
        rend_log, retorno_depende, bandera_invalido, retorno_abarca_invalido,
        dataset, reporte_imputaciones y precios_crudos (para comparaciones
        antes/después).
    """
    from src.preprocessing.kalman_imputation import imputar_serie
    from src.preprocessing.invalid_data import (
        bandera_dato_invalido,
        rendimientos_saltando_invalidos,
    )

    series_imputadas = {}
    banderas = {}
    registros_imputacion = []

    for nombre, elemento in datos_dict.items():
        df = elemento.get("dataframe") if isinstance(elemento, dict) else elemento
        if df is None or df.empty or columna not in df.columns:
            continue
        serie = df[columna].rename(nombre)
        imputada, bandera = imputar_serie(serie)
        series_imputadas[nombre] = imputada
        banderas[nombre] = bandera

        for fecha in serie.index[bandera]:
            registros_imputacion.append({
                "empresa": nombre,
                "fecha": fecha,
                "variable": columna,
                "valor_original": None,
                "valor_imputado": float(imputada.loc[fecha]),
                "metodo": "kalman_smoothing_local_level",
                "observacion": "NaN imputado con suavizado de Kalman (log-precio).",
            })

    precios_crudos = _dataframe_precios_anchos(datos_dict, columna)
    precios = pd.DataFrame(series_imputadas).sort_index()
    precios.index.name = "Date"

    bandera = pd.DataFrame(banderas).sort_index()
    bandera = bandera.fillna(False).astype(bool)
    bandera.index.name = "Date"

    bandera_invalido = bandera_dato_invalido(precios, fechas_invalidas)
    if (bandera & bandera_invalido).any().any():
        raise ValueError("Una fecha inválida coincide con un valor imputado; "
                         "revisar DEC-013 y DEC-022 antes de continuar.")
    precios = precios.mask(bandera_invalido)
    # Volumen en el calendario de los precios; el del día inválido también
    # queda NaN (la fila completa de la fuente es dudosa, DEC-022).
    volumen = (_dataframe_precios_anchos(datos_dict, "Volume")
               .reindex(index=precios.index, columns=precios.columns)
               .mask(bandera_invalido))
    rend_simples, rend_log, abarca_invalido = rendimientos_saltando_invalidos(
        precios, bandera_invalido)

    retorno_depende = (bandera.shift(1).fillna(False) | bandera)
    retorno_depende.index.name = "Date"

    dataset = _construir_dataset_imputado(datos_dict, precios, bandera,
                                          rend_simples, rend_log, retorno_depende,
                                          bandera_invalido, abarca_invalido)
    reporte = pd.DataFrame(registros_imputacion)

    return {
        "precios": precios,
        "precios_crudos": precios_crudos,
        "bandera": bandera,
        "rend_simples": rend_simples,
        "rend_log": rend_log,
        "retorno_depende": retorno_depende,
        "bandera_invalido": bandera_invalido,
        "retorno_abarca_invalido": abarca_invalido,
        "volumen": volumen,
        "dataset": dataset,
        "reporte_imputaciones": reporte,
    }


def _construir_dataset_imputado(datos_dict, precios, bandera, rend_simples,
                                rend_log, retorno_depende, bandera_invalido,
                                abarca_invalido):
    """Construye el dataset largo (tidy) con banderas de imputación."""
    registros = []
    for nombre, elemento in datos_dict.items():
        df = elemento.get("dataframe") if isinstance(elemento, dict) else elemento
        if df is None or df.empty or nombre not in precios.columns:
            continue
        for fecha in df.index:
            if fecha not in precios.index:
                continue
            registro = {
                "empresa": nombre,
                "fecha": fecha,
                "precio": precios.loc[fecha, nombre],
                "es_imputado_kalman": bool(bandera.loc[fecha, nombre]),
                "rendimiento_simple": rend_simples.loc[fecha, nombre]
                if nombre in rend_simples.columns else None,
                "rendimiento_log": rend_log.loc[fecha, nombre]
                if nombre in rend_log.columns else None,
                "retorno_depende_imputacion": bool(retorno_depende.loc[fecha, nombre])
                if nombre in retorno_depende.columns else False,
                "es_dato_invalido_fuente": bool(bandera_invalido.loc[fecha, nombre]),
                "retorno_abarca_dato_invalido": bool(abarca_invalido.loc[fecha, nombre]),
            }
            if "Close" in df.columns:
                registro["precio_original"] = df.loc[fecha, "Close"]
            registros.append(registro)

    dataset = pd.DataFrame(registros)
    dataset = dataset.sort_values(["fecha", "empresa"]).reset_index(drop=True)
    return dataset


def guardar_conjunto_procesado(conjunto, ruta=RUTA_DATOS_PROCESADOS):
    """Guarda todos los archivos del conjunto procesado (con imputación).

    Retorna lista de rutas guardadas.
    """
    ruta = Path(ruta)
    ruta.mkdir(parents=True, exist_ok=True)

    guardados = []

    if conjunto["precios"] is not None and not conjunto["precios"].empty:
        conjunto["precios"].to_csv(ruta / ARCHIVO_PRECIOS, index=True, encoding="utf-8")
        guardados.append(str(ruta / ARCHIVO_PRECIOS))

    if conjunto["bandera"] is not None and not conjunto["bandera"].empty:
        conjunto["bandera"].to_csv(ruta / ARCHIVO_BANDERA_IMPUTACION, index=True,
                                   encoding="utf-8")
        guardados.append(str(ruta / ARCHIVO_BANDERA_IMPUTACION))

    if conjunto["rend_simples"] is not None and not conjunto["rend_simples"].empty:
        conjunto["rend_simples"].to_csv(ruta / ARCHIVO_REND_SIMPLES, index=True,
                                        encoding="utf-8")
        guardados.append(str(ruta / ARCHIVO_REND_SIMPLES))

    if conjunto["rend_log"] is not None and not conjunto["rend_log"].empty:
        conjunto["rend_log"].to_csv(ruta / ARCHIVO_REND_LOG, index=True,
                                    encoding="utf-8")
        guardados.append(str(ruta / ARCHIVO_REND_LOG))

    if conjunto["retorno_depende"] is not None and not conjunto["retorno_depende"].empty:
        conjunto["retorno_depende"].to_csv(ruta / ARCHIVO_RETORNO_DEPENDE, index=True,
                                           encoding="utf-8")
        guardados.append(str(ruta / ARCHIVO_RETORNO_DEPENDE))

    if conjunto["bandera_invalido"] is not None and not conjunto["bandera_invalido"].empty:
        conjunto["bandera_invalido"].to_csv(ruta / ARCHIVO_BANDERA_INVALIDO,
                                            index=True, encoding="utf-8")
        guardados.append(str(ruta / ARCHIVO_BANDERA_INVALIDO))

    if conjunto.get("volumen") is not None and not conjunto["volumen"].empty:
        conjunto["volumen"].to_csv(ruta / ARCHIVO_VOLUMEN, index=True, encoding="utf-8")
        guardados.append(str(ruta / ARCHIVO_VOLUMEN))

    if conjunto["dataset"] is not None and not conjunto["dataset"].empty:
        conjunto["dataset"].to_csv(ruta / ARCHIVO_DATASET, index=False, encoding="utf-8")
        guardados.append(str(ruta / ARCHIVO_DATASET))

    return guardados