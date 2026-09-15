"""
constants.py — Constantes del proyecto
=======================================

Este archivo define constantes que se utilizan a lo largo del proyecto.
A diferencia de settings.py (que contiene parámetros configurables),
aquí se guardan valores fijos y definiciones.

IMPORTANTE: Los valores marcados con [PLACEHOLDER] deben definirse
antes de utilizarlos en el código.
"""

# =============================================================================
# EMPRESAS Y TICKERS
# =============================================================================

# Los tickers de las empresas seleccionadas están definidos en un único lugar:
# config/settings.py (variable TICKERS).
# Para no duplicar información, se referencia esa variable como única fuente.
from config.settings import TICKERS as TICKERS_BVC  # noqa: E402

# =============================================================================
# ÍNDICES DE REFERENCIA (BENCHMARKS)
# =============================================================================

# [PLACEHOLDER] — Índices que servirán como referencia para comparar
# el rendimiento del portafolio.
#
# Ejemplo:
# BENCHMARKS = {
#     "COLCAP": "^COLCAP",
#     "COL20": "^COL20",
# }
BENCHMARKS = {}  # [PLACEHOLDER] — Definir antes de la fase de datos

# =============================================================================
# NOMBRES DE COLUMNAS
# =============================================================================

# Nombres estándar que utilizaremos para las columnas del DataFrame.
# Esto evita errores por diferencias en mayúsculas/minúsculas.
COLUMNA_FECHA = "Fecha"
COLUMNA_PRECIO_APERTURA = "Apertura"
COLUMNA_PRECIO_MAXIMO = "Maximo"
COLUMNA_PRECIO_MINIMO = "Minimo"
COLUMNA_PRECIO_CIERRE = "Cierre"
COLUMNA_VOLUMEN = "Volumen"
COLUMNA_TICKER = "Ticker"
COLUMNA_RENDIMIENTO = "Rendimiento"
COLUMNA_RENDIMIENTO_LOG = "Rendimiento_Log"

# =============================================================================
# VARIABLES ECONÓMICAS EXTERNAS
# =============================================================================

# [PLACEHOLDER] — Variables macroeconómicas que podrían ser relevantes.
# Ejemplo:
# - Tasa de cambio COP/USD
# - Tasa de interés (DLR TES)
# - Inflación (IPC)
# - PIB
VARIABLES_MACRO = {}  # [PLACEHOLDER] — Definir según necesidad

# =============================================================================
# MÉTRICAS ESTÁNDAR
# =============================================================================

# Métricas que utilizaremos para evaluar modelos y portafolios.
METRICAS_RIESGO = [
    "volatilidad",
    "VaR",
    "CVaR",
    "drawdown_maximo",
    "beta",
    "downside_deviation",
]

METRICAS_RENTABILIDAD = [
    "rendimiento_total",
    "rendimiento_anualizado",
    "alpha",
    "sharpe_ratio",
    "sortino_ratio",
    "calmar_ratio",
]

METRICAS_MODELO = [
    "RMSE",
    "MAE",
    "MAPE",
    "R_squared",
    "AIC",
    "BIC",
]

# =============================================================================
# CONFIGURACIÓN DEL AGENTE DE IA
# =============================================================================

# [PLACEHOLDER] — Constantes del agente cuando se implemente.
# AGENTE_VERSION = "0.1.0"
# AGENTE.descripcion = "Agente coordinador de investigación cuantitativa"
