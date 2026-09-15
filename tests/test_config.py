"""Pruebas de configuración: tickers y parámetros globales."""

from config.settings import TICKERS, FECHA_INICIO, FRECUENCIA


def test_tickers_configurados_correctamente():
    assert isinstance(TICKERS, dict)
    assert len(TICKERS) == 9


def test_los_tickers_son_cadenas_unicas():
    valores = list(TICKERS.values())
    assert all(isinstance(t, str) and t for t in valores)
    assert len(set(valores)) == len(valores)


def test_los_nombres_de_empresa_son_cadenas():
    claves = list(TICKERS.keys())
    assert all(isinstance(k, str) and k for k in claves)


def test_fecha_inicio_y_frecuencia():
    assert FECHA_INICIO == "2020-01-01"
    assert FRECUENCIA == "1d"