"""
prospectiva.py — Prueba prospectiva (Fase 21, plan DEC-048)
===========================================================

Evalúa los modelos y estrategias del proyecto en datos POSTERIORES a toda la
muestra (desde el 2026-09-15), que no existían cuando se fijó el plan.

    - Historia: muestra completa 2020-01 a 2026-09-14 (con la regla de
      DEC-034 en 2025–2026), leída con ``evaluacion_final.cargar_muestra_completa``.
    - Evaluación confirmatoria: los primeros ``DIAS_CONFIRMATORIOS`` días
      bursátiles del bloque prospectivo, una sola vez (aunque se hayan
      descargado más días; así la fecha de corte no se elige mirando los
      resultados). Las corridas posteriores con todos los días disponibles son
      de SEGUIMIENTO (descriptivas).
    - Mismos procedimientos y pruebas que la evaluación final (familias H15-1
      a H15-5, con ``evaluacion_final.ejecutar_variante``) más las hipótesis
      P5 (acierto direccional de la LSTM con la prueba HAC) y P6 (volatility
      targeting del 1/N) de DEC-048.
    - Modo ``simulacro``: ejecuta TODO el código con historia 2020–2024 y los
      primeros días de 2025 como si fueran prospectivos, solo para comprobar
      que el código funciona (no es una evaluación: esos datos ya se vieron).

Ejecutar:
    python -m src.prospectiva --simulacro
    python -m src.prospectiva --datos datos/crudos_prospectiva/hasta_AAAA-MM-DD [--seguimiento]
"""

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from config.environment import RUTA_RESULTADOS
from config.settings import FECHA_FIN_VALIDACION, LIMITE_SECTOR
from src.backtesting import fase14, motor
from src.extensiones import inferencia as inf
from src.extensiones import portafolios_pronostico as pp
from src.portfolio.markowitz import log_a_simple

logger = logging.getLogger(__name__)

DIAS_CONFIRMATORIOS = 252           # un año bursátil (DEC-048)
DIAS_SIMULACRO = 126                # el simulacro se ejecutó con 126 días
RUTA = RUTA_RESULTADOS / "prospectiva"
BASES = ("rendimientos_log", "volumen", "externos", "tasas")


def recortar(bloque, dias):
    """Los primeros ``dias`` días bursátiles (calendario de las acciones) de cada base."""
    calendario = bloque["rendimientos_log"].index.sort_values()
    if len(calendario) < dias:
        raise ValueError(f"El bloque prospectivo tiene {len(calendario)} días bursátiles; "
                         f"se necesitan {dias} para la evaluación confirmatoria (DEC-048).")
    corte = calendario[dias - 1]
    return {b: df[df.index <= corte] for b, df in bloque.items()}


def armar_bloques(historia, evaluacion):
    """{base: (historia, evaluación)} con validaciones de orden y columnas."""
    bloques = {}
    for b in BASES:
        h, e = historia[b].sort_index(), evaluacion[b].sort_index()
        if list(h.columns) != list(e.columns):
            raise ValueError(f"{b}: las columnas de la historia y la evaluación no coinciden.")
        if not h.index.max() < e.index.min():
            raise ValueError(f"{b}: la evaluación no empieza después de la historia (leakage).")
        bloques[b] = (h, e)
    return bloques


def hipotesis_adicionales(bloques, carpeta):
    """P5 (dirección de la LSTM, prueba HAC) y P6 (volatility targeting del 1/N)."""
    pron = pd.read_csv(carpeta / "media_pronosticos.csv")
    p5 = inf.direccional_hac(pron["fecha_objetivo"], pron["objetivo"], pron["lstm"])
    p5 = pd.DataFrame([{"hipotesis": "P5: acierto direccional de la LSTM > azar (HAC, unilateral)",
                        **p5, "confirmada_5pct": bool(p5["pvalor"] < 0.05)}])

    rend = log_a_simple(pd.concat(bloques["rendimientos_log"]))
    ini_eval, fin_eval = bloques["rendimientos_log"][1].index.min(), bloques["rendimientos_log"][1].index.max()
    inicio = (ini_eval.to_period("M") - 1).start_time.strftime("%Y-%m-%d")
    rf = fase14.tasa_diaria(pd.concat(bloques["tasas"]), rend.index[rend.index >= pd.Timestamp(inicio)])
    universos = {"9_empresas": (list(rend.columns), LIMITE_SECTOR, ["igual", "vol_target_1n"])}
    res = pp.correr_b12(rend, rf, universos, inicio, fin_eval, {"evaluacion": (ini_eval, fin_eval)},
                        {"20pb": fase14.COSTOS["20pb"]})
    a = res["series"][("9_empresas", "vol_target_1n", "20pb")]
    b = res["series"][("9_empresas", "igual", "20pb")]
    d = motor.diferencia_sharpe(a - rf.reindex(a.index), b - rf.reindex(b.index), **fase14.BOOT)
    # Unilateral (H1: Sharpe mayor): mitad del p bilateral si la diferencia es positiva.
    p_uni = d["pvalor"] / 2 if d["dif_sharpe"] > 0 else 1 - d["pvalor"] / 2
    p6 = pd.DataFrame([{"hipotesis": "P6: Sharpe neto del volatility targeting > 1/N (9 empresas, 20 pb)",
                        **d, "pvalor_unilateral": p_uni, "confirmada_5pct": bool(p_uni < 0.05)}])
    return {"p5_direccion_lstm": p5, "p6_vol_target": p6, "p6_metricas": res["metricas"]}


def evaluar(historia, evaluacion, carpeta):
    """Corre las familias de la evaluación final y P5–P6, con y sin la regla de DEC-034."""
    from src.evaluacion_final import aplicar_regla, ejecutar_variante, huellas_resultados

    bloques = armar_bloques(historia, evaluacion)
    con_regla, detectadas = aplicar_regla(bloques)
    carpeta.mkdir(parents=True, exist_ok=True)
    detectadas.to_csv(carpeta / "fechas_detectadas.csv", index=False)
    variantes = {"con_regla": con_regla}
    if not detectadas.empty:
        variantes["sin_regla"] = bloques
    for nombre, bl in variantes.items():
        destino = carpeta / nombre
        ejecutar_variante(bl, destino)
        for clave, df in hipotesis_adicionales(bl, destino).items():
            df.to_csv(destino / f"{clave}.csv", index=False)
    meta = {"ejecutado": datetime.now().isoformat(timespec="seconds"),
            "historia": [str(historia["rendimientos_log"].index.min().date()),
                         str(historia["rendimientos_log"].index.max().date())],
            "evaluacion": [str(evaluacion["rendimientos_log"].index.min().date()),
                           str(evaluacion["rendimientos_log"].index.max().date())],
            "dias_evaluacion": int(len(evaluacion["rendimientos_log"])),
            "fechas_detectadas": [str(f.date()) for f in detectadas["fecha"]],
            "huellas": huellas_resultados(carpeta)}
    (carpeta / "huellas_resultados.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False),
                                                     encoding="utf-8")
    return meta


def simulacro():
    """Prueba de funcionamiento con datos ya vistos (NO es una evaluación)."""
    from src.evaluacion_final import cargar_muestra_completa

    muestra, _ = cargar_muestra_completa()
    corte = pd.Timestamp(FECHA_FIN_VALIDACION)
    historia = {b: muestra[b][muestra[b].index <= corte] for b in BASES}
    futuro = {b: muestra[b][muestra[b].index > corte] for b in BASES}
    return evaluar(historia, recortar(futuro, DIAS_SIMULACRO), RUTA / "simulacro")


def ejecutar(datos, seguimiento=False):
    from src.data.prospectiva import cargar_bloque
    from src.evaluacion_final import cargar_muestra_completa

    bloque = cargar_bloque(datos)
    historia, _ = cargar_muestra_completa()
    if seguimiento:
        fin = bloque["rendimientos_log"].index.max().date()
        return evaluar(historia, bloque, RUTA / f"seguimiento_hasta_{fin}")
    destino = RUTA / "confirmatoria"
    if destino.exists() and any(destino.iterdir()):
        raise FileExistsError(f"{destino} ya tiene resultados: la evaluación confirmatoria se hace una vez.")
    return evaluar(historia, recortar(bloque, DIAS_CONFIRMATORIOS), destino)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Prueba prospectiva (DEC-048).")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--simulacro", action="store_true", help="Prueba de funcionamiento con datos ya vistos.")
    g.add_argument("--datos", help="Carpeta datos/crudos_prospectiva/hasta_AAAA-MM-DD.")
    p.add_argument("--seguimiento", action="store_true",
                   help="Usa todos los días disponibles (descriptivo, no confirmatorio).")
    a = p.parse_args()
    meta = simulacro() if a.simulacro else ejecutar(a.datos, a.seguimiento)
    print(json.dumps({k: v for k, v in meta.items() if k != "huellas"}, indent=2, ensure_ascii=False))
