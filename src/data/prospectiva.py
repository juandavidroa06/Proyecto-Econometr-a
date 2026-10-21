"""
prospectiva.py — Datos de la prueba prospectiva (Fase 21, plan DEC-048)
=======================================================================

Responsabilidad única: descargar UNA vez y leer los datos posteriores a la
muestra original (que termina el 2026-09-14), con la misma fuente y las
mismas reglas de inmutabilidad (DEC-021):

    - La descarga empieza el 2026-09-14 (un día de solapamiento para calcular
      el primer rendimiento con la MISMA serie ajustada) y termina en la
      fecha ``--fin`` (exclusiva, como en Yahoo).
    - Se guarda en ``datos/crudos_prospectiva/hasta_<fin>/`` (acciones y
      externas) con metadatos y huellas SHA-256; si la carpeta existe, falla
      sin escribir nada.
    - El IBR se descarga a mano del Banco de la República (como en DEC-031) y
      se copia SIN modificar a esa carpeta con el nombre ``ARCHIVO_IBR``.

La descarga la hace el equipo (el hook del proyecto la bloquea para el
asistente):  python -m src.data.prospectiva --descargar --fin 2027-04-01
"""

import argparse
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from config.environment import RAIZ
from config.settings import (
    ARCHIVO_IBR,
    COLUMNA_IBR,
    FECHA_FIN,
    FRECUENCIA,
    PRECIO_RENDIMIENTOS,
    TICKERS,
    TICKERS_EXTERNOS,
)
from src.data.data_manager import cargar_resultados_crudos, guardar_datos_crudos

logger = logging.getLogger(__name__)

RUTA_CRUDOS_PROSPECTIVA = RAIZ / "datos" / "crudos_prospectiva"
INICIO_DESCARGA = "2026-09-14"          # último día de la muestra original (solapamiento)
PRIMER_DIA_PROSPECTIVO = pd.Timestamp(FECHA_FIN)   # 2026-09-15: nada anterior se evalúa


def carpeta(fin):
    fin = pd.Timestamp(fin)
    if fin <= PRIMER_DIA_PROSPECTIVO:
        raise ValueError(f"La fecha fin debe ser posterior a {PRIMER_DIA_PROSPECTIVO.date()}.")
    return RUTA_CRUDOS_PROSPECTIVA / f"hasta_{fin.date()}"


def _sha256(ruta):
    return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()


def descargar(fin, descargar_varios=None):
    """Descarga acciones y externas a ``hasta_<fin>/``. Falla si la carpeta ya existe
    o si alguna serie no se pudo descargar (no guarda un conjunto incompleto)."""
    if descargar_varios is None:
        from src.data.yahoo_downloader import descargar_varios
    destino = carpeta(fin)
    if destino.exists():
        raise FileExistsError(f"{destino} ya existe: los crudos son inmutables (DEC-021).")
    fin_txt = str(pd.Timestamp(fin).date())
    acciones = descargar_varios(TICKERS, INICIO_DESCARGA, fin_txt, FRECUENCIA)
    externas = descargar_varios(TICKERS_EXTERNOS, INICIO_DESCARGA, fin_txt, FRECUENCIA)
    fallidos = {n: r["estado"] for r_ in (acciones, externas) for n, r in r_.items() if r["estado"] != "ok"}
    if fallidos:
        raise RuntimeError(f"Descarga incompleta: {fallidos}. No se guarda nada.")
    guardados = guardar_datos_crudos(acciones, destino / "acciones")
    guardados += guardar_datos_crudos(externas, destino / "externas")
    import yfinance
    meta = {"descargado": datetime.now().isoformat(timespec="seconds"), "fuente": "yahoo_finance",
            "yfinance": yfinance.__version__, "inicio": INICIO_DESCARGA, "fin_exclusivo": fin_txt,
            "nota": "El IBR se agrega a mano (Banco de la República) con el nombre "
                    f"{ARCHIVO_IBR!r}; ver DEC-048.",
            "huellas": {str(Path(g).relative_to(destino)).replace("\\", "/"): _sha256(g) for g in guardados}}
    (destino / "metadatos.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Datos prospectivos guardados en %s (%d archivos).", destino, len(guardados))
    return destino


def verificar_huellas(destino):
    """Comprueba que los crudos no cambiaron desde la descarga."""
    meta = json.loads((Path(destino) / "metadatos.json").read_text(encoding="utf-8"))
    distintas = [a for a, h in meta["huellas"].items() if _sha256(Path(destino) / a) != h]
    if distintas:
        raise ValueError(f"Los crudos prospectivos cambiaron desde la descarga: {distintas}")
    return meta


def _ibr(ruta):
    """IBR overnight nominal (%) del archivo del Banco de la República, desde el
    primer día prospectivo (mismo formato que ``externos.cargar_ibr``)."""
    if not ruta.exists():
        raise FileNotFoundError(f"Falta {ruta}: descargar el IBR del Banco de la República y "
                                f"copiarlo sin modificar con el nombre {ARCHIVO_IBR!r}.")
    crudo = pd.read_csv(ruta, encoding="utf-8-sig")
    if COLUMNA_IBR not in crudo.columns:
        raise ValueError(f"No se encontró la columna {COLUMNA_IBR!r} en {ruta.name}.")
    fechas = pd.to_datetime(crudo.iloc[:, 0], format="%Y/%m/%d", errors="raise")
    serie = pd.Series(crudo[COLUMNA_IBR].to_numpy(float), index=fechas, name="IBR_overnight_nominal")
    if serie.index.has_duplicates or not serie.index.is_monotonic_increasing:
        raise ValueError("El IBR tiene fechas duplicadas o desordenadas.")
    serie = serie[serie.index >= PRIMER_DIA_PROSPECTIVO]
    if serie.empty or serie.isna().any() or not serie.between(0, 50).all():
        raise ValueError("IBR prospectivo vacío, con faltantes o fuera de [0, 50] %.")
    out = serie.to_frame()
    out.index.name = "Date"
    return out


def cargar_bloque(destino):
    """{base: DataFrame} del bloque prospectivo (desde el 2026-09-15), con las
    mismas bases que la partición congelada: rendimientos_log, volumen,
    externos y tasas. No imputa ni rellena faltantes."""
    destino = Path(destino)
    verificar_huellas(destino)
    acc = cargar_resultados_crudos(TICKERS, destino / "acciones")
    ext = cargar_resultados_crudos(TICKERS_EXTERNOS, destino / "externas")
    precios = pd.DataFrame({n: r["dataframe"][PRECIO_RENDIMIENTOS] for n, r in acc.items()}).sort_index()
    if (precios <= 0).any().any():
        raise ValueError("Hay precios no positivos en los datos prospectivos.")
    rend = np.log(precios / precios.shift(1))
    volumen = pd.DataFrame({n: r["dataframe"]["Volume"] for n, r in acc.items()}).sort_index()
    externos = pd.DataFrame({n: r["dataframe"][PRECIO_RENDIMIENTOS] for n, r in ext.items()}).sort_index()
    nuevo = lambda df: df[df.index >= PRIMER_DIA_PROSPECTIVO]
    bloque = {"rendimientos_log": nuevo(rend), "volumen": nuevo(volumen),
              "externos": nuevo(externos), "tasas": _ibr(destino / ARCHIVO_IBR)}
    for nombre, df in bloque.items():
        df.index.name = "Date"
        if df.empty:
            raise ValueError(f"El bloque prospectivo no tiene datos de {nombre}.")
    return bloque


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="Datos de la prueba prospectiva (DEC-048).")
    p.add_argument("--descargar", action="store_true", help="Descarga una sola vez (carpeta nueva).")
    p.add_argument("--fin", required=True, help="Fecha fin exclusiva, AAAA-MM-DD.")
    a = p.parse_args()
    if not a.descargar:
        p.error("Use --descargar para confirmar la descarga.")
    print(descargar(a.fin))
