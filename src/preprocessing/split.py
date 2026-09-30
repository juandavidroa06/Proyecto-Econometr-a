"""
split.py — Partición temporal entrenamiento / validación / prueba
==================================================================

Divide un DataFrame indexado por fecha en tres bloques CONSECUTIVOS y sin
solapamiento. Nunca se mezclan observaciones (no hay ``train_test_split``
aleatorio), para evitar data leakage (AGENTS.md, sección 6).

Las fechas de corte se definen en ``config/settings.py`` (DEC-017).
"""

import hashlib
import json
from pathlib import Path

import pandas as pd

NOMBRES_BLOQUES = ("train", "validacion", "test")


def _validar_indice(df):
    if not isinstance(df, (pd.DataFrame, pd.Series)):
        raise TypeError("Se esperaba un DataFrame o Series de pandas.")
    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("El índice debe ser un DatetimeIndex.")
    if df.index.has_duplicates:
        raise ValueError("El índice tiene fechas duplicadas.")
    if not df.index.is_monotonic_increasing:
        raise ValueError("El índice no está ordenado cronológicamente.")


def particion_temporal(df, fin_train, fin_validacion):
    """Devuelve dict con 'train', 'validacion' y 'test'.

    Reglas:
        train      : fecha <= fin_train
        validacion : fin_train < fecha <= fin_validacion
        test       : fecha > fin_validacion

    Lanza ValueError si las fechas de corte no son crecientes o si algún
    bloque queda vacío (no se devuelven particiones silenciosamente vacías).
    """
    _validar_indice(df)
    fin_train = pd.Timestamp(fin_train)
    fin_validacion = pd.Timestamp(fin_validacion)
    if not fin_train < fin_validacion:
        raise ValueError("fin_train debe ser anterior a fin_validacion.")

    train = df.loc[df.index <= fin_train]
    validacion = df.loc[(df.index > fin_train) & (df.index <= fin_validacion)]
    test = df.loc[df.index > fin_validacion]

    for nombre, bloque in (("train", train), ("validacion", validacion),
                           ("test", test)):
        if len(bloque) == 0:
            raise ValueError(f"La partición '{nombre}' quedó vacía.")

    return {"train": train, "validacion": validacion, "test": test}


def resumen_particion(particion):
    """Tabla con inicio, fin y número de observaciones de cada bloque."""
    filas = []
    for nombre, bloque in particion.items():
        filas.append({
            "bloque": nombre,
            "inicio": bloque.index.min(),
            "fin": bloque.index.max(),
            "observaciones": len(bloque),
        })
    return pd.DataFrame(filas)


# =============================================================================
# Fase 5: blindaje de la partición (verificación, guardado y huellas)
# =============================================================================

def verificar_sin_leakage(particion, original=None):
    """Comprueba que la partición respeta el orden temporal.

    Verifica: (1) están los tres bloques; (2) cada bloque es cronológico y sin
    fechas duplicadas; (3) train < validación < test sin solape; (4) si se pasa
    ``original``, que no se perdió ni se duplicó ninguna fecha.
    Lanza ValueError ante cualquier incumplimiento.
    """
    faltan = [n for n in NOMBRES_BLOQUES if n not in particion]
    if faltan:
        raise ValueError(f"Faltan bloques en la partición: {faltan}")
    for nombre in NOMBRES_BLOQUES:
        _validar_indice(particion[nombre])
    train, val, test = (particion[n] for n in NOMBRES_BLOQUES)
    if not train.index.max() < val.index.min():
        raise ValueError("Leakage: train no termina antes de que empiece validación.")
    if not val.index.max() < test.index.min():
        raise ValueError("Leakage: validación no termina antes de que empiece test.")
    if original is not None:
        unidas = train.index.append(val.index).append(test.index)
        if len(unidas) != len(original.index) or not unidas.equals(original.index):
            raise ValueError("La partición no reconstruye exactamente el original.")


def guardar_particiones(particion, carpeta, nombre_base):
    """Guarda cada bloque como ``{nombre_base}_{bloque}.csv`` en ``carpeta``."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    rutas = {}
    for nombre in NOMBRES_BLOQUES:
        ruta = carpeta / f"{nombre_base}_{nombre}.csv"
        particion[nombre].to_csv(ruta, encoding="utf-8")
        rutas[nombre] = ruta
    return rutas


def cargar_particion(carpeta, nombre_base, bloque, confirmar_evaluacion_final=False):
    """Carga un bloque guardado. El bloque 'test' exige confirmación explícita.

    Regla de la Fase 5: la prueba permanece intocable hasta la evaluación
    final. Para leerla hay que pasar ``confirmar_evaluacion_final=True``.
    """
    if bloque not in NOMBRES_BLOQUES:
        raise ValueError(f"Bloque desconocido: {bloque!r}")
    if bloque == "test" and not confirmar_evaluacion_final:
        raise PermissionError(
            "El bloque de prueba es intocable hasta la evaluación final. "
            "Use confirmar_evaluacion_final=True solo en esa etapa."
        )
    ruta = Path(carpeta) / f"{nombre_base}_{bloque}.csv"
    return pd.read_csv(ruta, index_col=0, parse_dates=True,
                       float_precision="round_trip")


def huella(df):
    """SHA-256 del contenido (independiente del sistema operativo)."""
    texto = df.to_csv(lineterminator="\n")
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def guardar_huellas(huellas, ruta):
    """Guarda un dict {nombre: huella} como JSON."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(huellas, indent=2, sort_keys=True),
                    encoding="utf-8")


def verificar_huellas(carpeta, nombre_base, ruta_huellas, bloques=("train", "validacion")):
    """Comprueba que los archivos guardados no fueron alterados.

    Por defecto verifica train y validación (no toca el bloque de prueba).
    Lanza ValueError si alguna huella no coincide.
    """
    esperadas = json.loads(Path(ruta_huellas).read_text(encoding="utf-8"))
    for bloque in bloques:
        df = cargar_particion(carpeta, nombre_base, bloque,
                              confirmar_evaluacion_final=(bloque == "test"))
        clave = f"{nombre_base}_{bloque}"
        if clave not in esperadas:
            raise ValueError(f"No hay huella registrada para {clave}.")
        if huella(df) != esperadas[clave]:
            raise ValueError(f"El archivo {clave} fue modificado desde la partición.")
