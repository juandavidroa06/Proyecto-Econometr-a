"""
pipeline.py — Punto de entrada de las Fases 2, 3, 3.5 y 4
======================================================

Orquesta el flujo completo reproducible:

    1. Descargar datos desde Yahoo Finance.
    2. Guardar los datos crudos (sin modificar).
    3. Registrar metadatos de la descarga.
    4. Validar la calidad de los datos y generar reporte.
    5. Imputar valores faltantes (Filtro de Kalman) y procesar rendimientos.
    6. Guardar datasets procesados con banderas de imputación.
    7. Validar la imputación (prueba artificial MAE/RMSE) y comparar antes/después.
    8. Análisis exploratorio (estadísticas, volatilidad, correlaciones, outliers).
    9. Generar gráficos.
    10. Resumen descriptivo.

Ejecución (desde la raíz del proyecto):
    python -m src.pipeline

El código es tolerante a fallos: si una etapa falla, se registra el error
y se continúa con las siguientes cuando es posible.
"""

import logging
import sys
from pathlib import Path

import pandas as pd

# Asegurar que la raíz del proyecto esté disponible en sys.path.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from config.settings import (  # noqa: E402
    TICKERS,
    FECHA_INICIO,
    FECHA_FIN,
    FRECUENCIA,
    PRECIO_RENDIMIENTOS,
)
from config.environment import (  # noqa: E402
    RUTA_RESULTADOS,
    RUTA_DATOS_CRUDOS,
    RUTA_DATOS_PROCESADOS,
    RUTA_DATOS_METADATA,
)

from src.data.yahoo_downloader import descargar_varios, fecha_fin_resuelta  # noqa: E402
from src.data.metadata import crear_metadatos_consolidados, guardar_metadatos  # noqa: E402
from src.data.data_validator import validar_varios, guardar_reporte_calidad  # noqa: E402
from src.data.data_manager import (  # noqa: E402
    guardar_datos_crudos,
    procesar_con_imputacion,
    guardar_conjunto_procesado,
)

logger = logging.getLogger(__name__)


def _configurar_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def etapa_descarga():
    """Fase 2: descarga y guardado de datos crudos + metadatos."""
    fecha_fin = fecha_fin_resuelta(FECHA_FIN)
    logger.info("Descargando %d empresas desde %s hasta %s (intervalo %s)",
                len(TICKERS), FECHA_INICIO, fecha_fin, FRECUENCIA)

    resultados = descargar_varios(TICKERS, FECHA_INICIO, fecha_fin, FRECUENCIA)

    guardados = guardar_datos_crudos(resultados, RUTA_DATOS_CRUDOS)
    logger.info("Archivos crudos guardados: %d", len(guardados))

    metadatos = crear_metadatos_consolidados(
        resultados, FECHA_INICIO, fecha_fin, FRECUENCIA
    )
    guardar_metadatos(metadatos, RUTA_DATOS_METADATA)

    return resultados


def etapa_validacion(resultados):
    """Fase 2: validación de calidad y reporte consolidado."""
    reporte = validar_varios(resultados)
    RUTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    ruta = RUTA_RESULTADOS / "reporte_calidad_datos.csv"
    guardar_reporte_calidad(reporte, ruta)
    logger.info("Reporte de calidad guardado en %s", ruta)
    return reporte


def etapa_procesamiento(resultados):
    """Fase 3.5: imputación de faltantes + rendimientos + banderas de imputación."""
    conjunto = procesar_con_imputacion(resultados)
    guardados = guardar_conjunto_procesado(conjunto, RUTA_DATOS_PROCESADOS)
    logger.info("Archivos procesados guardados: %d", len(guardados))
    logger.info("Valores imputados: %d", len(conjunto["reporte_imputaciones"]))
    return conjunto


def etapa_imputacion(resultados, conjunto):
    """Fase 3.5: validación de la imputación, comparación antes/después y gráficos."""
    from src.preprocessing.kalman_imputation import validar_imputacion
    from src.preprocessing.returns import calcular_rendimientos
    from src.exploratory_analysis.descriptive_statistics import (
        estadisticas_descriptivas,
    )
    from src.exploratory_analysis import plots

    RUTA_RESULTADOS.mkdir(parents=True, exist_ok=True)

    # 1. Reporte de imputaciones.
    reporte = conjunto["reporte_imputaciones"]
    if reporte.empty:
        reporte = pd.DataFrame(columns=["empresa", "fecha", "variable",
                                        "valor_original", "valor_imputado",
                                        "metodo", "observacion"])
    reporte.to_csv(RUTA_RESULTADOS / "reporte_imputaciones_kalman.csv",
                   index=False, encoding="utf-8")

    # 2. Validación artificial (ocultar observados -> imputar -> MAE/RMSE).
    validaciones = []
    for nombre, elemento in resultados.items():
        df = elemento.get("dataframe")
        if df is None or df.empty or PRECIO_RENDIMIENTOS not in df.columns:
            continue
        serie = df[PRECIO_RENDIMIENTOS]
        if serie.notna().sum() < 10:
            continue
        try:
            r = validar_imputacion(serie, n_ocultar=30)
            validaciones.append({
                "empresa": nombre,
                "mae": r["mae"],
                "rmse": r["rmse"],
                "mae_relativo": r["mae_relativo"],
                "n_ocultados": r["n_ocultados"],
            })
        except Exception as exc:  # noqa: BLE001
            logger.warning("Validación no disponible para %s: %s", nombre, exc)
            validaciones.append({
                "empresa": nombre, "mae": None, "rmse": None,
                "mae_relativo": None, "n_ocultados": 0,
            })
    pd.DataFrame(validaciones).to_csv(RUTA_RESULTADOS / "validacion_kalman.csv",
                                      index=False, encoding="utf-8")

    # 3. Comparación antes/después de la imputación (estadísticas de rendimientos).
    _, rend_antes_log = calcular_rendimientos(conjunto["precios_crudos"])
    estad_antes = estadisticas_descriptivas(rend_antes_log)
    estad_despues = estadisticas_descriptivas(conjunto["rend_log"])
    comparacion = pd.DataFrame({
        "media_antes": estad_antes["media"],
        "media_despues": estad_despues["media"],
        "media_diferencia": estad_despues["media"] - estad_antes["media"],
        "desv_antes": estad_antes["desviacion_estandar"],
        "desv_despues": estad_despues["desviacion_estandar"],
        "desv_diferencia": (estad_despues["desviacion_estandar"]
                            - estad_antes["desviacion_estandar"]),
    })
    comparacion.to_csv(RUTA_RESULTADOS / "comparacion_antes_despues_kalman.csv",
                       encoding="utf-8")

    # 4. Gráfico por cada serie que tenga imputaciones.
    bandera = conjunto["bandera"]
    for nombre in bandera.columns:
        if not bandera[nombre].any():
            continue
        elemento = resultados.get(nombre, {})
        df = elemento.get("dataframe")
        if df is None or df.empty:
            continue
        original = df[PRECIO_RENDIMIENTOS]
        imputada = conjunto["precios"][nombre]
        plots.plot_imputacion_kalman(nombre, original, imputada, bandera[nombre])

    return reporte


def etapa_exploratoria(conjunto, reporte_calidad):
    """Fase 3: análisis exploratorio, gráficos, outliers y resumen sobre datos imputados."""
    from src.exploratory_analysis.descriptive_statistics import (
        estadisticas_descriptivas,
        resumir_volatilidad,
    )
    from src.exploratory_analysis.correlations import matriz_correlacion
    from src.exploratory_analysis.outliers import detectar_outliers
    from src.exploratory_analysis import plots
    from src.exploratory_analysis.resumen import (
        generar_resumen_descriptivo,
        guardar_resumen,
        imprimir_resumen,
    )

    precios = conjunto["precios"]
    rend_log = conjunto["rend_log"]

    RUTA_RESULTADOS.mkdir(parents=True, exist_ok=True)

    estad = estadisticas_descriptivas(rend_log)
    estad.to_csv(RUTA_RESULTADOS / "estadisticas_descriptivas.csv",
                 encoding="utf-8")

    vol = resumir_volatilidad(rend_log)
    vol.to_csv(RUTA_RESULTADOS / "volatilidades.csv", encoding="utf-8")

    corr = matriz_correlacion(rend_log)
    corr.to_csv(RUTA_RESULTADOS / "matriz_correlacion.csv", encoding="utf-8")

    outliers = detectar_outliers(rend_log)
    outliers.to_csv(RUTA_RESULTADOS / "posibles_outliers.csv",
                    index=False, encoding="utf-8")

    graficos = [
        plots.plot_precios(precios),
        plots.plot_rendimientos(rend_log),
        plots.plot_distribucion(rend_log),
        plots.plot_volatilidad(rend_log),
        plots.plot_matriz_correlacion(corr),
    ]
    logger.info("Gráficos generados: %d", len(graficos))

    resumen = generar_resumen_descriptivo(rend_log, matriz_corr=corr,
                                          reporte_calidad=reporte_calidad)
    guardar_resumen(resumen)
    return resumen


def etapa_fase4(conjunto):
    """Fase 4 (EDA): partición temporal, iliquidez, saltos reversibles y pruebas.

    NO modifica ni elimina datos: solo genera reportes (DEC-017, DEC-018).
    """
    from config.settings import FECHA_FIN_TRAIN, FECHA_FIN_VALIDACION
    from src.data.data_manager import cargar_datos_crudos
    from src.preprocessing.split import particion_temporal, resumen_particion
    from src.exploratory_analysis.liquidity import auditar_iliquidez
    from src.exploratory_analysis.anomalies import (
        detectar_saltos_reversibles,
        contexto_evento,
    )
    from src.exploratory_analysis.stat_tests import (
        pruebas_estacionariedad,
        pruebas_rendimientos,
    )

    RUTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    rend_log = conjunto["rend_log"]
    precios = conjunto["precios"]

    # 1. Partición temporal (solo se registra; el test queda intocable).
    part = particion_temporal(rend_log, FECHA_FIN_TRAIN, FECHA_FIN_VALIDACION)
    resumen_particion(part).to_csv(RUTA_RESULTADOS / "particion_temporal.csv",
                                   index=False, encoding="utf-8")

    # 2. Iliquidez sobre datos crudos (umbrales de referencia).
    crudos = cargar_datos_crudos()
    iliq = auditar_iliquidez(crudos)
    iliq.to_csv(RUTA_RESULTADOS / "auditoria_iliquidez_umbral.csv",
                index=False, encoding="utf-8")
    logger.info("Empresas que superan el umbral de iliquidez: %s",
                ", ".join(iliq.loc[iliq["supera_umbral"], "empresa"]))

    # 3. Saltos reversibles (posibles precios anómalos) + contexto OHLCV.
    saltos = detectar_saltos_reversibles(rend_log)
    saltos.to_csv(RUTA_RESULTADOS / "saltos_reversibles.csv",
                  index=False, encoding="utf-8")
    contextos = []
    for _, fila in saltos.iterrows():
        clave = next((k for k in crudos if k.startswith(_prefijo(fila["empresa"]))), None)
        if clave is None:
            continue
        ctx = contexto_evento(crudos[clave], fila["fecha_salto"]).reset_index()
        ctx.insert(0, "empresa", fila["empresa"])
        contextos.append(ctx)
    if contextos:
        pd.concat(contextos).to_csv(RUTA_RESULTADOS / "contexto_saltos.csv",
                                    index=False, encoding="utf-8")

    # 4. Pruebas formales SOLO sobre entrenamiento.
    train_r = part["train"]
    train_p = precios.loc[precios.index <= pd.Timestamp(FECHA_FIN_TRAIN)]
    pruebas_estacionariedad(train_p).assign(serie_tipo="precio").to_csv(
        RUTA_RESULTADOS / "pruebas_estacionariedad_precios.csv",
        index=False, encoding="utf-8")
    pruebas_estacionariedad(train_r.dropna(how="all")).assign(
        serie_tipo="rendimiento_log").to_csv(
        RUTA_RESULTADOS / "pruebas_estacionariedad_rendimientos.csv",
        index=False, encoding="utf-8")
    pruebas_rendimientos(train_r).to_csv(
        RUTA_RESULTADOS / "pruebas_rendimientos_train.csv",
        index=False, encoding="utf-8")
    return part


def etapa_fase5(conjunto):
    """Fase 5: congela la partición temporal en archivos y verifica el orden.

    Guarda train / validación / test de rendimientos log y precios en
    ``datos/particiones/`` junto con una huella SHA-256 de cada bloque
    (DEC-019). No modifica datos: solo reparte por fechas de corte.
    """
    from config.settings import FECHA_FIN_TRAIN, FECHA_FIN_VALIDACION
    from config.environment import RUTA_PARTICIONES
    from src.preprocessing.split import (
        NOMBRES_BLOQUES,
        particion_temporal,
        verificar_sin_leakage,
        guardar_particiones,
        guardar_huellas,
        huella,
    )

    series = {"rendimientos_log": conjunto["rend_log"],
              "precios": conjunto["precios"]}
    huellas = {}
    part_rend = None
    for nombre_base, df in series.items():
        part = particion_temporal(df, FECHA_FIN_TRAIN, FECHA_FIN_VALIDACION)
        verificar_sin_leakage(part, df)
        guardar_particiones(part, RUTA_PARTICIONES, nombre_base)
        for bloque in NOMBRES_BLOQUES:
            huellas[f"{nombre_base}_{bloque}"] = huella(part[bloque])
        if nombre_base == "rendimientos_log":
            part_rend = part
    guardar_huellas(huellas, RUTA_PARTICIONES / "huellas.json")
    logger.info("Fase 5: particiones guardadas en %s", RUTA_PARTICIONES)
    return part_rend


def _prefijo(nombre_empresa):
    """Prefijo del archivo crudo a partir del nombre de la empresa (TICKERS)."""
    from config.settings import TICKERS
    ticker = TICKERS.get(nombre_empresa, nombre_empresa)
    return ticker.replace(".", "_")


def main():
    _configurar_logging()
    logger.info("=== INICIO: Fases 2, 3 y 3.5 ===")

    resultados = etapa_descarga()
    reporte_calidad = etapa_validacion(resultados)
    conjunto = etapa_procesamiento(resultados)
    etapa_imputacion(resultados, conjunto)
    resumen = etapa_exploratoria(conjunto, reporte_calidad)
    etapa_fase4(conjunto)
    etapa_fase5(conjunto)

    ok = sum(1 for r in resultados.values() if r["estado"] == "ok")
    error = sum(1 for r in resultados.values() if r["estado"] == "error")
    logger.info("Descargas exitosas: %d | con errores: %d", ok, error)

    from src.exploratory_analysis.resumen import imprimir_resumen
    imprimir_resumen(resumen)
    logger.info("=== FIN: Fases 2, 3 y 3.5 ===")


if __name__ == "__main__":
    main()