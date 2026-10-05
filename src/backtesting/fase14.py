"""
fase14.py — Ejecución de la Fase 14: backtesting walk-forward (plan DEC-032)
============================================================================

Implementa EXACTAMENTE el plan DEC-032:
    - Enero 2021 – diciembre 2024 (solo entrenamiento + validación).
    - Rebalanceo mensual (robustez: trimestral) con ventana móvil de 252 días.
    - Costos por lado de 20 pb (principal), 0 y 50 pb (sensibilidad).
    - Estrategias: 1/N, mínima varianza muestral y Ledoit-Wolf, mínimo
      CVaR 95 %, paridad de riesgo; 9 empresas con límite sectorial 40 %,
      4 líquidas sin límite sectorial; máximo 30 % por acción.
    - H1: Sharpe neto (20 pb) de cada estrategia de riesgo frente al 1/N,
      bootstrap por bloques (21 días, 2 000 réplicas), Holm sobre 8 pruebas.

No toca el bloque de prueba.

Ejecutar:  python -m src.backtesting.fase14
"""

import logging

import numpy as np
import pandas as pd

from config.environment import RUTA_GRAFICOS, RUTA_PARTICIONES, RUTA_RESULTADOS
from config.settings import (
    FECHA_FIN_VALIDACION,
    LIMITE_SECTOR,
    NIVEL_CVAR_OPTIMIZACION,
    PESO_MAXIMO_ACTIVO,
    SECTORES,
    SEMILLA_ALEATORIA,
)
from src.backtesting import motor
from src.comparacion.estadistica import holm
from src.data.externos import ibr_efectiva_anual
from src.optimizacion import optimizadores as opt
from src.optimizacion.fase12 import insumos
from src.portfolio.markowitz import log_a_simple, seleccionar_universo_liquido
from src.preprocessing.split import cargar_entrenamiento_validacion

logger = logging.getLogger(__name__)

INICIO_PRIMER_REBALANCEO = "2020-12-01"   # el de diciembre de 2020 abre el backtesting
VENTANA = 252
COSTOS = {"0pb": 0.0, "20pb": 0.002, "50pb": 0.005}
COSTO_PRINCIPAL = "20pb"
ESTRATEGIAS = ["igual", "min_var_muestral", "min_var_lw", "min_cvar", "paridad_riesgo"]
PERIODOS = {"2021-2023": ("2021-01-01", "2023-12-31"), "2024": ("2024-01-01", "2024-12-31"),
            "total": ("2021-01-01", "2024-12-31")}
BOOT = dict(n_remuestras=2000, largo_bloque=21, semilla=SEMILLA_ALEATORIA)


def pesos_estrategia(estrategia, ventana, restr):
    if estrategia == "igual":
        w = pd.Series(np.full(restr.n, 1 / restr.n), index=restr.activos)
        restr.verificar(w.to_numpy())
        return w
    ins = insumos(ventana)
    if estrategia == "min_var_muestral":
        return opt.minima_varianza(ins["cov"], restr)
    if estrategia == "min_var_lw":
        return opt.minima_varianza(ins["cov_lw"], restr)
    if estrategia == "min_cvar":
        return opt.minimo_cvar(ins["escenarios"], NIVEL_CVAR_OPTIMIZACION, restr)
    if estrategia == "paridad_riesgo":
        return opt.paridad_riesgo(ins["cov_lw"], restr)
    raise ValueError(f"Estrategia desconocida: {estrategia!r}")


def tasa_diaria(tasas, indice):
    """IBR efectivo diario (en la base de 252 días) en el calendario bursátil.

    Cada día usa el último IBR publicado hasta ese día (el IBR se publica a
    las 11:45 a. m.).
    """
    ef = ibr_efectiva_anual(tasas.iloc[:, 0]).sort_index()
    diaria = (1 + ef) ** (1 / 252) - 1
    alineada = diaria.reindex(diaria.index.union(indice)).ffill().reindex(indice)
    if alineada.isna().any():
        raise ValueError("No hay IBR publicado para algunos días del backtesting.")
    return alineada


def ejecutar_fase14(guardar=True):
    rend_log = cargar_entrenamiento_validacion(RUTA_PARTICIONES, "rendimientos_log")
    tasas = cargar_entrenamiento_validacion(RUTA_PARTICIONES, "tasas")
    rend = log_a_simple(pd.concat([rend_log["train"], rend_log["validacion"]]))
    # La tasa solo se necesita desde el primer rebalanceo (el IBR de la
    # muestra empieza el 2020-01-02, después del primer día bursátil).
    rf = tasa_diaria(pd.concat([tasas["train"], tasas["validacion"]]),
                     rend.index[rend.index >= pd.Timestamp(INICIO_PRIMER_REBALANCEO)])
    liquidos, _, _ = seleccionar_universo_liquido(rend_log["train"])
    universos = {"9_empresas": (list(rend.columns), LIMITE_SECTOR), "liquidas": (liquidos, None)}

    filas_met, filas_rot, series, pesos_guardados = [], [], {}, []
    for nombre_u, (activos, limite) in universos.items():
        restr = opt.Restricciones(activos, PESO_MAXIMO_ACTIVO, SECTORES, limite)
        mensuales = motor.fechas_rebalanceo(rend.index, INICIO_PRIMER_REBALANCEO,
                                            FECHA_FIN_VALIDACION, "M")
        trimestrales = motor.fechas_rebalanceo(rend.index, INICIO_PRIMER_REBALANCEO,
                                               FECHA_FIN_VALIDACION, "Q")
        for estrategia in ESTRATEGIAS:
            # Los pesos dependen solo de la ventana: se calculan una vez por fecha.
            objetivos = {}
            for f in mensuales:
                objetivos[f] = pesos_estrategia(estrategia, motor.ventana_estimacion(
                    rend[activos], f, VENTANA), restr)
                pesos_guardados.append({"universo": nombre_u, "estrategia": estrategia,
                                        "fecha": f, **objetivos[f].to_dict()})
            for frecuencia, fechas in (("mensual", mensuales), ("trimestral", trimestrales)):
                obj = {f: objetivos[f] for f in fechas}
                for nombre_c, c in COSTOS.items():
                    if frecuencia == "trimestral" and nombre_c != COSTO_PRINCIPAL:
                        continue
                    diario, rot = motor.simular(rend, obj, c, FECHA_FIN_VALIDACION)
                    clave = (nombre_u, estrategia, frecuencia, nombre_c)
                    series[clave] = diario["neto"]
                    filas_rot.append({"universo": nombre_u, "estrategia": estrategia,
                                      "frecuencia": frecuencia, "costo": nombre_c,
                                      "rotacion_media": float(rot.iloc[1:].mean()),
                                      "costo_total": float(diario["costo"].sum())})
                    for periodo, (ini, fin) in PERIODOS.items():
                        neto = diario["neto"].loc[ini:fin]
                        filas_met.append({"universo": nombre_u, "estrategia": estrategia,
                                          "frecuencia": frecuencia, "costo": nombre_c,
                                          "periodo": periodo, **motor.metricas(neto, rf)})
        # Referencia: invertir al IBR.
        for periodo, (ini, fin) in PERIODOS.items():
            neto = rf.loc[ini:fin]
            neto = neto[neto.index > mensuales[0]]
            m = motor.metricas(neto, rf)
            m["sharpe"] = np.nan                        # exceso idénticamente cero
            filas_met.append({"universo": nombre_u, "estrategia": "ibr", "frecuencia": "-",
                              "costo": "-", "periodo": periodo, **m})

    # H1: diferencia de Sharpe neto (20 pb, mensual, total) frente al 1/N.
    pruebas = []
    for nombre_u in universos:
        base = series[(nombre_u, "igual", "mensual", COSTO_PRINCIPAL)]
        ex_base = base - rf.reindex(base.index)
        for estrategia in ESTRATEGIAS[1:]:
            s = series[(nombre_u, estrategia, "mensual", COSTO_PRINCIPAL)]
            if not s.index.equals(base.index):
                raise ValueError("Las series de las estrategias no están alineadas.")
            d = motor.diferencia_sharpe(s - rf.reindex(s.index), ex_base, **BOOT)
            pruebas.append({"universo": nombre_u, "estrategia": estrategia,
                            "referencia": "igual", **d})
    pruebas = pd.DataFrame(pruebas)
    pruebas["pvalor_holm"] = holm(pruebas["pvalor"]).to_numpy()
    pruebas["significativa_5pct"] = pruebas["pvalor_holm"] < 0.05

    riqueza = pd.DataFrame({f"{u}|{e}": (1 + series[(u, e, "mensual", COSTO_PRINCIPAL)]).cumprod()
                            for u in universos for e in ESTRATEGIAS})
    primer = riqueza.index.min()
    riqueza["ibr"] = (1 + rf.loc[primer:]).cumprod()
    res = {"metricas": pd.DataFrame(filas_met), "rotacion": pd.DataFrame(filas_rot),
           "pruebas": pruebas, "pesos": pd.DataFrame(pesos_guardados),
           "riqueza": riqueza.rename_axis("Date").reset_index()}
    if guardar:
        RUTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
        for clave in res:
            res[clave].to_csv(RUTA_RESULTADOS / f"fase14_{clave}.csv", index=False)
        _graficar(riqueza)
    return res


def _graficar(riqueza):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    RUTA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    fig, ejes = plt.subplots(1, 2, figsize=(15, 5), sharey=True)
    estilos = {"igual": ("black", "-"), "min_var_muestral": ("tab:blue", "-"),
               "min_var_lw": ("tab:cyan", "--"), "min_cvar": ("tab:red", "-"),
               "paridad_riesgo": ("tab:green", "-.")}
    for eje, u in zip(ejes, ("9_empresas", "liquidas")):
        for e, (c, ls) in estilos.items():
            eje.plot(riqueza.index, riqueza[f"{u}|{e}"], color=c, ls=ls, lw=1.2, label=e)
        eje.plot(riqueza.index, riqueza["ibr"], color="gray", lw=1, ls=":", label="IBR")
        eje.axvline(pd.Timestamp("2024-01-01"), color="gray", lw=0.6)
        eje.text(pd.Timestamp("2024-01-15"), eje.get_ylim()[1] * 0.97, "validación", fontsize=7)
        eje.set_title(f"Universo {u} — rebalanceo mensual, costos 20 pb", fontsize=9)
        eje.set_ylabel("Valor de 1 peso invertido")
        eje.legend(fontsize=7)
    fig.suptitle("Fase 14: backtesting walk-forward (ventana móvil de 252 días)", fontsize=10)
    fig.tight_layout()
    fig.savefig(RUTA_GRAFICOS / "fase14_riqueza.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    r = ejecutar_fase14()
    pd.set_option("display.width", 250)
    m = r["metricas"]
    principal = m[(m["frecuencia"].isin(["mensual", "-"])) & (m["costo"].isin([COSTO_PRINCIPAL, "-"]))]
    print(principal.round(4).to_string(index=False))
    print(r["pruebas"].round(4).to_string(index=False))
    print(r["rotacion"].round(4).to_string(index=False))
