"""
fase6.py — Ejecución de la Fase 6: benchmark de Markowitz
==========================================================

Flujo (DEC-020):
    1. Carga SOLO entrenamiento y validación (``cargar_entrenamiento_validacion``).
    2. Estima media y covarianza con entrenamiento.
    3. Construye 3 portafolios (1/N, mínima varianza, máximo Sharpe) para dos
       universos: las 9 empresas y las líquidas según entrenamiento.
    4. Los pesos quedan FIJOS y se evalúan en entrenamiento (dentro de
       muestra) y en validación (fuera de muestra).
    5. Guarda resultados en ``resultados/``.

No toca el bloque de prueba.

Ejecutar:  python -m src.portfolio.fase6
"""

import logging

import pandas as pd

from config.environment import RUTA_GRAFICOS, RUTA_PARTICIONES, RUTA_RESULTADOS
from config.settings import PESO_MAXIMO_ACTIVO, TASA_LIBRE_RIESGO_ANUAL
from src.portfolio.markowitz import (
    estimar_parametros,
    frontera_eficiente,
    log_a_simple,
    maximo_sharpe,
    minima_varianza,
    pesos_igual,
    retorno_esperado,
    seleccionar_universo_liquido,
    volatilidad,
)
from src.portfolio.metricas import metricas_portafolio
from src.preprocessing.split import cargar_entrenamiento_validacion

logger = logging.getLogger(__name__)

NOMBRES_PORTAFOLIOS = {
    "igual": "Igual ponderación (1/N)",
    "min_var": "Mínima varianza",
    "max_sharpe": "Máximo Sharpe",
}


def construir_portafolios(rend_train_simple, peso_max=PESO_MAXIMO_ACTIVO,
                          rf=TASA_LIBRE_RIESGO_ANUAL):
    """Devuelve (dict de pesos por portafolio, parámetros estimados)."""
    par = estimar_parametros(rend_train_simple)
    pesos = {
        "igual": pesos_igual(rend_train_simple.columns, peso_max),
        "min_var": minima_varianza(par["cov"], peso_max),
        "max_sharpe": maximo_sharpe(par["mu"], par["cov"], rf, peso_max),
    }
    return pesos, par


def ejecutar_fase6(guardar=True):
    datos = cargar_entrenamiento_validacion(RUTA_PARTICIONES, "rendimientos_log")
    train = log_a_simple(datos["train"])
    valid = log_a_simple(datos["validacion"])

    liquidos, iliquidos, tabla_liq = seleccionar_universo_liquido(datos["train"])
    universos = {"9_empresas": list(train.columns), "liquidas": liquidos}
    logger.info("Universo líquido (solo train): %s | ilíquidas: %s",
                liquidos, iliquidos)

    filas_pesos, filas_met, filas_par, fronteras = [], [], [], {}
    for nombre_u, columnas in universos.items():
        pesos, par = construir_portafolios(train[columnas])
        fronteras[nombre_u] = (frontera_eficiente(par["mu"], par["cov"]), par, pesos)
        for activo in columnas:
            filas_par.append({
                "universo": nombre_u, "empresa": activo,
                "retorno_anual_train": par["mu"][activo],
                "volatilidad_anual_train": float(par["cov"].loc[activo, activo] ** 0.5),
                "observaciones_usadas": par["n_obs"],
                "filas_descartadas": par["n_descartadas"],
            })
        for clave, w in pesos.items():
            for activo, peso in w.items():
                filas_pesos.append({"universo": nombre_u, "portafolio": clave,
                                    "empresa": activo, "peso": float(peso)})
            esperado = {"retorno_esperado_train": retorno_esperado(w.to_numpy(), par["mu"]),
                        "volatilidad_esperada_train": volatilidad(w.to_numpy(), par["cov"])}
            for bloque, rend in (("train", train), ("validacion", valid)):
                m = metricas_portafolio(rend[columnas], w)
                filas_met.append({"universo": nombre_u, "portafolio": clave,
                                  "bloque": bloque, **esperado, **m})

    res = {
        "pesos": pd.DataFrame(filas_pesos),
        "metricas": pd.DataFrame(filas_met),
        "parametros": pd.DataFrame(filas_par),
        "liquidez_train": tabla_liq,
    }
    if guardar:
        RUTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
        res["pesos"].to_csv(RUTA_RESULTADOS / "fase6_pesos.csv", index=False)
        res["metricas"].to_csv(RUTA_RESULTADOS / "fase6_metricas.csv", index=False)
        res["parametros"].to_csv(RUTA_RESULTADOS / "fase6_parametros_train.csv", index=False)
        tabla_liq.to_csv(RUTA_RESULTADOS / "fase6_universo_liquidez_train.csv")
        _graficar_fronteras(fronteras)
    return res


def _graficar_fronteras(fronteras):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    RUTA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    fig, ejes = plt.subplots(1, len(fronteras), figsize=(13, 5), squeeze=False)
    for eje, (nombre, (fr, par, pesos)) in zip(ejes[0], fronteras.items()):
        eje.plot(fr["volatilidad"], fr["retorno"], color="black", label="Frontera (con tope)")
        for activo in par["mu"].index:
            eje.scatter(par["cov"].loc[activo, activo] ** 0.5, par["mu"][activo],
                        color="gray", s=18)
            eje.annotate(activo, (par["cov"].loc[activo, activo] ** 0.5,
                                  par["mu"][activo]), fontsize=7)
        for clave, w in pesos.items():
            eje.scatter(volatilidad(w.to_numpy(), par["cov"]),
                        retorno_esperado(w.to_numpy(), par["mu"]),
                        s=70, label=NOMBRES_PORTAFOLIOS[clave])
        eje.set_title(f"Universo: {nombre} (estimado con entrenamiento)")
        eje.set_xlabel("Volatilidad anual")
        eje.set_ylabel("Retorno anual esperado")
        eje.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(RUTA_GRAFICOS / "fase6_frontera_eficiente.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    r = ejecutar_fase6()
    pd.set_option("display.width", 200)
    print(r["pesos"].pivot_table(index=["universo", "empresa"],
                                 columns="portafolio", values="peso").round(3))
    print(r["metricas"].round(4).to_string(index=False))
