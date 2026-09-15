"""
resumen.py — Resumen descriptivo automático
=============================================

Genera un resumen textual/dict de carácter DESCRIPTIVO sobre los datos.
No constituye recomendación de inversión: solo describe los datos observados.

Ejemplos de frases que se generan:
    - "El activo con mayor rendimiento medio es X".
    - "El par con mayor correlación es (X, Y) con r = 0.82".

Se evitan frases de recomendación ("compre", "mejor inversión").
"""

import json

import pandas as pd

from config.environment import RUTA_RESULTADOS
from src.exploratory_analysis.correlations import (
    pares_mayor_correlacion,
    pares_menor_correlacion,
)


def generar_resumen_descriptivo(df_rendimientos, matriz_corr=None,
                                 reporte_calidad=None):
    """Genera un resumen descriptivo de los datos.

    Parámetros:
        df_rendimientos: DataFrame ancho de rendimientos (columnas = activos).
        matriz_corr: matriz de correlación (opcional; se calcula si es None).
        reporte_calidad: DataFrame del reporte de calidad (opcional).

    Retorna:
        dict con los resultados descriptivos.
    """
    stats = df_rendimientos.dropna()

    medias = stats.mean()
    volatilidades = stats.std()

    mayor_rendimiento = medias.idxmax()
    mayor_volatilidad = volatilidades.idxmax()
    menor_volatilidad = volatilidades.idxmin()

    if matriz_corr is None:
        matriz_corr = stats.corr()

    mayor_corr = pares_mayor_correlacion(matriz_corr, n=3)
    menor_corr = pares_menor_correlacion(matriz_corr, n=3)

    empresa_mas_datos = df_rendimientos.notna().sum().idxmax() \
        if not df_rendimientos.empty else None

    resumen = {
        "activo_mayor_rendimiento_medio": mayor_rendimiento,
        "rendimiento_medio": float(medias[mayor_rendimiento]),
        "activo_mayor_volatilidad": mayor_volatilidad,
        "volatilidad_mayor": float(volatilidades[mayor_volatilidad]),
        "activo_menor_volatilidad": menor_volatilidad,
        "volatilidad_menor": float(volatilidades[menor_volatilidad]),
        "pares_mayor_correlacion": [
            {"activo_a": a, "activo_b": b, "correlacion": c}
            for (a, b, c) in mayor_corr
        ],
        "pares_menor_correlacion": [
            {"activo_a": a, "activo_b": b, "correlacion": c}
            for (a, b, c) in menor_corr
        ],
        "empresa_mas_observaciones": empresa_mas_datos,
    }

    if reporte_calidad is not None and not reporte_calidad.empty:
        con_problemas = reporte_calidad[
            reporte_calidad["estado"] != "ok"
        ]["empresa"].tolist()
        resumen["empresas_con_problemas_calidad"] = con_problemas

    return resumen


def guardar_resumen(resumen, ruta_archivo=None):
    """Guarda el resumen como JSON en ``resultados/``."""
    if ruta_archivo is None:
        ruta_archivo = RUTA_RESULTADOS / "resumen_descriptivo.json"
    RUTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
    with open(ruta_archivo, "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=4)
    return str(ruta_archivo)


def imprimir_resumen(resumen):
    """Imprime el resumen descriptivo de forma legible."""
    print("=" * 60)
    print("RESUMEN DESCRIPTIVO DE LOS DATOS (NO es recomendación de inversión)")
    print("=" * 60)
    print(f"Activo con mayor rendimiento medio : "
          f"{resumen['activo_mayor_rendimiento_medio']}")
    print(f"Activo con mayor volatilidad      : "
          f"{resumen['activo_mayor_volatilidad']}")
    print(f"Activo con menor volatilidad      : "
          f"{resumen['activo_menor_volatilidad']}")
    print("Pares con mayor correlación:")
    for p in resumen["pares_mayor_correlacion"]:
        print(f"  - {p['activo_a']} <-> {p['activo_b']}: r = {p['correlacion']:.3f}")
    print("Pares con menor correlación:")
    for p in resumen["pares_menor_correlacion"]:
        print(f"  - {p['activo_a']} <-> {p['activo_b']}: r = {p['correlacion']:.3f}")
    if "empresas_con_problemas_calidad" in resumen:
        if resumen["empresas_con_problemas_calidad"]:
            print("Empresas con observaciones de calidad: "
                  f"{', '.join(resumen['empresas_con_problemas_calidad'])}")
        else:
            print("Ninguna empresa presentó observaciones de calidad críticas.")
    print("=" * 60)