"""
settings.py — Parámetros globales del proyecto
===============================================

Este archivo contiene configuraciones generales que se utilizan
en toda laipeline del proyecto.

IMPORTANTE: Los valores marcados con [PLACEHOLDER] deben definirse
antes de comenzar con la fase correspondiente.

Convención:
    - Los parámetros se organizan por secciones temáticas.
    - Cada parámetro incluye una descripción de su propósito.
    - Los valores por defecto son conservadores y razonables.
"""

# =============================================================================
# RUTAS DEL PROYECTO
# =============================================================================
# Estas rutas son relativas a la raíz del proyecto.
# Se recomienda usar estas constantes en lugar de hardcodear rutas.

import os

# Raíz del proyecto (carpeta donde está este archivo)
RAIZ_PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Carpetas principales
CARPETA_DATOS_CRUDOS = os.path.join(RAIZ_PROYECTO, "datos", "crudos")
CARPETA_DATOS_PROCESADOS = os.path.join(RAIZ_PROYECTO, "datos", "procesados")
CARPETA_DATOS_METADATA = os.path.join(RAIZ_PROYECTO, "datos", "metadata")
CARPETA_MODELOS = os.path.join(RAIZ_PROYECTO, "modelos")
CARPETA_RESULTADOS = os.path.join(RAIZ_PROYECTO, "resultados")

# =============================================================================
# CONFIGURACIÓN DE DATOS
# =============================================================================

# Fuente de datos financieros
FUENTE_DATOS = "yahoo_finance"

# Empresas seleccionadas y sus tickers en Yahoo Finance.
# NOTA: Los tickers de Yahoo Finance para estas acciones usan el sufijo ".CL".
TICKERS = {
    "Celsia": "CELSIA.CL",
    "Banco de Bogota": "BOGOTA.CL",
    "Ecopetrol": "ECOPETROL.CL",
    "ETB": "ETB.CL",
    "Nutresa": "NUTRESA.CL",
    "Banco Davivienda PF": "PFDAVVNDA.CL",
    "Promigas": "PROMIGAS.CL",
    "Mineros SA": "MINEROS.CL",
    "Grupo Bolivar": "GRUBOLIVAR.CL",
}

# Frecuencia / intervalo de las series de tiempo (Yahoo Finance).
# "1d" = diario, "1wk" = semanal, "1mo" = mensual.
FRECUENCIA = "1d"

# Horizonte temporal
FECHA_INICIO = "2020-01-01"
# DEC-021: fecha final FIJA de la muestra. Yahoo Finance trata ``end`` como
# EXCLUSIVO: "2026-09-15" -> última observación 2026-09-14. Es la misma fecha
# solicitada en la descarga original (datos/metadata/metadatos_descarga.json).
# No volver a None: el bloque de prueba crecería con cada descarga.
FECHA_FIN = "2026-09-15"

# Columna de precio utilizada para calcular rendimientos.
# "Adj Close" (precio ajustado) corrige dividendos y splits.
PRECIO_RENDIMIENTOS = "Adj Close"

# Días bursátiles por año (aproximación convencional, no universal).
DIAS_BURSATILES_ANIO = 252

# Divisa de los datos
DIVISA = "COP"  # Opciones: "COP", "USD"

# Ajuste por inflación
AJUSTE_INFLACION = False  # [PLACEHOLDER] — Decidir si se aplica ajuste

# =============================================================================
# CONFIGURACIÓN DE DIVISIÓN TEMPORAL
# =============================================================================

# DEC-017: la partición se define por FECHAS de corte (no por proporciones),
# para que sea explícita y reproducible. Siempre cronológica, nunca aleatoria.
#   train      : fecha <= FECHA_FIN_TRAIN
#   validación : FECHA_FIN_TRAIN < fecha <= FECHA_FIN_VALIDACION
#   test       : fecha  > FECHA_FIN_VALIDACION  (intocable hasta la evaluación)
FECHA_FIN_TRAIN = "2023-12-31"
FECHA_FIN_VALIDACION = "2024-12-31"

# [OBSOLETO tras DEC-017] Se conservan solo por compatibilidad con tests previos.
PROPORCION_TRAIN = 0.70
PROPORCION_VALIDACION = 0.15
PROPORCION_TEST = 0.15

# =============================================================================
# CONFIGURACIÓN DE ANÁLISIS EXPLORATORIO
# =============================================================================

# Nivel de significancia para pruebas estadísticas
NIVEL_SIGNIFICANCIA = 0.05

# Percentiles para detección de outliers
PERCENTIL_OUTLIER_BAJA = 0.01
PERCENTIL_OUTLIER_ALTA = 0.99

# Umbral de z-score para detección exploratoria de valores extremos
UMBRAL_ZSCORE = 3.0

# Auditoría de iliquidez (umbrales de REFERENCIA, no de exclusión; DEC-018)
UMBRAL_PCT_PRECIO_REPETIDO = 0.20   # % de días con precio igual al anterior
UMBRAL_RACHA_MAX_DIAS = 15          # racha máxima de días sin cambio de precio

# Detección de saltos reversibles (posibles precios anómalos; DEC-018)
UMBRAL_SALTO_LOG = 0.15             # |rendimiento log| mínimo para revisar
VENTANA_REVERSION_DIAS = 3          # días para que el salto se revierta

# =============================================================================
# CONFIGURACIÓN DE PORTAFOLIOS (Fase 6 — Markowitz, DEC-020)
# =============================================================================

# Peso máximo por activo (restricción realista; w_i <= 30 %).
PESO_MAXIMO_ACTIVO = 0.30

# Tasa libre de riesgo ANUAL para el Sharpe.
# [PLACEHOLDER] No hay serie de tasas en el proyecto todavía (variables macro
# pendientes). 0.0 es un supuesto provisional que FAVORECE el Sharpe de todos
# los portafolios por igual; sustituir por una tasa real antes del informe.
TASA_LIBRE_RIESGO_ANUAL = 0.0

# =============================================================================
# CONFIGURACIÓN DE VISUALIZACIÓN
# =============================================================================

# Estilo general de los gráficos
ESTILO_GRAFICOS = "seaborn-v0_8-whitegrid"
TAMANO_FIGURA_DEFAULT = (12, 6)
PALETA_COLORES = "viridis"

# =============================================================================
# CONFIGURACIÓN DE REPRODUCIBILIDAD
# =============================================================================

# Semilla para generadores aleatorios
SEMILLA_ALEATORIA = 42

# =============================================================================
# PLACEHOLDER — Configuración del agente de IA
# =============================================================================
# Esta sección se llenará cuando implementemos el agente.
# AGENTE_CONFIG = {}
