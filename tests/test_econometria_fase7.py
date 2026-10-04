"""Pruebas de la Fase 7 (DEC-023): ARIMA, GARCH, referencias y métricas."""

import numpy as np
import pandas as pd
import pytest

from src.econometrics import arima, evaluacion, garch


def _ar1(n=600, phi=0.5, semilla=1):
    rng = np.random.default_rng(semilla)
    e = rng.normal(0, 0.01, n)
    y = np.zeros(n)
    for t in range(1, n):
        y[t] = phi * y[t - 1] + e[t]
    return pd.Series(y, index=pd.bdate_range("2020-01-01", periods=n))


def _garch11(n=1500, omega=0.05, alpha=0.1, beta=0.85, semilla=2):
    rng = np.random.default_rng(semilla)
    h = np.empty(n)
    r = np.empty(n)
    h[0] = omega / (1 - alpha - beta)
    r[0] = np.sqrt(h[0]) * rng.standard_normal()
    for t in range(1, n):
        h[t] = omega + alpha * r[t - 1] ** 2 + beta * h[t - 1]
        r[t] = np.sqrt(h[t]) * rng.standard_normal()
    return pd.Series(r / 100, index=pd.bdate_range("2018-01-01", periods=n))


# --- Métricas -----------------------------------------------------------------

def test_mae_rmse():
    y = pd.Series([1.0, -1.0, 2.0])
    f = pd.Series([0.0, 0.0, 0.0])
    assert evaluacion.mae(y, f) == pytest.approx(4 / 3)
    assert evaluacion.rmse(y, f) == pytest.approx(np.sqrt(2))


def test_metricas_rechazan_indices_distintos_o_nan():
    with pytest.raises(ValueError):
        evaluacion.mae(pd.Series([1.0], index=[0]), pd.Series([1.0], index=[1]))
    with pytest.raises(ValueError):
        evaluacion.mae(pd.Series([np.nan]), pd.Series([1.0]))


def test_qlike_es_minimo_en_la_varianza_verdadera():
    proxy = pd.Series(np.full(50, 4.0))
    valores = {h: evaluacion.qlike(proxy, pd.Series(np.full(50, h))) for h in (2.0, 4.0, 8.0)}
    assert min(valores, key=valores.get) == 4.0


def test_diebold_mariano_detecta_modelo_mejor():
    rng = np.random.default_rng(0)
    buena = pd.Series(rng.uniform(0, 1, 300))
    mala = buena + 0.5
    dm = evaluacion.diebold_mariano(buena, mala)
    assert dm["dm_estadistico"] < 0 and dm["dm_pvalor"] < 0.01
    igual = evaluacion.diebold_mariano(buena, buena)
    assert np.isnan(igual["dm_estadistico"])


# --- ARIMA ----------------------------------------------------------------------

def test_seleccion_recupera_ar1():
    orden, tabla = arima.seleccionar_orden(_ar1()[:500], 2, 2, "bic")
    assert orden == (1, 0)
    assert len(tabla) == 9
    # El elegido convergió; los que no, quedan registrados (no se ocultan).
    elegido = tabla[(tabla["p"] == 1) & (tabla["q"] == 0)].iloc[0]
    assert elegido["convergio"]
    assert (tabla.loc[~tabla["convergio"], "avisos"] != "").all()


def test_arima_rechaza_faltantes():
    s = _ar1()
    s.iloc[5] = np.nan
    with pytest.raises(ValueError):
        arima.seleccionar_orden(s, 1, 1)


def test_pronostico_arima_no_usa_informacion_futura():
    s = _ar1()
    train, valid = s[:500], s[500:]
    res, _ = arima.ajustar_arima(train, (1, 0))
    base = arima.pronostico_un_paso(train, valid, res)
    alterada = valid.copy()
    alterada.iloc[50:] += 1.0          # cambiar el "futuro" desde la obs. 50
    otro = arima.pronostico_un_paso(train, alterada, res)
    # Los pronósticos hasta la obs. 50 (que usan datos hasta la 49) no cambian.
    pd.testing.assert_series_equal(base.iloc[:51], otro.iloc[:51])
    assert not np.isclose(base.iloc[51], otro.iloc[51])


def test_pronostico_arima_exige_orden_temporal():
    s = _ar1()
    res, _ = arima.ajustar_arima(s[:500], (1, 0))
    with pytest.raises(ValueError, match="Leakage"):
        arima.pronostico_un_paso(s[100:500], s[:100], res)


# --- GARCH y referencias ---------------------------------------------------------

def test_garch_recupera_persistencia():
    r = _garch11()
    res = garch.ajustar_garch(r[:1200], r[1200:], distribucion="normal")
    resumen = garch.resumen_garch(res)
    assert resumen["convergio"]
    assert resumen["persistencia"] == pytest.approx(0.95, abs=0.05)
    assert res.nobs == 1200   # solo entrenamiento en la estimación


def test_pronostico_garch_no_usa_informacion_futura():
    r = _garch11()
    train, valid = r[:1200], r[1200:]
    base = garch.pronostico_varianza_un_paso(
        garch.ajustar_garch(train, valid, "normal"), train, valid)
    alterada = valid.copy()
    alterada.iloc[100:] *= 5
    otro = garch.pronostico_varianza_un_paso(
        garch.ajustar_garch(train, alterada, "normal"), train, alterada)
    pd.testing.assert_series_equal(base.iloc[:101], otro.iloc[:101])
    assert otro.iloc[101] > base.iloc[101]


def test_ewma_formula_y_sin_futuro():
    train = pd.Series([0.01, -0.02, 0.03], index=pd.bdate_range("2024-01-01", periods=3))
    valid = pd.Series([0.01, 0.05], index=pd.bdate_range("2024-01-04", periods=2))
    h = garch.varianza_ewma(train, valid, lam=0.9)
    y = np.concatenate([train, valid]) * 100
    esperado = [np.var(train * 100, ddof=1)]
    for t in range(1, 5):
        esperado.append(0.9 * esperado[-1] + 0.1 * y[t - 1] ** 2)
    np.testing.assert_allclose(h.to_numpy(), esperado[3:])


def test_varianza_constante_es_la_de_train():
    s = _ar1()
    h = garch.varianza_constante(s[:500], s[500:])
    assert h.nunique() == 1
    assert h.iloc[0] == pytest.approx((s[:500] * 100).var(ddof=1))
