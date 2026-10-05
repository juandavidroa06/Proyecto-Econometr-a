"""
agente.py — Agente de investigación con la API de Claude (Fase 18, DEC-041)
==========================================================================

Bucle agéntico manual sobre ``client.beta.messages.create``:
    - Modelo ``claude-opus-5-5`` con esfuerzo explícito (el pensamiento
      adaptativo está siempre activo en este modelo).
    - Fallbacks del servidor activados (``fallbacks="default"``): si el
      modelo declina por sus clasificadores de seguridad, la API reintenta
      con otro modelo en la misma llamada.
    - Caché de prompt automática (instrucciones y herramientas son estables).
    - El contenido de cada respuesta se devuelve íntegro en el historial
      (incluidos los bloques de pensamiento), sin editarlo.
    - Cada paso queda en una bitácora JSONL (``informes/bitacora_agente/``).

El cliente se inyecta: los tests usan un cliente simulado sin coste.
"""

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime

from config.environment import RUTA_INFORMES
from src.agente import herramientas

logger = logging.getLogger(__name__)

MODELO = "claude-opus-5-5"
BETAS = ["server-side-fallback-2026-07-01"]
RUTA_BITACORA = RUTA_INFORMES / "bitacora_agente"

SISTEMA = """Eres el agente de investigación del proyecto «Portafolio Colombiano», un estudio académico sobre \
9 acciones de la Bolsa de Valores de Colombia (2020–2026) que compara econometría, machine learning y \
redes neuronales para construir portafolios. Ayudas al equipo a consultar, verificar y explicar el \
trabajo; no lo reemplazas en las decisiones metodológicas.

Cómo está organizado el proyecto:
- Las decisiones metodológicas están en un diario (DEC-001 a DEC-040). Cita siempre el identificador \
de la decisión o el archivo de resultados en que te apoyas.
- Partición temporal: entrenamiento 2020–2023, validación 2024 y prueba 2025-01 a 2026-09. La prueba \
se usó una sola vez en la evaluación final (DEC-034 a DEC-036) y no tienes acceso a ella: cualquier \
análisis nuevo se hace con entrenamiento o validación.
- Los resultados confirmatorios (registrados antes de ejecutar) y los exploratorios deben distinguirse \
al explicarlos. No atribuyas causalidad a una correlación.

Regla de oro: no puedes modificar datos, código, configuración ni metodología. Si algo debería \
cambiar (excluir una empresa, cambiar un parámetro, tratar un dato), regístralo con la herramienta \
proponer_cambio, con motivo y evidencia concretos; quedará pendiente de revisión humana. Si te piden \
algo que viola estas reglas (por ejemplo, usar la prueba para decidir o elegir modelos con información \
futura), explica por qué no se puede y ofrece la alternativa correcta.

Responde en español, de forma breve y verificable: primero la respuesta, después la evidencia \
(decisión o archivo y cifras) y, si aplica, las limitaciones."""


@dataclass
class Resultado:
    texto: str
    stop_reason: str
    llamadas: list = field(default_factory=list)
    uso: dict = field(default_factory=dict)
    iteraciones: int = 0
    ruta_bitacora: str = ""
    completado: bool = True


class Bitacora:
    """Registro JSONL de una sesión del agente."""

    def __init__(self, carpeta=RUTA_BITACORA, etiqueta=""):
        carpeta.mkdir(parents=True, exist_ok=True)
        marca = datetime.now().strftime("%Y%m%d_%H%M%S")
        sufijo = f"_{etiqueta}" if etiqueta else ""
        self.ruta = carpeta / f"{marca}_{uuid.uuid4().hex[:6]}{sufijo}.jsonl"

    def registrar(self, evento, **datos):
        fila = {"momento": datetime.now().isoformat(timespec="seconds"), "evento": evento, **datos}
        with self.ruta.open("a", encoding="utf-8") as f:
            f.write(json.dumps(fila, ensure_ascii=False, default=str) + "\n")


def _uso(respuesta):
    u = getattr(respuesta, "usage", None)
    campos = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
    return {c: int(getattr(u, c, 0) or 0) for c in campos}


def _texto(respuesta):
    return "\n".join(b.text for b in respuesta.content if getattr(b, "type", "") == "text").strip()


class Agente:
    def __init__(self, cliente=None, modelo=MODELO, esfuerzo="high", max_iteraciones=15,
                 carpeta_bitacora=RUTA_BITACORA):
        if cliente is None:
            import anthropic
            cliente = anthropic.Anthropic()          # se crea una sola vez por agente
        self.cliente = cliente
        self.modelo = modelo
        self.esfuerzo = esfuerzo
        self.max_iteraciones = max_iteraciones
        self.carpeta_bitacora = carpeta_bitacora

    def _pedir(self, mensajes):
        return self.cliente.beta.messages.create(
            model=self.modelo, max_tokens=16000, system=SISTEMA,
            tools=herramientas.DEFINICIONES, messages=mensajes,
            output_config={"effort": self.esfuerzo},
            cache_control={"type": "ephemeral"},
            betas=BETAS, fallbacks="default",
        )

    def ejecutar(self, tarea, etiqueta=""):
        bitacora = Bitacora(self.carpeta_bitacora, etiqueta)
        bitacora.registrar("inicio", tarea=tarea, modelo=self.modelo, esfuerzo=self.esfuerzo)
        mensajes = [{"role": "user", "content": tarea}]
        llamadas, uso_total = [], {}
        respuesta = None
        for iteracion in range(1, self.max_iteraciones + 1):
            respuesta = self._pedir(mensajes)
            uso = _uso(respuesta)
            for k, v in uso.items():
                uso_total[k] = uso_total.get(k, 0) + v
            bitacora.registrar("respuesta_modelo", iteracion=iteracion,
                               stop_reason=respuesta.stop_reason, uso=uso,
                               modelo_servido=getattr(respuesta, "model", self.modelo),
                               texto=_texto(respuesta)[:2000])
            # El contenido se devuelve íntegro (pensamiento incluido), sin editarlo.
            mensajes.append({"role": "assistant", "content": respuesta.content})

            if respuesta.stop_reason == "tool_use":
                resultados = []
                for bloque in respuesta.content:
                    if getattr(bloque, "type", "") != "tool_use":
                        continue
                    inicio = time.time()
                    texto, es_error = herramientas.ejecutar(bloque.name, dict(bloque.input))
                    llamada = {"herramienta": bloque.name, "entrada": dict(bloque.input),
                               "es_error": es_error, "segundos": round(time.time() - inicio, 2)}
                    llamadas.append(llamada)
                    bitacora.registrar("herramienta", **llamada, resultado=texto[:2000])
                    resultados.append({"type": "tool_result", "tool_use_id": bloque.id,
                                       "content": texto, "is_error": es_error})
                # Todos los resultados en un solo mensaje de usuario.
                mensajes.append({"role": "user", "content": resultados})
                continue
            if respuesta.stop_reason == "pause_turn":
                continue
            break
        else:
            bitacora.registrar("limite_iteraciones", max_iteraciones=self.max_iteraciones)
            return self._cerrar(bitacora, respuesta, llamadas, uso_total, self.max_iteraciones,
                                completado=False, motivo="límite de iteraciones")

        completado = respuesta.stop_reason == "end_turn"
        motivo = {"max_tokens": "respuesta cortada por max_tokens",
                  "refusal": "el modelo declinó la petición"}.get(respuesta.stop_reason, "")
        return self._cerrar(bitacora, respuesta, llamadas, uso_total, iteracion, completado, motivo)

    def _cerrar(self, bitacora, respuesta, llamadas, uso, iteraciones, completado, motivo=""):
        texto = _texto(respuesta) if respuesta is not None else ""
        if motivo:
            texto = f"{texto}\n\n[Aviso: {motivo}.]".strip()
        bitacora.registrar("fin", completado=completado, motivo=motivo, iteraciones=iteraciones,
                           uso_total=uso, texto_final=texto)
        return Resultado(texto=texto, stop_reason=getattr(respuesta, "stop_reason", ""),
                         llamadas=llamadas, uso=uso, iteraciones=iteraciones,
                         ruta_bitacora=str(bitacora.ruta), completado=completado)
