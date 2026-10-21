"""Pruebas de la prueba prospectiva (DEC-048) con datos simulados: no descargan nada."""

import numpy as np
import pandas as pd
import pytest

from config.settings import ARCHIVO_IBR, COLUMNA_IBR, TICKERS, TICKERS_EXTERNOS
from src import prospectiva as pr
from src.data import prospectiva as dp


def _falsa_descarga(tickers, inicio, fin, intervalo):
    fechas = pd.bdate_range(inicio, pd.Timestamp(fin) - pd.Timedelta(days=1))
    rng = np.random.default_rng(len(tickers))
    out = {}
    for i, (n, t) in enumerate(tickers.items()):
        precio = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, len(fechas)))) * (i + 1)
        df = pd.DataFrame({"Open": precio, "High": precio, "Low": precio, "Close": precio,
                           "Adj Close": precio, "Volume": 1000.0, "Dividends": 0.0,
                           "Stock Splits": 0.0}, index=pd.DatetimeIndex(fechas, name="Date"))
        out[n] = {"empresa": n, "ticker": t, "estado": "ok", "dataframe": df,
                  "advertencias": [], "error": None}
    return out


@pytest.fixture
def carpeta_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(dp, "RUTA_CRUDOS_PROSPECTIVA", tmp_path)
    return tmp_path


def _ibr(destino, desde="2026-09-01", hasta="2026-12-31"):
    fechas = pd.date_range(desde, hasta, freq="D")
    pd.DataFrame({"Fecha": fechas.strftime("%Y/%m/%d"), COLUMNA_IBR: 9.25}).to_csv(
        destino / ARCHIVO_IBR, index=False, encoding="utf-8-sig")


def test_descarga_una_vez_con_huellas(carpeta_tmp):
    destino = dp.descargar("2026-12-01", descargar_varios=_falsa_descarga)
    assert destino == carpeta_tmp / "hasta_2026-12-01"
    meta = dp.verificar_huellas(destino)
    assert len(meta["huellas"]) == len(TICKERS) + len(TICKERS_EXTERNOS)
    with pytest.raises(FileExistsError):
        dp.descargar("2026-12-01", descargar_varios=_falsa_descarga)
    with pytest.raises(ValueError):
        dp.carpeta("2026-09-10")


def test_descarga_incompleta_no_guarda_nada(carpeta_tmp):
    def con_falla(tickers, *a):
        r = _falsa_descarga(tickers, *a)
        r[next(iter(r))]["estado"] = "vacio"
        return r
    with pytest.raises(RuntimeError):
        dp.descargar("2026-12-01", descargar_varios=con_falla)
    assert not (carpeta_tmp / "hasta_2026-12-01").exists()


def test_cargar_bloque_empieza_despues_de_la_muestra_y_detecta_cambios(carpeta_tmp):
    destino = dp.descargar("2026-12-01", descargar_varios=_falsa_descarga)
    with pytest.raises(FileNotFoundError):
        dp.cargar_bloque(destino)                 # falta el IBR
    _ibr(destino)
    b = dp.cargar_bloque(destino)
    assert set(b) == set(pr.BASES)
    assert b["rendimientos_log"].index.min() == pd.Timestamp("2026-09-15")
    assert not b["rendimientos_log"].isna().any().any()   # el 2026-09-14 solo sirvió de base
    assert list(b["rendimientos_log"].columns) == list(TICKERS)
    archivo = next((destino / "acciones").glob("*.csv"))
    archivo.write_text(archivo.read_text() + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="cambiaron"):
        dp.cargar_bloque(destino)


def test_recortar_usa_los_primeros_dias_sin_importar_cuanto_se_descargo():
    idx = pd.bdate_range("2026-09-15", periods=200)
    bloque = {b: pd.DataFrame({"a": np.arange(200.0)}, index=idx) for b in pr.BASES}
    r = pr.recortar(bloque, 126)
    assert len(r["rendimientos_log"]) == 126 and r["tasas"].index.max() == idx[125]
    with pytest.raises(ValueError, match="se necesitan"):
        pr.recortar({b: df.iloc[:50] for b, df in bloque.items()}, 126)


def test_armar_bloques_rechaza_solapamiento_y_columnas_distintas():
    h_idx = pd.bdate_range("2026-01-01", periods=10)
    e_idx = pd.bdate_range("2026-02-01", periods=10)
    hist = {b: pd.DataFrame({"a": 1.0}, index=h_idx) for b in pr.BASES}
    ev = {b: pd.DataFrame({"a": 1.0}, index=e_idx) for b in pr.BASES}
    assert pr.armar_bloques(hist, ev)["volumen"][1].index.equals(e_idx)
    malo = dict(ev, volumen=pd.DataFrame({"b": 1.0}, index=e_idx))
    with pytest.raises(ValueError, match="columnas"):
        pr.armar_bloques(hist, malo)
    with pytest.raises(ValueError, match="leakage"):
        pr.armar_bloques(hist, {b: pd.DataFrame({"a": 1.0}, index=h_idx) for b in pr.BASES})
