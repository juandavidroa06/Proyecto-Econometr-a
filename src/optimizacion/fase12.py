"""
fase12.py — Ejecución de las Fases 12–13: optimización con restricciones
=========================================================================

Flujo (DEC-031):
    1. Carga SOLO entrenamiento y validación (rendimientos y tasas).
    2. Insumos estimados con entrenamiento (rendimientos simples, filas
       completas): media histórica, covarianza muestral y de Ledoit-Wolf,
       escenarios para el CVaR, tasa libre de riesgo = IBR overnight medio
       de entrenamiento convertido a efectiva anual.
    3. Siete portafolios con restricciones: suma 1, sin cortos, máximo 30 %
       por acción y, en la variante con sectores, máximo 40 % por sector.
    4. Pesos fijos evaluados en entrenamiento y validación (Sharpe con el
       IBR medio de cada bloque); CVaR realizado, concentración y
       exposición sectorial.

No toca el bloque de prueba. El rebalanceo periódico es la Fase 14.

Ejecutar:  python -m src.optimizacion.fase12
"""

import logging

import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf

from config.environment import RUTA_GRAFICOS, RUTA_PARTICIONES, RUTA_RESULTADOS
from config.settings import (
    DIAS_BURSATILES_ANIO,
    LIMITE_SECTOR,
    NIVEL_CVAR_OPTIMIZACION,
    PESO_MAXIMO_ACTIVO,
    SECTORES,
)
from src.data.externos import ibr_efectiva_anual
from src.optimizacion import optimizadores as opt
from src.portfolio.markowitz import log_a_simple, seleccionar_universo_liquido
from src.portfolio.metricas import metricas_portafolio, rendimiento_diario
from src.preprocessing.split import cargar_entrenamiento_validacion
from src.riesgo.medidas import cola_empirica

logger = logging.getLogger(__name__)

NOMBRES = {
    "igual": "1/N",
    "min_var_muestral": "Mínima varianza (muestral)",
    "min_var_lw": "Mínima varianza (Ledoit-Wolf)",
    "min_cvar": "Mínimo CVaR 95 %",
    "paridad_riesgo": "Paridad de riesgo (Ledoit-Wolf)",
    "max_sharpe": "Máximo Sharpe (Ledoit-Wolf, IBR)",
    "max_retorno_vol_1n": "Máx. retorno con vol ≤ vol(1/N)",
}


def insumos(rend_train):
    """Media, covarianzas (anuales) y escenarios diarios con filas completas."""
    completos = rend_train.dropna(how="any")
    if len(completos) < 2 * completos.shape[1]:
        raise ValueError("Muy pocas filas completas para estimar la covarianza.")
    mu = completos.mean() * DIAS_BURSATILES_ANIO
    cov = completos.cov() * DIAS_BURSATILES_ANIO
    lw = LedoitWolf().fit(completos.to_numpy())
    cov_lw = pd.DataFrame(lw.covariance_ * DIAS_BURSATILES_ANIO,
                          index=completos.columns, columns=completos.columns)
    return {"mu": mu, "cov": cov, "cov_lw": cov_lw, "escenarios": completos,
            "encogimiento_lw": float(lw.shrinkage_),
            "filas_descartadas": int(len(rend_train) - len(completos))}


def construir(ins, restr, rf):
    """Diccionario {portafolio: pesos} y avisos (p. ej. Sharpe degenerado)."""
    activos = restr.activos
    pesos, avisos = {}, []
    pesos["igual"] = pd.Series(np.full(len(activos), 1 / len(activos)), index=activos)
    try:
        restr.verificar(pesos["igual"].to_numpy())
    except ValueError:
        # 1/N viola el límite sectorial: se usa el portafolio factible más
        # cercano a 1/N (mínima distancia euclidiana).
        objetivo = np.full(len(activos), 1 / len(activos))
        pesos["igual"] = opt._resolver(lambda w: float(((w - objetivo) ** 2).sum()), restr)
        avisos.append("1/N infactible con el límite sectorial: se usa el factible más cercano.")
    pesos["min_var_muestral"] = opt.minima_varianza(ins["cov"], restr)
    pesos["min_var_lw"] = opt.minima_varianza(ins["cov_lw"], restr)
    pesos["min_cvar"] = opt.minimo_cvar(ins["escenarios"], NIVEL_CVAR_OPTIMIZACION, restr)
    pesos["paridad_riesgo"] = opt.paridad_riesgo(ins["cov_lw"], restr)
    pesos["max_sharpe"] = opt.maximo_sharpe(ins["mu"], ins["cov_lw"], rf, restr)
    S = ins["cov_lw"].to_numpy()
    sharpe_max = (float(pesos["max_sharpe"] @ ins["mu"]) - rf) / np.sqrt(
        float(pesos["max_sharpe"] @ S @ pesos["max_sharpe"]))
    if sharpe_max <= 0:
        avisos.append(f"Máximo Sharpe degenerado: el mejor Sharpe de entrenamiento es "
                      f"{sharpe_max:.3f} <= 0 (ningún portafolio supera al IBR).")
    w1n = pesos["igual"].to_numpy()
    vol_1n = float(np.sqrt(w1n @ S @ w1n))
    pesos["max_retorno_vol_1n"] = opt.maximo_retorno(ins["mu"], ins["cov_lw"], vol_1n, restr)
    return pesos, avisos


def _tasa_bloque(tasas):
    return float(ibr_efectiva_anual(tasas.iloc[:, 0]).mean())


def ejecutar_fase12(guardar=True):
    rend = cargar_entrenamiento_validacion(RUTA_PARTICIONES, "rendimientos_log")
    tasas = cargar_entrenamiento_validacion(RUTA_PARTICIONES, "tasas")
    tr, va = log_a_simple(rend["train"]), log_a_simple(rend["validacion"])
    rf = {"train": _tasa_bloque(tasas["train"]), "validacion": _tasa_bloque(tasas["validacion"])}
    logger.info("Tasa libre de riesgo efectiva anual (IBR medio): %s", rf)
    liquidos, _, _ = seleccionar_universo_liquido(rend["train"])
    universos = {"9_empresas": list(tr.columns), "liquidas": liquidos}

    filas_pesos, filas_met, filas_aviso, filas_ins = [], [], [], []
    for nombre_u, activos in universos.items():
        ins = insumos(tr[activos])
        filas_ins.append({"universo": nombre_u, "encogimiento_ledoit_wolf": ins["encogimiento_lw"],
                          "filas_descartadas_train": ins["filas_descartadas"],
                          "rf_train": rf["train"], "rf_validacion": rf["validacion"]})
        for variante, limite in (("sin_sectores", None), ("con_sectores", LIMITE_SECTOR)):
            restr = opt.Restricciones(activos, PESO_MAXIMO_ACTIVO, SECTORES, limite)
            pesos, avisos = construir(ins, restr, rf["train"])
            for a in avisos:
                filas_aviso.append({"universo": nombre_u, "variante": variante, "aviso": a})
                logger.warning("%s | %s: %s", nombre_u, variante, a)
            for clave, w in pesos.items():
                rc = opt.contribuciones_riesgo(w.to_numpy(), ins["cov_lw"])
                for activo, peso, c in zip(w.index, w.to_numpy(), rc):
                    filas_pesos.append({"universo": nombre_u, "variante": variante,
                                        "portafolio": clave, "empresa": activo,
                                        "sector": SECTORES[activo], "peso": float(peso),
                                        "contribucion_riesgo": float(c)})
                expo = restr.exposicion_sectorial(w.to_numpy())
                for bloque, datos in (("train", tr), ("validacion", va)):
                    m = metricas_portafolio(datos[activos], w, rf=rf[bloque])
                    r, _ = rendimiento_diario(datos[activos], w)
                    _, cvar = cola_empirica(r, 1 - NIVEL_CVAR_OPTIMIZACION)
                    filas_met.append({
                        "universo": nombre_u, "variante": variante, "portafolio": clave,
                        "bloque": bloque, "rf": rf[bloque], **m,
                        "cvar95_diario_realizado": float(cvar),
                        "n_efectivo": float(1 / (w.to_numpy() ** 2).sum()),
                        "peso_financiero": expo.get("financiero", 0.0),
                    })
    res = {"pesos": pd.DataFrame(filas_pesos), "metricas": pd.DataFrame(filas_met),
           "avisos": pd.DataFrame(filas_aviso, columns=["universo", "variante", "aviso"]),
           "insumos": pd.DataFrame(filas_ins)}
    if guardar:
        RUTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
        for clave in res:
            res[clave].to_csv(RUTA_RESULTADOS / f"fase12_{clave}.csv", index=False)
        _graficar(res["pesos"])
    return res


def _graficar(pesos):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    RUTA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    fig, ejes = plt.subplots(1, 2, figsize=(15, 5.5), sharey=True)
    empresas = sorted(pesos["empresa"].unique())
    paleta = plt.get_cmap("tab10")
    colores = {e: paleta(i) for i, e in enumerate(empresas)}   # mismo color en ambos paneles
    for eje, universo in zip(ejes, ("9_empresas", "liquidas")):
        d = pesos[(pesos["universo"] == universo) & (pesos["variante"] == "con_sectores")]
        tabla = d.pivot_table(index="portafolio", columns="empresa", values="peso")
        tabla = tabla.reindex([k for k in NOMBRES if k in tabla.index])
        tabla.index = [NOMBRES[k] for k in tabla.index]
        tabla.plot(kind="barh", stacked=True, ax=eje, width=0.75, legend=False,
                   color=[colores[c] for c in tabla.columns])
        eje.set_xlim(0, 1)
        eje.set_title(f"Universo {universo} — con límite sectorial 40 %", fontsize=9)
        eje.set_xlabel("Peso")
        eje.tick_params(labelsize=8)
    from matplotlib.patches import Patch
    fig.legend([Patch(color=colores[e]) for e in empresas], empresas,
               loc="lower center", ncol=9, fontsize=7)
    fig.suptitle("Fase 12: pesos estimados con entrenamiento (2020–2023)", fontsize=10)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    fig.savefig(RUTA_GRAFICOS / "fase12_pesos.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    r = ejecutar_fase12()
    pd.set_option("display.width", 250)
    print(r["insumos"].round(4).to_string(index=False))
    print(r["avisos"].to_string(index=False))
    m = r["metricas"]
    cols = ["universo", "variante", "portafolio", "bloque", "retorno_anual", "volatilidad_anual",
            "sharpe", "max_drawdown", "cvar95_diario_realizado", "n_efectivo", "peso_financiero"]
    print(m[cols].round(4).to_string(index=False))
