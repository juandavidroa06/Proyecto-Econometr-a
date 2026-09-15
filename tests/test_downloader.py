"""Pruebas del módulo de descarga (sin conexión real: se simula Yahoo)."""

import pandas as pd
import pytest

import src.data.yahoo_downloader as yd


def _df_ejemplo():
    return pd.DataFrame(
        {
            "Open": [10, 20],
            "High": [11, 21],
            "Low": [9, 19],
            "Close": [10.5, 20.5],
            "Adj Close": [10.5, 20.5],
            "Volume": [100, 200],
        },
        index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
    )


def test_descargar_ticker_devuelve_dataframe(monkeypatch):
    monkeypatch.setattr(yd, "descargar_serie", lambda *a, **k: _df_ejemplo())
    df = yd.descargar_ticker("EJEMPLO.CL", "2020-01-01")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty


def test_columnas_esperadas_cuando_yahoo_las_proporciona(monkeypatch):
    monkeypatch.setattr(yd, "descargar_serie", lambda *a, **k: _df_ejemplo())
    df = yd.descargar_ticker("EJEMPLO.CL", "2020-01-01")
    for col in ["Open", "High", "Low", "Close", "Adj Close", "Volume"]:
        assert col in df.columns


def test_descargar_ticker_devuelve_none_si_falla(monkeypatch):
    def _fallar(*a, **k):
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr(yd, "descargar_serie", _fallar)
    df = yd.descargar_ticker("MALO.CL", "2020-01-01")
    assert df is None


def test_descargar_varios_tolerante_a_fallos(monkeypatch):
    def _selectiva(ticker, *a, **k):
        if ticker == "FALLA.CL":
            raise RuntimeError("sin datos")
        return _df_ejemplo()

    monkeypatch.setattr(yd, "descargar_serie", _selectiva)
    resultados = yd.descargar_varios(
        {"A": "OK.CL", "B": "FALLA.CL"}, "2020-01-01"
    )
    assert resultados["A"]["estado"] == "ok"
    assert resultados["B"]["estado"] == "error"
    assert resultados["B"]["dataframe"] is None
    assert resultados["B"]["advertencias"]


def test_descargar_varios_con_datos_vacios(monkeypatch):
    monkeypatch.setattr(yd, "descargar_serie", lambda *a, **k: pd.DataFrame())
    resultados = yd.descargar_varios({"A": "VACIO.CL"}, "2020-01-01")
    assert resultados["A"]["estado"] == "vacio"