"""
Hook PreToolUse del proyecto (Fase 18, DEC-043): protege la regla de oro.

Bloquea, para cualquier sesión de Claude Code en este repositorio (el
agente investigador y cualquier otra):
    - comandos de terminal que abren el bloque de prueba o descargan datos;
    - lectura directa de las particiones de prueba;
    - edición o escritura de archivos dentro de datos/.

Recibe el JSON del evento por stdin y, si hay que bloquear, responde con
``permissionDecision: deny`` y el motivo (que el modelo ve). Sin
dependencias externas.
"""

import json
import re
import sys

PATRONES_COMANDO = [
    (r"_test\.csv", "abre una partición del bloque de prueba"),
    (r"confirmar_evaluacion_final\s*=\s*True", "abre el bloque de prueba"),
    (r"evaluacion_final\b.*--modo\s+final", "ejecuta la evaluación final (solo una vez, ya hecha)"),
    (r"--descargar\b", "descarga datos nuevos (los crudos son inmutables)"),
    (r"src[./\\]data[./\\]externos", "descarga datos externos"),
]


def _normalizar(ruta):
    return (ruta or "").replace("\\", "/").lower()


def decidir(evento):
    herramienta = evento.get("tool_name", "")
    entrada = evento.get("tool_input", {}) or {}
    if herramienta in ("Bash", "PowerShell"):
        comando = entrada.get("command", "")
        for patron, motivo in PATRONES_COMANDO:
            if re.search(patron, comando, flags=re.IGNORECASE):
                return f"Bloqueado por la regla de oro del proyecto: el comando {motivo}."
    ruta = _normalizar(entrada.get("file_path") or entrada.get("path") or entrada.get("notebook_path"))
    if herramienta == "Read" and re.search(r"datos/particiones/[^/]*_test\.csv$", ruta):
        return "Bloqueado: el bloque de prueba no se lee (DEC-034 a DEC-036)."
    if herramienta in ("Edit", "Write", "NotebookEdit") and re.search(r"(^|/)datos/", ruta):
        return ("Bloqueado: los datos no se modifican a mano (AGENTS.md, sección 5). "
                "Si algo debe cambiar, regístrelo como propuesta para revisión humana.")
    return None


def main():
    try:
        evento = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # sin evento válido no hay nada que decidir
    motivo = decidir(evento)
    if motivo:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": motivo}}, ensure_ascii=True))  # ASCII: evita problemas de codificación en Windows
    return 0


if __name__ == "__main__":
    sys.exit(main())
