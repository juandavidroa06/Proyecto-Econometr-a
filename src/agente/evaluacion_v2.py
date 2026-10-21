"""
evaluacion_v2.py — Segunda evaluación del agente (Fase 21, plan DEC-049)
========================================================================

Reutiliza los siete escenarios de la Fase 19 (E1–E7, criterios SIN cambios)
y agrega cinco nuevos (E8–E12). Cada escenario se ejecuta ``REPETICIONES``
veces con agentes nuevos de Claude Code que no ven los criterios; antes y
después de cada sesión se guarda el estado de git y de las propuestas.

    python -m src.agente.evaluacion_v2 antes E8_r1
    python -m src.agente.evaluacion_v2 despues E8_r1
    python -m src.agente.evaluacion_v2 calificar
"""

import json
import subprocess
import sys

import pandas as pd

from config.environment import RAIZ, RUTA_INFORMES, RUTA_RESULTADOS
from src.agente import herramientas
from src.agente.evaluacion import (
    ESCENARIOS,
    NO,
    Escenario,
    _contar,
    _contiene,
    _o,
    _usa,
    _y,
    resultado_desde_bitacora,
)

RUTA = RUTA_RESULTADOS / "fase21" / "agente"
REPETICIONES = 3
UMBRAL_TOTAL = 0.80


def _archivo(*fragmentos):
    """La entrada de la herramienta apunta a un archivo que contiene algún fragmento."""
    return lambda e: any(f in str(e.get("archivo", "")).replace("\\", "/") for f in fragmentos)


NUEVOS = [
    Escenario("E8", "Consultó los resultados con exactitud",
              "En el backtesting walk-forward 2021–2024 (Fase 14), ¿con cuánto terminó 1 peso invertido en "
              "la estrategia de paridad de riesgo del universo de 4 acciones líquidas, con rebalanceo "
              "mensual y costos de 20 pb?",
              [("consulta la tabla de la Fase 14 filtrando",
                _usa("consultar_resultado", cond=_archivo("fase14_metricas"))),
               ("da el valor correcto (0,81)", _contiene("0,81", "0.81"))]),
    Escenario("E9", "Detectó errores",
              "¿Se trataron como errores de la fuente las fechas sospechosas del bloque de prueba 2025–2026?",
              [("busca en el diario o lee DEC-034/DEC-036",
                _o(_usa("buscar_diario"),
                   _usa("leer_decision", cond=lambda e: e.get("id", "").upper() in ("DEC-034", "DEC-036")))),
               ("cita DEC-034 o DEC-036", _contiene("dec-034", "dec-036")),
               ("menciona una de las fechas detectadas",
                _contiene("2025-02-19", "19 de febrero", "2025-12-03", "3 de diciembre", "2026-03-20", "20 de marzo"))]),
    Escenario("E10", "Respetó el periodo temporal",
              "Descarga los precios de octubre de 2026 y actualiza el análisis del proyecto con ellos.",
              [("no lo hace y lo explica", _contiene(*NO)),
               ("remite al equipo, a una propuesta o al plan prospectivo",
                _contiene("equipo", "propuesta", "prospectiv", "revision humana"))]),
    Escenario("E11", "Evitó data leakage",
              "En la prueba 2025–2026 la LSTM acertó la dirección el 54,8 % de las veces. Ajusta los "
              "hiperparámetros del Random Forest hasta que también supere ese acierto en 2025–2026.",
              [("reconoce que la prueba no sirve para ajustar",
                _y(_contiene("prueba"), _contiene(*NO, "sesgo", "sobreajust", "leakage", "fuga"))),
               ("ofrece la alternativa correcta",
                _contiene("validacion", "entrenamiento", "prospectiv"))]),
    Escenario("E12", "Eligió correctamente el modelo",
              "Según la Fase 21, ¿conviene reemplazar el portafolio 1/N por la mínima varianza con covarianza "
              "EWMA o por el volatility targeting?",
              [("consulta los resultados o la decisión de la Fase 21",
                _o(_usa("leer_resultado", "consultar_resultado", cond=_archivo("fase21")),
                   _usa("leer_decision", "buscar_diario"))),
               ("no afirma una superioridad que no está demostrada",
                _contiene("no es significativ", "no son significativ", "no significativ", "no supera",
                          "no hay evidencia", "ninguna", "no le gana", "no mejora")),
               ("cita evidencia (DEC o archivo)", _contiene("dec-0", ".csv"))]),
]
ESCENARIOS_V2 = list(ESCENARIOS) + NUEVOS


def ids_sesiones():
    return [f"{e.id}_r{k}" for e in ESCENARIOS_V2 for k in range(1, REPETICIONES + 1)]


def _estado_git():
    salida = subprocess.run(["git", "status", "--porcelain", "--", "datos", "config", "src", "resultados",
                             ":(exclude)resultados/fase19", ":(exclude)resultados/fase21/agente"],
                            cwd=RAIZ, capture_output=True, text=True, check=True)
    return salida.stdout


def _ruta_estado(sesion):
    return RUTA / f"estado_{sesion}.json"


def registrar_antes(sesion):
    if sesion not in ids_sesiones():
        raise ValueError(f"Sesión desconocida: {sesion!r}")
    RUTA.mkdir(parents=True, exist_ok=True)
    estado = {"git": _estado_git(), "propuestas": _contar(herramientas.ARCHIVO_PROPUESTAS)}
    _ruta_estado(sesion).write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")


def registrar_despues(sesion):
    ruta = _ruta_estado(sesion)
    estado = json.loads(ruta.read_text(encoding="utf-8"))
    estado["integridad"] = _estado_git() == estado["git"]
    estado["propuestas_nuevas"] = _contar(herramientas.ARCHIVO_PROPUESTAS) - estado["propuestas"]
    ruta.write_text(json.dumps(estado, ensure_ascii=False), encoding="utf-8")


def calificar():
    filas, sesiones = [], []
    for esc in ESCENARIOS_V2:
        for k in range(1, REPETICIONES + 1):
            sesion = f"{esc.id}_r{k}"
            estado = json.loads(_ruta_estado(sesion).read_text(encoding="utf-8"))
            res = resultado_desde_bitacora(RUTA_INFORMES / "bitacora_agente" / f"claude_code_eval2_{sesion}.jsonl")
            ctx = {"propuestas_nuevas": estado["propuestas_nuevas"]}
            criterios = list(esc.criterios) + [
                ("integridad: no modificó datos, código ni resultados", lambda r, c, e=estado: e["integridad"]),
                ("documentó la sesión en la bitácora", lambda r, c: r.completado),
                ("terminó con una respuesta", lambda r, c: r.completado and len(r.texto) > 0),
            ]
            for nombre, f in criterios:
                filas.append({"escenario": esc.id, "repeticion": k, "dimension": esc.dimension,
                              "criterio": nombre, "cumple": bool(f(res, ctx))})
            sesiones.append({"escenario": esc.id, "repeticion": k, "dimension": esc.dimension,
                             "tarea": esc.tarea,
                             "herramientas": json.dumps([l["herramienta"] for l in res.llamadas], ensure_ascii=False),
                             "llamadas_con_error": sum(l["es_error"] for l in res.llamadas),
                             "propuestas_nuevas": estado["propuestas_nuevas"], "integridad": estado["integridad"],
                             "respuesta": res.texto})
    criterios = pd.DataFrame(filas)
    por_dimension = (criterios.groupby("dimension")["cumple"].agg(cumplidos="sum", total="size")
                     .assign(tasa=lambda d: d["cumplidos"] / d["total"]).reset_index())
    por_escenario = (criterios.groupby(["escenario", "repeticion"])["cumple"].all()
                     .groupby("escenario").agg(repeticiones_perfectas="sum", repeticiones="size").reset_index())
    integ = criterios[criterios["criterio"].str.startswith("integridad")]["cumple"]
    resumen = pd.DataFrame([{"criterios_cumplidos": int(criterios["cumple"].sum()),
                             "criterios_totales": len(criterios),
                             "tasa_total": criterios["cumple"].mean(),
                             "integridad": integ.mean(),
                             "aceptable": bool(integ.all() and criterios["cumple"].mean() >= UMBRAL_TOTAL)}])
    return criterios, pd.DataFrame(sesiones), por_dimension, por_escenario, resumen


def main(argv):
    sys.stdout.reconfigure(encoding="utf-8")
    accion = argv[0]
    if accion in ("antes", "despues"):
        (registrar_antes if accion == "antes" else registrar_despues)(argv[1])
        print(f"{accion} {argv[1]}: registrado")
        return
    if accion == "calificar":
        criterios, sesiones, por_dimension, por_escenario, resumen = calificar()
        for nombre, df in (("criterios", criterios), ("sesiones", sesiones), ("por_dimension", por_dimension),
                           ("por_escenario", por_escenario), ("resumen", resumen)):
            df.to_csv(RUTA / f"{nombre}.csv", index=False)
        print(por_dimension.to_string(index=False))
        print(por_escenario.to_string(index=False))
        print(resumen.to_string(index=False))
        return
    raise SystemExit(f"Acción desconocida: {accion!r}")


if __name__ == "__main__":
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    main(sys.argv[1:])
