"""
cli.py — Herramientas del agente para Claude Code (Fase 18, opción B, DEC-043)
=============================================================================

Expone las MISMAS 9 herramientas de ``herramientas.py`` (mismos contratos,
validación y reglas) como un comando de consola, para que el agente
investigador de Claude Code (skill ``/investigador``) las use. Cada llamada
queda en la bitácora de su sesión.

    python -m src.agente.cli listar
    python -m src.agente.cli leer_decision '{"id": "DEC-022"}' --sesion demo
    python -m src.agente.cli fin --sesion demo --texto "respuesta final"
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.agente import herramientas  # noqa: E402
from src.agente.agente import RUTA_BITACORA  # noqa: E402


def ruta_sesion(sesion):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", sesion):
        raise SystemExit("La sesión solo admite letras, números, '_' y '-'.")
    RUTA_BITACORA.mkdir(parents=True, exist_ok=True)
    return RUTA_BITACORA / f"claude_code_{sesion}.jsonl"


def registrar(sesion, evento, **datos):
    fila = {"momento": datetime.now().isoformat(timespec="seconds"), "evento": evento,
            "agente": "claude_code", **datos}
    with ruta_sesion(sesion).open("a", encoding="utf-8") as f:
        f.write(json.dumps(fila, ensure_ascii=False, default=str) + "\n")


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Herramientas del agente investigador.")
    p.add_argument("herramienta", help="Nombre de la herramienta, 'listar' o 'fin'.")
    p.add_argument("entrada", nargs="?", default="{}", help="Entrada JSON de la herramienta.")
    p.add_argument("--sesion", default="manual", help="Identificador de la sesión (bitácora).")
    p.add_argument("--texto", default="", help="Respuesta final (solo con 'fin').")
    a = p.parse_args(argv)

    if a.herramienta == "listar":
        for d in herramientas.DEFINICIONES:
            props = ", ".join(f"{k}: {v.get('enum', v['type'])}" for k, v in d["input_schema"]["properties"].items())
            print(f"- {d['name']}({props})\n    {d['description']}")
        return 0
    if a.herramienta == "fin":
        registrar(a.sesion, "fin", texto_final=a.texto)
        print(f"Sesión registrada en {ruta_sesion(a.sesion)}")
        return 0
    try:
        entrada = json.loads(a.entrada)
    except json.JSONDecodeError as exc:
        print(f"Error: la entrada no es JSON válido ({exc}).")
        return 2
    inicio = time.time()
    texto, es_error = herramientas.ejecutar(a.herramienta, entrada)
    registrar(a.sesion, "herramienta", herramienta=a.herramienta, entrada=entrada,
              es_error=es_error, segundos=round(time.time() - inicio, 2), resultado=texto[:2000])
    print(texto)
    return 1 if es_error else 0


if __name__ == "__main__":
    sys.exit(main())
