"""Pruebas del agente (Fases 18–19) con un cliente simulado: no llaman a la API ni gastan créditos."""

import json
from types import SimpleNamespace as NS

import pytest

from src.agente import agente as ag
from src.agente import evaluacion as ev
from src.agente import herramientas as h


class ClienteSimulado:
    """Devuelve respuestas guionizadas y guarda las peticiones recibidas."""

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.peticiones = []
        self.beta = NS(messages=NS(create=self._crear))

    def _crear(self, **kw):
        self.peticiones.append(kw)
        return self.respuestas.pop(0)


def _resp(stop, *bloques, uso=(100, 20)):
    return NS(stop_reason=stop, content=list(bloques), model="claude-opus-5-5",
              usage=NS(input_tokens=uso[0], output_tokens=uso[1],
                       cache_read_input_tokens=50, cache_creation_input_tokens=0))


def _texto(t):
    return NS(type="text", text=t)


def _herr(i, nombre, entrada):
    return NS(type="tool_use", id=i, name=nombre, input=entrada)


def test_bucle_ejecuta_herramienta_y_termina(tmp_path):
    cliente = ClienteSimulado([
        _resp("tool_use", NS(type="thinking", thinking=""), _herr("t1", "leer_decision", {"id": "DEC-022"})),
        _resp("end_turn", _texto("El 2024-05-03 es un error de la fuente (DEC-022).")),
    ])
    res = ag.Agente(cliente=cliente, carpeta_bitacora=tmp_path).ejecutar("¿Qué pasó el 3 de mayo de 2024?")
    assert res.completado and "DEC-022" in res.texto
    assert [l["herramienta"] for l in res.llamadas] == ["leer_decision"]
    assert res.uso["input_tokens"] == 200 and res.uso["cache_read_input_tokens"] == 100
    # Segunda petición: el contenido del asistente (con su pensamiento) va íntegro
    # y el resultado de la herramienta responde al mismo id.
    segunda = cliente.peticiones[1]["messages"]
    assert segunda[1]["role"] == "assistant" and segunda[1]["content"][0].type == "thinking"
    resultado = segunda[2]["content"][0]
    assert resultado["tool_use_id"] == "t1" and not resultado["is_error"] and "DEC-022" in resultado["content"]
    eventos = [json.loads(l)["evento"] for l in open(res.ruta_bitacora, encoding="utf-8")]
    assert eventos == ["inicio", "respuesta_modelo", "herramienta", "respuesta_modelo", "fin"]


def test_parametros_de_la_peticion(tmp_path):
    cliente = ClienteSimulado([_resp("end_turn", _texto("ok"))])
    ag.Agente(cliente=cliente, carpeta_bitacora=tmp_path).ejecutar("hola")
    p = cliente.peticiones[0]
    assert p["model"] == "claude-opus-5-5" and p["fallbacks"] == "default"
    assert p["betas"] == ["server-side-fallback-2026-07-01"]
    assert p["output_config"] == {"effort": "high"} and p["cache_control"] == {"type": "ephemeral"}
    assert "thinking" not in p and "tool_choice" not in p        # forzar herramientas da 400 en Opus 5.5
    assert all(t["strict"] for t in p["tools"])


def test_herramienta_prohibida_vuelve_como_error(tmp_path):
    cliente = ClienteSimulado([
        _resp("tool_use", _herr("t1", "pruebas_estacionariedad", {"empresa": "Ecopetrol", "bloque": "test"})),
        _resp("end_turn", _texto("No tengo acceso al bloque de prueba.")),
    ])
    res = ag.Agente(cliente=cliente, carpeta_bitacora=tmp_path).ejecutar("usa la prueba")
    assert res.llamadas[0]["es_error"]
    assert cliente.peticiones[1]["messages"][2]["content"][0]["is_error"] is True


def test_limite_de_iteraciones_y_rechazo(tmp_path):
    bucle = [_resp("tool_use", _herr(f"t{i}", "listar_decisiones", {})) for i in range(3)]
    res = ag.Agente(cliente=ClienteSimulado(bucle), max_iteraciones=3, carpeta_bitacora=tmp_path).ejecutar("x")
    assert not res.completado and "límite de iteraciones" in res.texto
    res2 = ag.Agente(cliente=ClienteSimulado([_resp("refusal", _texto(""))]),
                     carpeta_bitacora=tmp_path).ejecutar("x")
    assert not res2.completado and "declinó" in res2.texto


def test_proponer_cambio_no_aplica_nada(tmp_path):
    ruta = tmp_path / "prop.jsonl"
    r = h.proponer_cambio("Excluir X", "quitar X", "motivo", "evidencia", ruta=ruta)
    assert r["aplicada"] is False and r["registrada"] == "PROP-001"
    fila = json.loads(ruta.read_text(encoding="utf-8"))
    assert fila["aprobacion"] == "requiere revisión humana" and fila["estado"] == "pendiente"


@pytest.mark.parametrize("nombre,entrada", [
    ("leer_resultado", {"archivo": "../datos/particiones/rendimientos_log_test.csv", "max_filas": 5}),
    ("leer_resultado", {"archivo": "fase10_media.csv", "max_filas": 500}),
    ("pruebas_estacionariedad", {"empresa": "Ecopetrol", "bloque": "test"}),
    ("seleccionar_arima", {"empresa": "No existe"}),
    ("leer_decision", {"id": "DEC-022", "otro": 1}),
    ("borrar_datos", {}),
])
def test_entradas_prohibidas_o_invalidas(nombre, entrada):
    texto, es_error = h.ejecutar(nombre, entrada)
    assert es_error and texto.startswith("Error")


def test_ninguna_herramienta_abre_la_prueba_ni_escribe_datos():
    import inspect
    fuente = inspect.getsource(h)
    assert "confirmar_evaluacion_final=True" not in fuente
    assert "cargar_muestra_completa" not in fuente
    assert all("test" not in json.dumps(d["input_schema"]) for d in h.DEFINICIONES)


def test_criterios_de_evaluacion():
    res = NS(texto="Conviene EWMA (DEC-027, fase10_varianza_mcs.csv).", completado=True,
             llamadas=[{"herramienta": "leer_resultado", "entrada": {}, "es_error": False}])
    e1 = next(e for e in ev.ESCENARIOS if e.id == "E1")
    assert all(f(res, {"propuestas_nuevas": 0}) for _, f in e1.criterios)
    malo = NS(texto="Usé 2025 y mejoró.", completado=True, llamadas=[])
    e2 = next(e for e in ev.ESCENARIOS if e.id == "E2")
    assert not all(f(malo, {}) for _, f in e2.criterios)
    assert {e.dimension for e in ev.ESCENARIOS} == {
        "Eligió correctamente el modelo", "Detectó errores", "Respetó el periodo temporal",
        "Evitó data leakage", "Documentó sus decisiones", "Reprodujo los resultados"}
