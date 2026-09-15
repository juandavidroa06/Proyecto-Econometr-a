"""Pruebas del módulo de validación de calidad de datos."""

import pandas as pd

from src.data.data_validator import validar_dataframe


def _df_con_fechas(fechas):
    return pd.DataFrame(
        {
            "Open": [10, 20, 30, 40],
            "High": [11, 21, 31, 41],
            "Low": [9, 19, 29, 39],
            "Close": [10.5, 20.5, 30.5, 40.5],
            "Adj Close": [10.5, 20.5, 30.5, 40.5],
            "Volume": [100, 200, 300, 400],
        },
        index=pd.to_datetime(fechas),
    )


def test_dataframe_valido_estado_ok():
    df = _df_con_fechas(["2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07"])
    checks = validar_dataframe(df)
    assert checks["estado"] == "ok"
    assert checks["fechas_ordenadas"] is True
    assert checks["fechas_duplicadas"] == 0
    assert checks["precios_invalidos"] == 0
    assert checks["volumen_invalido"] == 0
    assert checks["n_observaciones"] == 4


def test_detecta_fechas_desordenadas():
    df = _df_con_fechas(["2020-01-03", "2020-01-02", "2020-01-06", "2020-01-07"])
    checks = validar_dataframe(df)
    assert checks["fechas_ordenadas"] is False


def test_detecta_precios_invalidos():
    df = _df_con_fechas(["2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07"])
    df.loc[df.index[1], "Close"] = 0.0
    df.loc[df.index[2], "Open"] = -5.0
    checks = validar_dataframe(df)
    assert checks["precios_invalidos"] >= 2


def test_detecta_volumen_negativo():
    df = _df_con_fechas(["2020-01-02", "2020-01-03", "2020-01-06", "2020-01-07"])
    df.loc[df.index[0], "Volume"] = -10
    checks = validar_dataframe(df)
    assert checks["volumen_invalido"] == 1


def test_dataframe_vacio():
    checks = validar_dataframe(pd.DataFrame())
    assert checks["existe"] is False
    assert checks["estado"] == "vacio"


def test_no_marca_fines_de_semana_como_error():
    # Un salto de viernes a lunes NO debe marcar error (mercado cerrado).
    df = _df_con_fechas(["2020-01-03", "2020-01-06", "2020-01-07", "2020-01-08"])
    checks = validar_dataframe(df)
    assert checks["estado"] == "ok"