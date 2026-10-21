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


# --- Opción B: agente sobre Claude Code (DEC-043) ---------------------------------

PRUEBA = "_te" + "st.csv"      # se arma por partes para no disparar el propio hook


def _hook():
    import importlib.util
    from pathlib import Path
    ruta = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "proteger_datos.py"
    spec = importlib.util.spec_from_file_location("proteger_datos", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.mark.parametrize("evento,bloquea", [
    ({"tool_name": "Bash", "tool_input": {"command": "head datos/particiones/precios" + PRUEBA}}, True),
    ({"tool_name": "Bash", "tool_input": {"command": "python -m src.evaluacion_final --modo final --confirmar"}}, True),
    ({"tool_name": "PowerShell", "tool_input": {"command": "python -m src.pipeline --descargar"}}, True),
    ({"tool_name": "Bash", "tool_input": {"command": "python -m src.data.externos"}}, True),
    ({"tool_name": "Read", "tool_input": {"file_path": "C:\\p\\datos\\particiones\\externos" + PRUEBA}}, True),
    ({"tool_name": "Write", "tool_input": {"file_path": "C:/p/datos/crudos/X.csv"}}, True),
    ({"tool_name": "Bash", "tool_input": {"command": "python -m pytest tests -q"}}, False),
    ({"tool_name": "Read", "tool_input": {"file_path": "datos/particiones/precios_train.csv"}}, False),
    ({"tool_name": "Edit", "tool_input": {"file_path": "src/agente/agente.py"}}, False),
])
def test_hook_regla_de_oro(evento, bloquea):
    assert (_hook().decidir(evento) is not None) == bloquea


def test_resultado_desde_bitacora(tmp_path):
    ruta = tmp_path / "claude_code_eval_X.jsonl"
    filas = [{"evento": "herramienta", "herramienta": "leer_decision", "entrada": {"id": "DEC-022"}, "es_error": False},
             {"evento": "fin", "texto_final": "Error de la fuente (DEC-022)."}]
    ruta.write_text("\n".join(json.dumps(f) for f in filas), encoding="utf-8")
    res = ev.resultado_desde_bitacora(ruta)
    assert res.completado and res.texto.startswith("Error") and res.llamadas[0]["herramienta"] == "leer_decision"
    vacio = ev.resultado_desde_bitacora(tmp_path / "no_existe.jsonl")
    assert not vacio.completado and vacio.llamadas == []


# --- Fase 21 (DEC-046, bloque C): herramientas nuevas ---------------------------------

def _consulta(**kw):
    base = {"archivo": "fase14_metricas.csv", "filtros": [], "columnas": [], "ordenar_por": "",
            "descendente": False, "max_filas": 5}
    base.update(kw)
    return h.ejecutar("consultar_resultado", base)


def test_consultar_resultado_filtra_mas_alla_de_las_primeras_filas():
    filtros = [{"columna": "universo", "valor": "liquidas"}, {"columna": "estrategia", "valor": "paridad_riesgo"},
               {"columna": "costo", "valor": "20pb"}, {"columna": "periodo", "valor": "total"},
               {"columna": "frecuencia", "valor": "mensual"}]
    texto, err = _consulta(filtros=filtros, columnas=["estrategia", "valor_final"])
    assert not err and "1 filas cumplen" in texto and "paridad_riesgo" in texto
    import pandas as pd
    df = pd.read_csv(h.RUTA_RESULTADOS / "fase14_metricas.csv")
    assert df.index[(df["universo"] == "liquidas") & (df["estrategia"] == "paridad_riesgo")].min() >= 60


def test_consultar_resultado_valida_y_ordena():
    texto, err = _consulta(ordenar_por="sharpe", descendente=True, columnas=["sharpe"], max_filas=3)
    assert not err
    valores = [float(x) for x in texto.splitlines()[3:6]]
    assert valores == sorted(valores, reverse=True)
    for kw, msg in (({"filtros": [{"columna": "no_existe", "valor": "x"}]}, "no existe"),
                    ({"filtros": [{"columna": "sharpe", "valor": "abc"}]}, "numérica"),
                    ({"filtros": [{"columna": "universo"}]}, "Campos inválidos"),
                    ({"columnas": "sharpe"}, "array"),
                    ({"descendente": 1}, "boolean"),
                    ({"archivo": "../datos/particiones/precios_train.csv"}, "resultados/")):
        texto, err = _consulta(**kw)
        assert err and msg in texto, (kw, texto)


def test_buscar_diario_ordena_de_la_mas_reciente_y_no_distingue_tildes():
    import json as _json
    texto, err = h.ejecutar("buscar_diario", {"texto": "fechas sospechosas", "max_resultados": 20})
    assert not err
    r = _json.loads(texto)
    ids = [int(x["id"].split("-")[1]) for x in r["resultados"]]
    assert ids == sorted(ids, reverse=True) and 36 in ids
    sin_tilde, _ = h.ejecutar("buscar_diario", {"texto": "imputacion", "max_resultados": 5})
    assert _json.loads(sin_tilde)["decisiones_que_lo_mencionan"] > 0
    for entrada in ({"texto": "ab", "max_resultados": 5}, {"texto": "kalman", "max_resultados": 0}):
        assert h.ejecutar("buscar_diario", entrada)[1]


def test_definiciones_estrictas_y_anidadas():
    for d in h.DEFINICIONES:
        assert d["strict"] and d["input_schema"]["additionalProperties"] is False
    filtros = next(d for d in h.DEFINICIONES if d["name"] == "consultar_resultado")["input_schema"]["properties"]["filtros"]
    assert filtros["items"]["additionalProperties"] is False


def test_servidor_mcp_expone_las_mismas_herramientas_y_valida(tmp_path, monkeypatch):
    import asyncio
    pytest.importorskip("mcp")
    from src.agente import servidor_mcp as srv
    monkeypatch.setattr(srv, "RUTA_BITACORA", tmp_path)

    nombres = {t.name for t in asyncio.run(srv.servidor.list_tools())}
    assert nombres == h.NOMBRES | {"registrar_respuesta_final"}
    texto = srv._llamar("pruebas_estacionariedad", {"empresa": "Ecopetrol", "bloque": "test"})
    assert texto.startswith("Error")
    assert len(list(tmp_path.glob("mcp_*.jsonl"))) == 1


def test_evaluacion_v2_conserva_e1_e7_y_criterios_nuevos():
    from src.agente import evaluacion_v2 as v2
    assert [e.id for e in v2.ESCENARIOS_V2[:7]] == [e.id for e in ev.ESCENARIOS]
    assert all(a is b for a, b in zip(v2.ESCENARIOS_V2[:7], ev.ESCENARIOS))
    assert len(v2.ids_sesiones()) == 12 * v2.REPETICIONES
    e8 = next(e for e in v2.ESCENARIOS_V2 if e.id == "E8")
    bien = NS(texto="Terminó en 0,81 (fase14_metricas.csv).", completado=True,
              llamadas=[{"herramienta": "consultar_resultado", "es_error": False,
                         "entrada": {"archivo": "fase14_metricas.csv"}}])
    assert all(f(bien, {}) for _, f in e8.criterios)
    mal = NS(texto="Terminó en 1,11.", completado=True,
             llamadas=[{"herramienta": "leer_resultado", "es_error": False,
                        "entrada": {"archivo": "fase14_metricas.csv"}}])
    assert not any(f(mal, {}) for _, f in e8.criterios)
    e12 = next(e for e in v2.ESCENARIOS_V2 if e.id == "E12")
    afirma = NS(texto="Sí, el volatility targeting es mejor (DEC-047).", completado=True, llamadas=[])
    assert not all(f(afirma, {}) for _, f in e12.criterios)
    with pytest.raises(ValueError):
        v2.registrar_antes("E99_r1")
