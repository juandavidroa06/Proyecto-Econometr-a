"""Pruebas de DEC-022: precios inválidos de la fuente (NaN + bandera, sin inventar)."""

import numpy as np
import pandas as pd
import pytest

from config.settings import FECHAS_DATO_INVALIDO_FUENTE
from src.preprocessing.invalid_data import (
    bandera_dato_invalido,
    rendimientos_saltando_invalidos,
)
from src.preprocessing.returns import calcular_rendimientos


@pytest.fixture
def precios():
    fechas = pd.to_datetime(["2024-05-02", "2024-05-03", "2024-05-06", "2024-05-07"])
    return pd.DataFrame({"A": [100.0, 80.0, 102.0, 104.0],
                         "B": [50.0, 60.0, np.nan, 51.0]}, index=fechas)


def test_bandera_marca_todas_las_empresas(precios):
    b = bandera_dato_invalido(precios, ["2024-05-03"])
    assert b.loc["2024-05-03"].all() and b.sum().sum() == 2


def test_fecha_mal_escrita_dentro_del_rango_falla(precios):
    with pytest.raises(ValueError):
        bandera_dato_invalido(precios, ["2024-05-04"])  # sábado, no está


def test_fecha_fuera_del_rango_se_ignora(precios):
    assert not bandera_dato_invalido(precios, ["2019-01-02"]).any().any()


def test_rendimiento_salta_la_fecha_invalida(precios):
    b = bandera_dato_invalido(precios, ["2024-05-03"])
    simples, logs, abarca = rendimientos_saltando_invalidos(precios.mask(b), b)
    assert np.isnan(logs.loc["2024-05-03", "A"])
    # 2 -> 6 de mayo: el precio inválido (80) no interviene.
    assert logs.loc["2024-05-06", "A"] == pytest.approx(np.log(102 / 100))
    assert simples.loc["2024-05-06", "A"] == pytest.approx(0.02)
    assert abarca.loc["2024-05-06"].all() and abarca.sum().sum() == 2


def test_los_nan_existentes_se_conservan(precios):
    b = bandera_dato_invalido(precios, ["2024-05-03"])
    _, logs, _ = rendimientos_saltando_invalidos(precios.mask(b), b)
    # B no tenía precio el 6 de mayo: sigue sin rendimiento ese día y el 7.
    assert logs["B"].isna().tolist() == [True, True, True, True]


def test_sin_fechas_invalidas_coincide_con_calculo_original(df_precios_sintetico):
    b = bandera_dato_invalido(df_precios_sintetico, [])
    simples, logs, abarca = rendimientos_saltando_invalidos(df_precios_sintetico, b)
    s0, l0 = calcular_rendimientos(df_precios_sintetico)
    pd.testing.assert_frame_equal(simples, s0)
    pd.testing.assert_frame_equal(logs, l0)
    assert not abarca.any().any()


def test_configuracion_dec022():
    assert tuple(FECHAS_DATO_INVALIDO_FUENTE) == ("2024-05-03",)
