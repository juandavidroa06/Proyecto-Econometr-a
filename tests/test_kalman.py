"""Pruebas del módulo de imputación con Filtro de Kalman."""

import numpy as np
import pandas as pd
import pytest

from src.preprocessing.kalman_imputation import (
    detectar_faltantes,
    imputar_serie,
    imputar_series_multiples,
    validar_imputacion,
)


def _serie_con_nan(n=120, pos_nan=60, semilla=7):
    rng = np.random.default_rng(semilla)
    precios = 100 + np.cumsum(rng.normal(0, 1.0, n))
    fechas = pd.date_range("2020-01-01", periods=n, freq="B")
    serie = pd.Series(precios, index=fechas, name="Adj Close")
    serie.iloc[pos_nan] = np.nan
    return serie


def test_deteccion_de_faltantes():
    serie = _serie_con_nan()
    mask = detectar_faltantes(serie)
    assert isinstance(mask, pd.Series)
    assert mask.sum() == 1
    assert mask.iloc[60]


def test_imputar_preserva_originales():
    serie = _serie_con_nan()
    imputada, bandera = imputar_serie(serie)

    observadas = serie.dropna()
    for fecha, valor in observadas.items():
        assert imputada.loc[fecha] == valor


def test_imputar_genera_valor_donde_habia_nan():
    serie = _serie_con_nan()
    imputada, bandera = imputar_serie(serie)
    assert not pd.isna(imputada.iloc[60])
    assert imputada.iloc[60] > 0


def test_bandera_marca_solo_imputados():
    serie = _serie_con_nan()
    imputada, bandera = imputar_serie(serie)
    assert bandera.sum() == 1
    assert bool(bandera.iloc[60]) is True
    assert bool(bandera.iloc[0]) is False


def test_sin_faltantes_devuelve_serie_sin_cambios():
    serie = _serie_con_nan()
    serie.iloc[60] = 105.0  # eliminar el NaN
    imputada, bandera = imputar_serie(serie)
    pd.testing.assert_series_equal(imputada, serie)
    assert not bandera.any()


def test_imputacion_falla_sin_suficientes_datos():
    # Solo 2 observaciones válidas: no se puede estimar el modelo.
    serie = pd.Series([100.0, np.nan, 102.0],
                      index=pd.to_datetime(["2020-01-01", "2020-01-02", "2020-01-03"]))
    imputada, bandera = imputar_serie(serie)
    assert pd.isna(imputada.iloc[1])
    assert not bandera.any()


def test_reportes_multiples_series():
    buena = _serie_con_nan(pos_nan=60)
    sin_nan = _serie_con_nan(pos_nan=60).fillna(105.0)
    imputadas, banderas, reporte = imputar_series_multiples(
        {"A": buena, "B": sin_nan}
    )
    assert len(reporte) == 1
    fila = reporte.iloc[0]
    assert fila["empresa"] == "A"
    assert fila["valor_original"] is None
    assert not pd.isna(fila["valor_imputado"])


def test_validacion_mae_rmse_finitos():
    serie = _serie_con_nan(pos_nan=60)
    serie.iloc[60] = serie.iloc[59]  # rellenar para validar sobre observados
    resultado = validar_imputacion(serie, n_ocultar=20, semilla=1)
    assert resultado["n_ocultados"] == 20
    assert np.isfinite(resultado["mae"])
    assert np.isfinite(resultado["rmse"])
    assert resultado["mae"] >= 0
    assert resultado["rmse"] >= 0
    assert len(resultado["detalle"]) == 20


def test_validacion_respeta_datos_reales():
    serie = _serie_con_nan(pos_nan=60)
    serie.iloc[60] = 110.0
    copia = serie.copy()
    validar_imputacion(serie, n_ocultar=15, semilla=3)
    pd.testing.assert_series_equal(serie, copia)