"""Pruebas de DEC-021: fecha final fija, crudos inmutables y partición congelada."""

import json

import numpy as np
import pandas as pd
import pytest

from config.environment import RUTA_DATOS_CRUDOS, RUTA_DATOS_METADATA
from config.settings import FECHA_FIN, TICKERS
from src.data.data_manager import (
    cargar_resultados_crudos,
    guardar_datos_crudos,
    nombre_archivo_crudo,
)
from src.preprocessing.split import comparar_con_huellas_guardadas, guardar_huellas


def _crudo(valor=100.0):
    fechas = pd.date_range("2024-01-01", periods=5, freq="B", name="Date")
    return pd.DataFrame({"Close": np.full(5, valor), "Adj Close": np.full(5, valor)},
                        index=fechas)


# --- Fecha final fija -------------------------------------------------------

def test_fecha_fin_es_fija():
    assert FECHA_FIN is not None
    pd.Timestamp(FECHA_FIN)  # formato válido


def test_fecha_fin_coincide_con_la_descarga_original():
    meta = json.loads((RUTA_DATOS_METADATA / "metadatos_descarga.json")
                      .read_text(encoding="utf-8"))
    solicitadas = {m["fecha_fin_solicitada"] for m in meta.values()}
    assert solicitadas == {FECHA_FIN}


@pytest.mark.skipif(not RUTA_DATOS_CRUDOS.exists(), reason="Sin datos crudos.")
def test_crudos_terminan_antes_de_fecha_fin():
    # Yahoo trata 'end' como exclusivo.
    for ticker in TICKERS.values():
        df = pd.read_csv(RUTA_DATOS_CRUDOS / nombre_archivo_crudo(ticker),
                         index_col=0, parse_dates=True)
        assert df.index.max() < pd.Timestamp(FECHA_FIN)


# --- Crudos inmutables --------------------------------------------------------

def test_guardar_crudos_no_sobrescribe(tmp_path):
    guardar_datos_crudos({"A": {"ticker": "A.CL", "dataframe": _crudo(100)}}, tmp_path)
    archivo = tmp_path / "A_CL.csv"
    antes = archivo.read_bytes()
    with pytest.raises(FileExistsError):
        guardar_datos_crudos({"A": {"ticker": "A.CL", "dataframe": _crudo(999)}},
                             tmp_path)
    assert archivo.read_bytes() == antes


def test_guardar_crudos_no_escribe_nada_si_alguno_existe(tmp_path):
    guardar_datos_crudos({"A": {"ticker": "A.CL", "dataframe": _crudo()}}, tmp_path)
    nuevos = {"B": {"ticker": "B.CL", "dataframe": _crudo()},
              "A": {"ticker": "A.CL", "dataframe": _crudo(999)}}
    with pytest.raises(FileExistsError):
        guardar_datos_crudos(nuevos, tmp_path)
    assert not (tmp_path / "B_CL.csv").exists()


def test_cargar_resultados_crudos_ida_y_vuelta(tmp_path):
    tickers = {"A": "A.CL", "B": "B.CL"}
    guardar_datos_crudos({n: {"ticker": t, "dataframe": _crudo()}
                          for n, t in tickers.items()}, tmp_path)
    res = cargar_resultados_crudos(tickers, tmp_path)
    assert set(res) == {"A", "B"}
    for nombre, item in res.items():
        assert item["estado"] == "ok" and item["ticker"] == tickers[nombre]
        pd.testing.assert_frame_equal(item["dataframe"], _crudo(), check_freq=False)


def test_cargar_resultados_crudos_falla_si_falta_un_ticker(tmp_path):
    guardar_datos_crudos({"A": {"ticker": "A.CL", "dataframe": _crudo()}}, tmp_path)
    with pytest.raises(FileNotFoundError):
        cargar_resultados_crudos({"A": "A.CL", "B": "B.CL"}, tmp_path)


# --- Partición congelada ------------------------------------------------------

def test_huellas_sin_archivo_previo(tmp_path):
    assert comparar_con_huellas_guardadas({"x": "1"}, tmp_path / "h.json") is False


def test_huellas_iguales(tmp_path):
    ruta = tmp_path / "h.json"
    guardar_huellas({"x": "1", "y": "2"}, ruta)
    assert comparar_con_huellas_guardadas({"x": "1", "y": "2"}, ruta) is True


@pytest.mark.parametrize("nuevas", [{"x": "1", "y": "CAMBIO"}, {"x": "1"},
                                    {"x": "1", "y": "2", "z": "3"}])
def test_huellas_distintas_lanzan_error(tmp_path, nuevas):
    ruta = tmp_path / "h.json"
    guardar_huellas({"x": "1", "y": "2"}, ruta)
    with pytest.raises(ValueError, match="cambió"):
        comparar_con_huellas_guardadas(nuevas, ruta)
