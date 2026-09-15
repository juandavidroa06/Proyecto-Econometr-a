"""Pruebas del cálculo de rendimientos."""

import numpy as np
import pandas as pd

from src.preprocessing.returns import (
    rendimiento_simple,
    rendimiento_log,
    calcular_rendimientos,
)


def test_rendimiento_simple_primera_observacion_nan(serie_precios):
    simples = rendimiento_simple(serie_precios)
    assert pd.isna(simples.iloc[0])


def test_rendimiento_log_primera_observacion_nan(serie_precios):
    logs = rendimiento_log(serie_precios)
    assert pd.isna(logs.iloc[0])


def test_rendimiento_simple_valor_manual():
    precios = pd.Series([100.0, 110.0, 99.0])
    simples = rendimiento_simple(precios)
    assert np.isclose(simples.iloc[1], 0.10)
    assert np.isclose(simples.iloc[2], -0.10)


def test_rendimiento_log_valor_manual():
    precios = pd.Series([100.0, 110.0, 88.0])
    logs = rendimiento_log(precios)
    assert np.isclose(logs.iloc[1], np.log(110 / 100))
    assert np.isclose(logs.iloc[2], np.log(88 / 110))


def test_calcular_rendimientos_devuelve_tupla(serie_precios):
    simples, logs = calcular_rendimientos(serie_precios)
    assert isinstance(simples, pd.Series)
    assert isinstance(logs, pd.Series)
    assert len(simples) == len(serie_precios)


def test_rendimientos_preservan_indice_ordenado(df_precios_sintetico):
    simples, logs = calcular_rendimientos(df_precios_sintetico)
    assert simples.index.is_monotonic_increasing
    assert logs.index.is_monotonic_increasing
    assert not simples.index.duplicated().any()
    assert not logs.index.duplicated().any()