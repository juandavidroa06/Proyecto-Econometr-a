"""Pruebas de la Fase 10 (DEC-027): Holm, bootstrap, MCS, R²_OS y Pesaran-Timmermann."""

import numpy as np
import pandas as pd
import pytest

from src.comparacion import estadistica as est


def test_holm_valores_conocidos():
    p = pd.Series([0.01, 0.04, 0.03, np.nan])
    h = est.holm(p)
    # Orden: 0.01*3=0.03, 0.03*2=0.06, 0.04*1=0.04 -> monotonía => 0.06.
    assert h.tolist()[:3] == pytest.approx([0.03, 0.06, 0.06])
    assert np.isnan(h.iloc[3])


def test_holm_no_supera_uno():
    assert est.holm([0.5, 0.6, 0.9]).max() == 1.0


def test_bootstrap_bloques_forma_rango_y_semilla():
    a = est.bootstrap_bloques(50, 100, 7, semilla=1)
    b = est.bootstrap_bloques(50, 100, 7, semilla=1)
    assert a.shape == (100, 50) and a.min() >= 0 and a.max() < 50
    np.testing.assert_array_equal(a, b)
    # Dentro de un bloque los índices son consecutivos (circulares).
    assert ((a[:, 1] - a[:, 0]) % 50 == 1).all()


def test_mcs_excluye_un_modelo_claramente_peor():
    rng = np.random.default_rng(0)
    base = rng.normal(1, 0.2, 300)
    perdidas = pd.DataFrame({"bueno": base, "igual": base + rng.normal(0, 0.01, 300),
                             "malo": base + 0.5})
    tabla = est.model_confidence_set(perdidas, alfa=0.10, n_remuestras=500, semilla=1)
    en = dict(zip(tabla["modelo"], tabla["en_mcs"]))
    assert en["bueno"] and en["igual"] and not en["malo"]


def test_mcs_incluye_todos_si_son_equivalentes():
    rng = np.random.default_rng(1)
    perdidas = pd.DataFrame(rng.normal(1, 0.3, (300, 3)), columns=list("abc"))
    tabla = est.model_confidence_set(perdidas, alfa=0.05, n_remuestras=500, semilla=2)
    assert tabla["en_mcs"].all()
    assert tabla["pvalor_mcs"].max() == 1.0


def test_mcs_rechaza_faltantes():
    with pytest.raises(ValueError):
        est.model_confidence_set(pd.DataFrame({"a": [1.0, np.nan], "b": [1.0, 2.0]}))


def test_r2_fuera_de_muestra():
    ref = np.ones(100)
    r = est.r2_fuera_de_muestra(np.full(100, 0.9), ref, n_remuestras=200, semilla=3)
    assert r["r2_os"] == pytest.approx(0.1)
    assert r["ic_inf"] == pytest.approx(0.1) and r["ic_sup"] == pytest.approx(0.1)


def test_pesaran_timmermann_detecta_direccion_y_no_inventa():
    rng = np.random.default_rng(4)
    y = rng.normal(size=500)
    bueno = est.pesaran_timmermann(y, y + rng.normal(0, 0.5, 500))
    assert bueno["acierto"] > 0.75 and bueno["pt_pvalor"] < 0.001
    azar = est.pesaran_timmermann(y, rng.normal(size=500))
    assert azar["pt_pvalor"] > 0.01
    constante = est.pesaran_timmermann(y, np.full(500, 0.3))   # signo sin variación
    assert np.isnan(constante["pt_estadistico"])


def test_pesaran_timmermann_ignora_ceros():
    y = np.array([0.0] * 5 + [1.0, -1.0] * 10)
    f = np.array([1.0] * 5 + [1.0, -1.0] * 10)
    assert est.pesaran_timmermann(y, f)["n"] == 20
