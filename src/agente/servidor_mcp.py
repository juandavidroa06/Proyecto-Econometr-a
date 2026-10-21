"""
servidor_mcp.py — Herramientas del agente como servidor MCP (Fase 21, DEC-046, C3)
==================================================================================

Expone las MISMAS herramientas de ``herramientas.py`` (mismos contratos,
validación y reglas) como herramientas nativas de Claude Code mediante el
Model Context Protocol (transporte stdio). Se registra en ``.mcp.json`` en la
raíz del proyecto; la línea de comandos (``src.agente.cli``) se mantiene.

Cada llamada queda en la bitácora ``informes/bitacora_agente/mcp_<inicio>.jsonl``.
No hay herramienta para abrir el bloque de prueba, descargar datos, escribir
en ``datos/``, editar código ni usar git (regla de oro, DEC-041).

Ejecutar (normalmente lo hace Claude Code):  python -m src.agente.servidor_mcp
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from src.agente import herramientas as h  # noqa: E402
from src.agente.agente import RUTA_BITACORA  # noqa: E402

INSTRUCCIONES = (
    "Herramientas del agente investigador del proyecto Portafolio Colombiano. Solo leen el "
    "diario y los resultados, ejecutan análisis con entrenamiento o validación, verifican la "
    "reproducibilidad o registran PROPUESTAS de cambio para revisión humana. No pueden abrir el "
    "bloque de prueba, descargar datos ni modificar datos, código o metodología. Cita siempre la "
    "decisión (DEC-xxx) o el archivo de resultados en que te apoyas y, al terminar, registra tu "
    "respuesta con registrar_respuesta_final.")

SESION = f"mcp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
servidor = MCPServer(name="investigador", instructions=INSTRUCCIONES)
SOLO_LECTURA = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)


def _registrar(evento, **datos):
    RUTA_BITACORA.mkdir(parents=True, exist_ok=True)
    fila = {"momento": datetime.now().isoformat(timespec="seconds"), "evento": evento,
            "agente": "claude_code_mcp", **datos}
    with (RUTA_BITACORA / f"{SESION}.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(fila, ensure_ascii=False, default=str) + "\n")


def _llamar(nombre, entrada):
    """Valida, ejecuta y registra; los errores se devuelven como texto 'Error: ...'."""
    inicio = time.time()
    texto, es_error = h.ejecutar(nombre, entrada)
    _registrar("herramienta", herramienta=nombre, entrada=entrada, es_error=es_error,
               segundos=round(time.time() - inicio, 2), resultado=texto[:2000])
    return texto


def _descripcion(nombre):
    return next(d["description"] for d in h.DEFINICIONES if d["name"] == nombre)


Empresa = Literal[tuple(h.EMPRESAS)]
Fase = Literal[tuple(sorted(h.FASES_REPRODUCIBLES))]


class Filtro(BaseModel):
    columna: str
    valor: str


@servidor.tool(description=_descripcion("listar_decisiones"), annotations=SOLO_LECTURA)
def listar_decisiones() -> str:
    return _llamar("listar_decisiones", {})


@servidor.tool(description=_descripcion("leer_decision"), annotations=SOLO_LECTURA)
def leer_decision(id: str) -> str:
    return _llamar("leer_decision", {"id": id})


@servidor.tool(description=_descripcion("buscar_diario"), annotations=SOLO_LECTURA)
def buscar_diario(texto: str, max_resultados: int = 10) -> str:
    return _llamar("buscar_diario", {"texto": texto, "max_resultados": max_resultados})


@servidor.tool(description=_descripcion("listar_resultados"), annotations=SOLO_LECTURA)
def listar_resultados() -> str:
    return _llamar("listar_resultados", {})


@servidor.tool(description=_descripcion("leer_resultado"), annotations=SOLO_LECTURA)
def leer_resultado(archivo: str, max_filas: int = 20) -> str:
    return _llamar("leer_resultado", {"archivo": archivo, "max_filas": max_filas})


@servidor.tool(description=_descripcion("consultar_resultado"), annotations=SOLO_LECTURA)
def consultar_resultado(archivo: str, filtros: list[Filtro] | None = None,
                        columnas: list[str] | None = None, ordenar_por: str = "",
                        descendente: bool = False, max_filas: int = 20) -> str:
    return _llamar("consultar_resultado", {
        "archivo": archivo, "filtros": [f.model_dump() for f in (filtros or [])],
        "columnas": list(columnas or []), "ordenar_por": ordenar_por,
        "descendente": descendente, "max_filas": max_filas})


@servidor.tool(description=_descripcion("pruebas_estacionariedad"), annotations=SOLO_LECTURA)
def pruebas_estacionariedad(empresa: Empresa, bloque: Literal["train", "validacion"]) -> str:
    return _llamar("pruebas_estacionariedad", {"empresa": empresa, "bloque": bloque})


@servidor.tool(description=_descripcion("seleccionar_arima"), annotations=SOLO_LECTURA)
def seleccionar_arima(empresa: Empresa) -> str:
    return _llamar("seleccionar_arima", {"empresa": empresa})


@servidor.tool(description=_descripcion("verificar_reproducibilidad"),
               annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                                           idempotentHint=True, openWorldHint=False))
def verificar_reproducibilidad(fase: Fase) -> str:
    return _llamar("verificar_reproducibilidad", {"fase": fase})


@servidor.tool(description=_descripcion("ejecutar_tests"), annotations=SOLO_LECTURA)
def ejecutar_tests() -> str:
    return _llamar("ejecutar_tests", {})


@servidor.tool(description=_descripcion("proponer_cambio"),
               annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                                           openWorldHint=False))
def proponer_cambio(titulo: str, accion_propuesta: str, motivo: str, evidencia: str) -> str:
    return _llamar("proponer_cambio", {"titulo": titulo, "accion_propuesta": accion_propuesta,
                                       "motivo": motivo, "evidencia": evidencia})


@servidor.tool(description="Registra en la bitácora la respuesta final que diste al usuario "
                           "(una vez por consulta, al terminar).",
               annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False,
                                           openWorldHint=False))
def registrar_respuesta_final(texto: str) -> str:
    _registrar("fin", texto_final=texto)
    return f"Respuesta registrada en informes/bitacora_agente/{SESION}.jsonl"


if __name__ == "__main__":
    servidor.run("stdio")
