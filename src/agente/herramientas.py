"""
herramientas.py — Herramientas del agente de investigación (Fase 18, DEC-041)
=============================================================================

Responsabilidad única: definir QUÉ puede hacer el agente y ejecutarlo con
validación explícita.

Regla de oro (borrador del proyecto): el agente no puede modificar datos ni
cambiar la metodología por su cuenta. Por diseño:
    - No hay herramienta para abrir el bloque de prueba, descargar datos,
      escribir en ``datos/``, editar código o usar git.
    - Los análisis nuevos solo usan entrenamiento o validación.
    - Reejecutar una fase verifica su reproducibilidad y restaura los
      archivos versionados: no deja cambios.
    - Cualquier cambio de datos, configuración o metodología solo puede
      PROPONERSE (``proponer_cambio``) y queda pendiente de revisión humana.

Cada herramienta tiene un contrato JSON explícito (``strict``) y además se
valida la entrada antes de ejecutarla (AGENTS.md, secciones 4 y 10).
"""

import json
import re
import subprocess
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd

from config.environment import RAIZ, RUTA_INFORMES, RUTA_PARTICIONES, RUTA_RESULTADOS
from config.settings import TICKERS

EMPRESAS = sorted(TICKERS)
ARCHIVO_PROPUESTAS = RUTA_INFORMES / "propuestas_agente.jsonl"

# Fases que el agente puede reejecutar para comprobar su reproducibilidad.
# Todas usan solo entrenamiento y validación; se excluyen las que tardan
# muchos minutos (Fases 9 y 16) y las que abren la prueba (Fase 15).
FASES_REPRODUCIBLES = {
    "fase6": ("src.portfolio.fase6", "fase6_*.csv"),
    "fase7": ("src.econometrics.fase7", "fase7_*.csv"),
    "fase10": ("src.comparacion.fase10", "fase10_*.csv"),
    "fase11": ("src.riesgo.fase11", "fase11_*.csv"),
    "fase12": ("src.optimizacion.fase12", "fase12_*.csv"),
    "fase14": ("src.backtesting.fase14", "fase14_*.csv"),
}
LIMITE_TEXTO = 6000


def _esquema(propiedades, requeridos):
    return {"type": "object", "properties": propiedades, "required": requeridos,
            "additionalProperties": False}


DEFINICIONES = [
    {"name": "listar_decisiones",
     "description": "Lista las decisiones metodológicas del diario (id, título y estado). "
                    "Úsala para orientarte antes de leer una decisión concreta.",
     "input_schema": _esquema({}, [])},
    {"name": "leer_decision",
     "description": "Devuelve el texto completo de una decisión del diario, p. ej. DEC-022.",
     "input_schema": _esquema({"id": {"type": "string", "description": "Identificador, p. ej. DEC-022"}},
                              ["id"])},
    {"name": "listar_resultados",
     "description": "Lista los archivos CSV de resultados disponibles en resultados/ (rutas relativas).",
     "input_schema": _esquema({}, [])},
    {"name": "leer_resultado",
     "description": "Lee un CSV de resultados/ y devuelve sus primeras filas como texto. Los "
                    "resultados de resultados/fase15/final son la evaluación confirmatoria ya "
                    "publicada: pueden citarse, no usarse para tomar decisiones nuevas.",
     "input_schema": _esquema({
         "archivo": {"type": "string", "description": "Ruta relativa dentro de resultados/, p. ej. fase10_media.csv"},
         "max_filas": {"type": "integer", "description": "Máximo de filas (1 a 60)"}},
         ["archivo", "max_filas"])},
    {"name": "pruebas_estacionariedad",
     "description": "Calcula ADF, KPSS, Ljung-Box (rendimientos y cuadrados), ARCH-LM y Jarque-Bera "
                    "sobre los rendimientos log de una empresa en entrenamiento o validación.",
     "input_schema": _esquema({
         "empresa": {"type": "string", "enum": EMPRESAS},
         "bloque": {"type": "string", "enum": ["train", "validacion"]}},
         ["empresa", "bloque"])},
    {"name": "seleccionar_arima",
     "description": "Selecciona el orden ARIMA(p,0,q) por BIC para una empresa usando SOLO "
                    "entrenamiento (como en la Fase 7) y devuelve el orden y el diagnóstico de residuos.",
     "input_schema": _esquema({"empresa": {"type": "string", "enum": EMPRESAS}}, ["empresa"])},
    {"name": "verificar_reproducibilidad",
     "description": "Reejecuta una fase, compara sus CSV con la versión publicada en git y restaura "
                    "los archivos (no deja cambios). Devuelve la máxima diferencia por archivo.",
     "input_schema": _esquema({"fase": {"type": "string", "enum": sorted(FASES_REPRODUCIBLES)}}, ["fase"])},
    {"name": "ejecutar_tests",
     "description": "Ejecuta la batería de tests del proyecto (pytest) y devuelve el resumen.",
     "input_schema": _esquema({}, [])},
    {"name": "proponer_cambio",
     "description": "Registra una PROPUESTA de cambio de datos, configuración o metodología. No "
                    "aplica nada: queda pendiente de revisión humana. Es la única forma de sugerir "
                    "cambios.",
     "input_schema": _esquema({
         "titulo": {"type": "string"},
         "accion_propuesta": {"type": "string"},
         "motivo": {"type": "string"},
         "evidencia": {"type": "string", "description": "Archivos, decisiones o cifras que la respaldan"}},
         ["titulo", "accion_propuesta", "motivo", "evidencia"])},
]
for _d in DEFINICIONES:
    _d["strict"] = True
NOMBRES = {d["name"] for d in DEFINICIONES}


class ErrorHerramienta(Exception):
    """Error esperado de una herramienta (entrada inválida o acción no permitida)."""


# --- Validación ----------------------------------------------------------------------

def validar_entrada(nombre, entrada):
    """Valida la entrada contra el esquema (tipos, enums, requeridos, sin extras)."""
    if nombre not in NOMBRES:
        raise ErrorHerramienta(f"Herramienta desconocida: {nombre!r}")
    if not isinstance(entrada, dict):
        raise ErrorHerramienta("La entrada debe ser un objeto JSON.")
    esquema = next(d for d in DEFINICIONES if d["name"] == nombre)["input_schema"]
    extras = set(entrada) - set(esquema["properties"])
    faltan = set(esquema["required"]) - set(entrada)
    if extras or faltan:
        raise ErrorHerramienta(f"Campos inválidos (sobran {sorted(extras)}, faltan {sorted(faltan)}).")
    tipos = {"string": str, "integer": int}
    for campo, regla in esquema["properties"].items():
        valor = entrada[campo]
        if not isinstance(valor, tipos[regla["type"]]) or isinstance(valor, bool):
            raise ErrorHerramienta(f"'{campo}' debe ser de tipo {regla['type']}.")
        if "enum" in regla and valor not in regla["enum"]:
            raise ErrorHerramienta(f"'{campo}' debe ser uno de {regla['enum']}.")


# --- Implementaciones -------------------------------------------------------------------

def _diario():
    return (RUTA_INFORMES / "diario_decisiones.md").read_text(encoding="utf-8")


def listar_decisiones():
    texto = _diario()
    filas = []
    for m in re.finditer(r"^### (DEC-\d+)[^:\n]*:\s*(.+)$", texto, flags=re.M):
        bloque = texto[m.end():texto.find("\n### ", m.end()) if "\n### " in texto[m.end():] else None]
        estado = re.search(r"\*\*Estado:\*\*\s*(.+)", bloque)
        filas.append({"id": m.group(1), "titulo": m.group(2).strip(),
                      "estado": estado.group(1).strip()[:120] if estado else ""})
    return filas


def leer_decision(id):
    ident = id.strip().upper()
    if not re.fullmatch(r"DEC-\d{3}", ident):
        raise ErrorHerramienta("El id debe tener la forma DEC-001.")
    texto = _diario()
    m = re.search(rf"^### {ident}\b.*$", texto, flags=re.M)
    if not m:
        raise ErrorHerramienta(f"No existe {ident} en el diario.")
    fin = texto.find("\n---", m.end())
    return texto[m.start():fin if fin > 0 else None][:LIMITE_TEXTO]


def listar_resultados():
    return sorted(str(p.relative_to(RUTA_RESULTADOS)).replace("\\", "/")
                  for p in RUTA_RESULTADOS.rglob("*.csv"))


def leer_resultado(archivo, max_filas):
    if not 1 <= max_filas <= 60:
        raise ErrorHerramienta("max_filas debe estar entre 1 y 60.")
    ruta = (RUTA_RESULTADOS / archivo).resolve()
    if RUTA_RESULTADOS.resolve() not in ruta.parents or ruta.suffix != ".csv":
        raise ErrorHerramienta("Solo se pueden leer CSV dentro de resultados/.")
    if not ruta.exists():
        raise ErrorHerramienta(f"No existe resultados/{archivo}.")
    df = pd.read_csv(ruta)
    texto = df.head(max_filas).to_string(index=False, max_colwidth=40)
    nota = f"({len(df)} filas en total, se muestran {min(len(df), max_filas)})"
    if "fase15/final" in archivo.replace("\\", "/"):
        nota += " — evaluación confirmatoria ya publicada (DEC-036): citar, no decidir con ella."
    return f"{nota}\n{texto}"[:LIMITE_TEXTO]


def pruebas_estacionariedad(empresa, bloque):
    from src.exploratory_analysis.stat_tests import pruebas_estacionariedad as est
    from src.exploratory_analysis.stat_tests import pruebas_rendimientos
    from src.preprocessing.split import cargar_entrenamiento_validacion

    r = cargar_entrenamiento_validacion(RUTA_PARTICIONES, "rendimientos_log")[bloque][[empresa]]
    a = est(r).iloc[0]
    b = pruebas_rendimientos(r).iloc[0]
    return {"empresa": empresa, "bloque": bloque, "n": int(b["n"]),
            "adf_pvalor": round(float(a["adf_pvalor"]), 4),
            "kpss_pvalor": round(float(a["kpss_pvalor"]), 4),
            "estacionaria_segun_adf_y_kpss": bool(a["adf_rechaza_raiz_unitaria"]
                                                  and not a["kpss_rechaza_estacionariedad"]),
            "jarque_bera_pvalor": round(float(b["jb_pvalor"]), 4),
            "ljung_box_rendimientos_pvalor": round(float(b["lb_r_pvalor"]), 4),
            "ljung_box_cuadrados_pvalor": round(float(b["lb_r2_pvalor"]), 4),
            "arch_lm_pvalor": round(float(b["arch_lm_pvalor"]), 4),
            "nota": "KPSS trunca su p-valor a [0,01; 0,10]."}


def seleccionar_arima(empresa):
    from config.settings import ARIMA_CRITERIO, ARIMA_MAX_P, ARIMA_MAX_Q
    from src.econometrics import arima
    from src.preprocessing.split import cargar_entrenamiento_validacion

    serie = cargar_entrenamiento_validacion(RUTA_PARTICIONES, "rendimientos_log")["train"][empresa].dropna()
    orden, tabla = arima.seleccionar_orden(serie, ARIMA_MAX_P, ARIMA_MAX_Q, ARIMA_CRITERIO)
    res, _ = arima.ajustar_arima(serie, orden)
    diag = arima.diagnostico_residuos(res)
    return {"empresa": empresa, "datos": "solo entrenamiento (2020–2023)", "orden_p_q": list(orden),
            "bic": round(float(res.bic), 2), "modelos_probados": len(tabla),
            "no_convergieron": int((~tabla["convergio"]).sum()),
            "ljung_box_residuos_pvalor": round(diag["lb_resid_pvalor"], 4),
            "ljung_box_residuos2_pvalor": round(diag["lb_resid2_pvalor"], 4)}


def _git(*args):
    return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True, check=True).stdout


def verificar_reproducibilidad(fase):
    modulo, patron = FASES_REPRODUCIBLES[fase]
    archivos = sorted(str(p.relative_to(RAIZ)).replace("\\", "/") for p in RUTA_RESULTADOS.glob(patron))
    if not archivos:
        raise ErrorHerramienta(f"No hay resultados publicados de {fase}.")
    if _git("status", "--porcelain", "--", *archivos).strip():
        raise ErrorHerramienta("Hay cambios sin commitear en esos resultados: no se reejecuta "
                               "para no sobrescribir trabajo del equipo.")
    inicio = time.time()
    proc = subprocess.run([sys.executable, "-m", modulo], cwd=RAIZ, capture_output=True,
                          text=True, timeout=1800, encoding="utf-8", errors="replace")
    try:
        if proc.returncode != 0:
            raise ErrorHerramienta(f"La fase falló (código {proc.returncode}): {proc.stderr[-800:]}")
        import io
        filas = []
        for a in archivos:
            nuevo = pd.read_csv(RAIZ / a)
            publicado = pd.read_csv(io.StringIO(_git("show", f"HEAD:{a}")))
            mismas = nuevo.shape == publicado.shape and list(nuevo.columns) == list(publicado.columns)
            num = nuevo.select_dtypes("number").columns if mismas else []
            dif = float((nuevo[num] - publicado[num]).abs().max().max()) if len(num) else 0.0
            filas.append({"archivo": a, "misma_forma": mismas,
                          "max_dif_absoluta": dif if mismas else None})
        return {"fase": fase, "segundos": round(time.time() - inicio, 1), "archivos": filas}
    finally:
        # Restaura la versión publicada de los resultados (y gráficos) de la fase.
        _git("checkout", "--", *archivos)
        graficos = [str(p.relative_to(RAIZ)) for p in (RUTA_RESULTADOS / "graficos").glob(f"{fase}_*")]
        if graficos:
            _git("checkout", "--", *graficos)


def ejecutar_tests():
    proc = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"],
                          cwd=RAIZ, capture_output=True, text=True, timeout=1800,
                          encoding="utf-8", errors="replace")
    ultimas = [l for l in proc.stdout.strip().splitlines() if l.strip()][-3:]
    return {"codigo_salida": proc.returncode, "resumen": ultimas}


def proponer_cambio(titulo, accion_propuesta, motivo, evidencia, ruta=None):
    ruta = Path(ruta or ARCHIVO_PROPUESTAS)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    previas = ruta.read_text(encoding="utf-8").splitlines() if ruta.exists() else []
    propuesta = {"id": f"PROP-{len(previas) + 1:03d}", "fecha": datetime.now().isoformat(timespec="seconds"),
                 "titulo": titulo, "accion_propuesta": accion_propuesta, "motivo": motivo,
                 "evidencia": evidencia, "aprobacion": "requiere revisión humana",
                 "estado": "pendiente", "origen": "agente"}
    with ruta.open("a", encoding="utf-8") as f:
        f.write(json.dumps(propuesta, ensure_ascii=False) + "\n")
    return {"registrada": propuesta["id"], "estado": "pendiente de revisión humana",
            "aplicada": False}


IMPLEMENTACIONES = {
    "listar_decisiones": listar_decisiones, "leer_decision": leer_decision,
    "listar_resultados": listar_resultados, "leer_resultado": leer_resultado,
    "pruebas_estacionariedad": pruebas_estacionariedad, "seleccionar_arima": seleccionar_arima,
    "verificar_reproducibilidad": verificar_reproducibilidad, "ejecutar_tests": ejecutar_tests,
    "proponer_cambio": proponer_cambio,
}


def ejecutar(nombre, entrada):
    """Valida y ejecuta. Retorna (texto_resultado, es_error).

    Los errores esperados (entrada inválida, acción no permitida) vuelven al
    modelo como ``is_error``; los inesperados también, pero con su tipo, para
    que el fallo sea visible en la bitácora y no se oculte.
    """
    try:
        validar_entrada(nombre, entrada)
        salida = IMPLEMENTACIONES[nombre](**entrada)
        texto = salida if isinstance(salida, str) else json.dumps(salida, ensure_ascii=False, default=str)
        return texto[:LIMITE_TEXTO], False
    except ErrorHerramienta as exc:
        return f"Error: {exc}", True
    except subprocess.TimeoutExpired:
        return "Error: la ejecución superó el tiempo máximo.", True
    except Exception as exc:  # noqa: BLE001 - se informa al modelo y queda en la bitácora
        return f"Error inesperado ({type(exc).__name__}): {exc}", True


def normalizar(texto):
    """Minúsculas sin tildes (para buscar palabras clave en la evaluación)."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sin_tildes.lower()
