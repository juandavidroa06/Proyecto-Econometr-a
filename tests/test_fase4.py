"""Tests de la Fase 4: partición temporal, iliquidez, saltos y pruebas."""

import numpy as np
import pandas as pd
import pytest

from src.preprocessing.split import particion_temporal
from src.exploratory_analysis.liquidity import (
    racha_maxima_sin_cambio,
    auditar_iliquidez,
)
from src.exploratory_analysis.anomalies import (
    detectar_saltos_reversibles,
    sensibilidad_volatilidad_movil,
)
from src.exploratory_analysis.stat_tests import pruebas_rendimientos


def _df(n=300):
    idx = pd.date_range("2022-01-03", periods=n, freq="B")
    return pd.DataFrame({"a": np.arange(n, dtype=float)}, index=idx)


def test_particion_es_cronologica_y_sin_solape():
    df = _df()
    p = particion_temporal(df, "2022-06-30", "2022-12-31")
    assert p["train"].index.max() < p["validacion"].index.min()
    assert p["validacion"].index.max() < p["test"].index.min()
    assert sum(len(b) for b in p.values()) == len(df)


def test_particion_rechaza_cortes_invalidos_o_bloques_vacios():
    df = _df()
    with pytest.raises(ValueError):
        particion_temporal(df, "2022-12-31", "2022-06-30")
    with pytest.raises(ValueError):
        particion_temporal(df, "2010-01-01", "2010-06-30")


def test_particion_rechaza_indice_desordenado():
    df = _df().iloc[::-1]
    with pytest.raises(ValueError):
        particion_temporal(df, "2022-06-30", "2022-12-31")


def test_racha_maxima():
    s = pd.Series([1, 1, 1, 1, 2, 2, 3, 3, 3.0])
    assert racha_maxima_sin_cambio(s) == 3


def test_auditar_iliquidez_marca_pero_no_decide():
    idx = pd.date_range("2024-01-01", periods=100, freq="B")
    ilíquida = pd.DataFrame({"Close": 10.0, "Volume": 0}, index=idx)
    liquida = pd.DataFrame(
        {"Close": np.linspace(10, 20, 100), "Volume": 1000}, index=idx)
    res = auditar_iliquidez({"ilíquida": ilíquida, "líquida": liquida})
    fila = res.set_index("empresa")
    assert fila.loc["ilíquida", "supera_umbral"]
    assert not fila.loc["líquida", "supera_umbral"]
    assert (res["decision"] == "pendiente").all()


def test_salto_reversible_detectado_y_no_modifica_datos():
    idx = pd.date_range("2024-01-01", periods=30, freq="B")
    r = pd.Series(0.001, index=idx)
    r.iloc[10] = -0.26
    r.iloc[11] = 0.265
    df = pd.DataFrame({"X": r})
    copia = df.copy()
    saltos = detectar_saltos_reversibles(df)
    assert len(saltos) == 1
    assert saltos.iloc[0]["fecha_salto"] == idx[10]
    pd.testing.assert_frame_equal(df, copia)


def test_salto_sin_reversion_no_se_marca():
    idx = pd.date_range("2024-01-01", periods=30, freq="B")
    r = pd.Series(0.001, index=idx)
    r.iloc[10] = 0.30  # cambio de nivel real, sin reversión
    assert detectar_saltos_reversibles(pd.DataFrame({"X": r})).empty


def test_sensibilidad_volatilidad_baja_sin_el_evento():
    idx = pd.date_range("2024-01-01", periods=120, freq="B")
    rng = np.random.default_rng(42)
    r = pd.Series(rng.normal(0, 0.01, 120), index=idx)
    r.iloc[60], r.iloc[61] = -0.26, 0.265
    out = sensibilidad_volatilidad_movil(
        pd.DataFrame({"X": r}), "X", idx[60], idx[61])
    assert out["vol_max_sin_evento"] < out["vol_max_con_evento"]


def test_pruebas_rendimientos_devuelve_una_fila_por_serie():
    rng = np.random.default_rng(42)
    df = pd.DataFrame({"A": rng.normal(0, 0.01, 400),
                       "B": rng.normal(0, 0.02, 400)})
    res = pruebas_rendimientos(df)
    assert list(res["serie"]) == ["A", "B"]
    assert res["jb_pvalor"].between(0, 1).all()
