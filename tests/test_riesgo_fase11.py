"""Pruebas de la Fase 11 (DEC-028): VaR/ES sin información futura y backtesting."""

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from src.riesgo import backtesting as bt
from src.riesgo import medidas


@pytest.fixture
def serie():
    rng = np.random.default_rng(11)
    r = pd.Series(rng.standard_t(5, 900) * 0.01, index=pd.bdate_range("2020-01-01", periods=900))
    return r[:650], r[650:]


# --- Medidas ----------------------------------------------------------------------

@pytest.mark.parametrize("metodo", medidas.METODOS)
def test_var_positivo_y_es_mayor_que_var(serie, metodo):
    tr, va = serie
    m = medidas.calcular(metodo, tr, va, 0.01)
    assert (m["var"] > 0).all() and (m["es"] >= m["var"]).all()
    assert m.index.equals(va.index) and not m.isna().any().any()


@pytest.mark.parametrize("metodo", medidas.METODOS)
def test_var_no_usa_informacion_futura(serie, metodo):
    tr, va = serie
    base = medidas.calcular(metodo, tr, va, 0.05)
    alterada = va.copy()
    alterada.iloc[100:] -= 0.3            # pérdidas grandes desde el día 100
    otro = medidas.calcular(metodo, tr, alterada, 0.05)
    # El VaR del día 100 usa datos hasta el 99: no cambia; el del 101 sí.
    pd.testing.assert_frame_equal(base.iloc[:101], otro.iloc[:101])
    assert otro["var"].iloc[101] != base["var"].iloc[101]


def test_historica_es_el_cuantil_de_la_ventana(serie):
    tr, va = serie
    m = medidas.historica(tr, va, 0.05, ventana=250)
    esperado = -np.quantile(tr.to_numpy()[-250:], 0.05)
    assert m["var"].iloc[0] == pytest.approx(esperado)


def test_t_estandarizada_coincide_con_simulacion():
    var, es = medidas._t_estandarizada(0.01, 5.0)
    rng = np.random.default_rng(0)
    z = rng.standard_t(5, 2_000_000) * np.sqrt(3 / 5)     # varianza unitaria
    q = np.quantile(z, 0.01)
    assert var == pytest.approx(-q, rel=0.01)
    assert es == pytest.approx(-z[z <= q].mean(), rel=0.02)


def test_t_con_nu_menor_o_igual_a_2_falla():
    with pytest.raises(ValueError):
        medidas._t_estandarizada(0.01, 2.0)


def test_ewma_normal_formula(serie):
    tr, va = serie
    m = medidas.ewma_normal(tr, va, 0.01)
    sigma = m["var"] / -stats.norm.ppf(0.01)
    np.testing.assert_allclose(m["es"], sigma * stats.norm.pdf(stats.norm.ppf(0.01)) / 0.01)


# --- Backtesting --------------------------------------------------------------------

def test_kupiec_sin_rechazo_con_tasa_exacta():
    ex = np.zeros(1000, bool)
    ex[::100] = True                       # 10 excesos de 1000 = 1 %
    lr, p = bt.kupiec(ex, 0.01)
    assert lr == pytest.approx(0.0, abs=1e-9) and p == pytest.approx(1.0)


def test_kupiec_rechaza_demasiados_excesos():
    ex = np.zeros(250, bool)
    ex[:15] = True
    assert bt.kupiec(ex, 0.01)[1] < 0.001


def test_christoffersen_detecta_agrupamiento():
    disperso = np.zeros(500, int)
    disperso[::50] = 1
    agrupado = np.zeros(500, int)
    agrupado[100:110] = 1
    assert bt.christoffersen(disperso, 0.02)["pvalor_ind"] > 0.5
    assert bt.christoffersen(agrupado, 0.02)["pvalor_ind"] < 0.001


@pytest.mark.parametrize("n_excesos,zona", [(0, "verde"), (4, "verde"), (5, "amarillo"),
                                            (9, "amarillo"), (10, "rojo")])
def test_zonas_basilea_250_dias(n_excesos, zona):
    assert bt.zona_basilea(n_excesos, 250) == zona


def test_prueba_es_y_perdida_cuantilica():
    r = np.array([-0.05, 0.01, -0.03, 0.02, -0.04] + [0.0] * 20)
    var = np.full(25, 0.02)
    es = np.full(25, 0.04)
    res = bt.prueba_es(r, var, es)
    assert res["n_excesos"] == 3 and res["perdida_sobre_es"] == pytest.approx(1.0)
    tick = bt.perdida_cuantilica(np.array([-0.05, 0.01]), np.array([0.02, 0.02]), 0.01)
    np.testing.assert_allclose(tick, [(0.01 - 1) * (-0.05 + 0.02), 0.01 * (0.01 + 0.02)])
