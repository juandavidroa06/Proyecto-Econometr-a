"""Pruebas de la Fase 6 (Markowitz): datos sintéticos y archivos reales."""

import numpy as np
import pandas as pd
import pytest

from config.environment import RUTA_PARTICIONES
from src.portfolio.markowitz import (
    estimar_parametros,
    filas_completas,
    frontera_eficiente,
    log_a_simple,
    maximo_sharpe,
    minima_varianza,
    pesos_igual,
    seleccionar_universo_liquido,
    verificar_pesos,
)
from src.portfolio.metricas import maximo_drawdown, metricas_portafolio


def _rend(n=500, seed=0, sigmas=(0.01, 0.02, 0.03), mus=(0.0005, 0.0005, 0.0005)):
    rng = np.random.default_rng(seed)
    datos = {f"A{i}": rng.normal(m, s, n)
             for i, (m, s) in enumerate(zip(mus, sigmas))}
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    return pd.DataFrame(datos, index=idx)


def test_log_a_simple():
    assert log_a_simple(pd.Series([np.log(1.1)])).iloc[0] == pytest.approx(0.1)


def test_filas_completas_no_imputa_y_cuenta():
    r = _rend(50)
    r.iloc[3, 1] = np.nan
    completos, n = filas_completas(r)
    assert n == 1 and len(completos) == 49 and not completos.isna().any().any()


def test_minima_varianza_no_correlacionados_es_inversa_de_varianza():
    sigmas = np.array([0.1, 0.2, 0.4])
    cov = pd.DataFrame(np.diag(sigmas ** 2), index=list("abc"), columns=list("abc"))
    w = minima_varianza(cov, peso_max=1.0)
    esperado = (1 / sigmas ** 2) / (1 / sigmas ** 2).sum()
    assert np.allclose(w.to_numpy(), esperado, atol=1e-4)


def test_restricciones_se_cumplen():
    par = estimar_parametros(log_a_simple(_rend(400, sigmas=(0.01, 0.02, 0.03, 0.015),
                                                 mus=(0.001, 0.0002, 0.0003, 0.0004))))
    for w in (pesos_igual(par["mu"].index), minima_varianza(par["cov"]),
              maximo_sharpe(par["mu"], par["cov"])):
        verificar_pesos(w.to_numpy(), 0.30)
        assert w.sum() == pytest.approx(1.0)
        assert (w >= 0).all() and (w <= 0.30 + 1e-6).all()


def test_tope_activo_y_restriccion_infactible():
    cov = pd.DataFrame(np.eye(3) * 0.04, index=list("abc"), columns=list("abc"))
    with pytest.raises(ValueError):
        minima_varianza(cov, peso_max=0.30)  # 3 * 0.30 < 1
    with pytest.raises(ValueError):
        pesos_igual(["a", "b", "c"], peso_max=0.30)


def test_maximo_sharpe_prefiere_el_activo_dominante():
    mu = pd.Series([0.20, 0.02, 0.02, 0.02], index=list("abcd"))
    cov = pd.DataFrame(np.eye(4) * 0.04, index=mu.index, columns=mu.index)
    w = maximo_sharpe(mu, cov, rf=0.0, peso_max=0.5)
    assert w["a"] == pytest.approx(0.5, abs=1e-4)


def test_frontera_es_creciente_en_riesgo_y_retorno():
    par = estimar_parametros(log_a_simple(_rend(400, mus=(0.001, 0.0004, 0.0002))))
    fr = frontera_eficiente(par["mu"], par["cov"], peso_max=0.6, puntos=10)
    assert len(fr) >= 5
    assert fr["retorno"].is_monotonic_increasing
    assert fr["volatilidad"].is_monotonic_increasing


def test_estimar_parametros_exige_observaciones_suficientes():
    with pytest.raises(ValueError):
        estimar_parametros(_rend(4))


def test_rendimientos_infinitos_se_rechazan():
    r = _rend(50)
    r.iloc[0, 0] = np.inf
    with pytest.raises(ValueError):
        filas_completas(r)


def test_seleccion_universo_liquido_usa_solo_lo_recibido():
    r = _rend(200)
    r.iloc[:100, 2] = 0.0  # 50 % de días sin cambio
    liquidos, iliquidos, _ = seleccionar_universo_liquido(r, umbral=0.20)
    assert iliquidos == ["A2"] and "A2" not in liquidos


def test_metricas_con_rendimiento_constante():
    idx = pd.date_range("2024-01-01", periods=10, freq="B")
    rend = pd.DataFrame({"a": 0.01, "b": 0.01}, index=idx)
    w = pd.Series([0.5, 0.5], index=["a", "b"])
    m = metricas_portafolio(rend, w, rf=0.0, dias=252)
    assert m["retorno_anual"] == pytest.approx(0.01 * 252)
    assert m["rendimiento_acumulado"] == pytest.approx(1.01 ** 10 - 1)
    assert m["max_drawdown"] == 0.0


def test_maximo_drawdown_caida_conocida():
    r = pd.Series([0.1, -0.5, 0.0])
    assert maximo_drawdown(r) == pytest.approx(-0.5)


def test_metricas_exigen_mismo_orden_de_activos():
    idx = pd.date_range("2024-01-01", periods=5, freq="B")
    rend = pd.DataFrame({"a": 0.01, "b": 0.02}, index=idx)
    with pytest.raises(ValueError):
        metricas_portafolio(rend, pd.Series([0.5, 0.5], index=["b", "a"]))


@pytest.mark.skipif(not (RUTA_PARTICIONES / "huellas.json").exists(),
                    reason="Faltan las particiones (etapa_fase5).")
def test_fase6_sobre_datos_reales_cumple_restricciones():
    from src.portfolio.fase6 import ejecutar_fase6

    res = ejecutar_fase6(guardar=False)
    sumas = res["pesos"].groupby(["universo", "portafolio"])["peso"].sum()
    assert np.allclose(sumas.to_numpy(), 1.0)
    assert (res["pesos"]["peso"] >= -1e-9).all()
    assert (res["pesos"]["peso"] <= 0.30 + 1e-6).all()
    assert set(res["metricas"]["bloque"]) == {"train", "validacion"}
