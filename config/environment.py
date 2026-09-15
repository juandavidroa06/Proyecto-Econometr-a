"""
environment.py — Variables de entorno y rutas
==============================================

Este archivo gestiona las rutas del sistema y las variables de entorno
necesarias para el proyecto.

Propósito:
    - Centralizar el manejo de rutas para evitar errores.
    - Facilitar la reproducibilidad en diferentes sistemas operativos.
    - Separar configuración técnica de la lógica del negocio.

NOTA: No almacenar credenciales ni datos sensibles en este archivo.
"""

import os
from pathlib import Path

# =============================================================================
# RAÍZ DEL PROYECTO
# =============================================================================

# Detecta automáticamente la raíz del proyecto buscando este archivo.
# Funciona sin importar desde dónde se ejecute el script.
RAIZ = Path(__file__).resolve().parent.parent

# =============================================================================
# RUTAS PRINCIPALES
# =============================================================================

RUTA_DATOS_CRUDOS = RAIZ / "datos" / "crudos"
RUTA_DATOS_PROCESADOS = RAIZ / "datos" / "procesados"
RUTA_DATOS_METADATA = RAIZ / "datos" / "metadata"
RUTA_NOTEBOOKS = RAIZ / "notebooks"
RUTA_SRC = RAIZ / "src"
RUTA_MODELOS = RAIZ / "modelos"
RUTA_RESULTADOS = RAIZ / "resultados"
RUTA_GRAFICOS = RAIZ / "resultados" / "graficos"
RUTA_INFORMES = RAIZ / "informes"
RUTA_TESTS = RAIZ / "tests"
RUTA_CONFIG = RAIZ / "config"
RUTA_DOCS = RAIZ / "docs"

# =============================================================================
# FUNCIONES UTILITARIAS
# =============================================================================


def verificar_estructura():
    """
    Verifica que todas las carpetas requeridas existan.

    Retorna:
        dict: Diccionario con el estado de cada carpeta (True/False).

    Uso:
        from config.environment import verificar_estructura
        estado = verificar_estructura()
        print(estado)
    """
    carpetas = {
        "datos/crudos": RUTA_DATOS_CRUDOS,
        "datos/procesados": RUTA_DATOS_PROCESADOS,
        "datos/metadata": RUTA_DATOS_METADATA,
        "notebooks": RUTA_NOTEBOOKS,
        "src": RUTA_SRC,
        "modelos": RUTA_MODELOS,
        "resultados": RUTA_RESULTADOS,
        "informes": RUTA_INFORMES,
        "tests": RUTA_TESTS,
        "config": RUTA_CONFIG,
        "docs": RUTA_DOCS,
    }

    estado = {}
    for nombre, ruta in carpetas.items():
        estado[nombre] = ruta.exists()

    return estado


def imprimir_estado_estructura():
    """Imprime el estado de la estructura de carpetas de forma legible."""
    estado = verificar_estructura()
    print("=" * 50)
    print("ESTADO DE LA ESTRUCTURA DEL PROYECTO")
    print("=" * 50)
    for carpeta, existe in estado.items():
        simbolo = "OK" if existe else "FALTA"
        print(f"  [{simbolo}] {carpeta}")
    print("=" * 50)


# =============================================================================
# EJECUCIÓN DIRECTA
# =============================================================================

if __name__ == "__main__":
    imprimir_estado_estructura()
