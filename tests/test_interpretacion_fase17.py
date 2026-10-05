"""Pruebas de la Fase 17 (DEC-039/040): cálculos auxiliares de la interpretación."""

import numpy as np
import pandas as pd
import pytest

from src.interpretacion import fase17


def test_ols_recupera_coeficientes():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(500, 2))
    y = 0.3 + X @ np.array([1.5, -0.5]) + rng.normal(0, 0.01, 500)
    np.testing.assert_allclose(fase17._ols(y, X), [1.5, -0.5], atol=0.01)


def test_caracteristicas_de_la_ventana():
    idx = pd.bdate_range("2023-01-02", periods=6)
    v = pd.DataFrame({"A": [0.01, 0.0, -0.01, 0.0, 0.02, 0.0],
                      "B": [0.02, 0.0, -0.02, 0.0, 0.04, 0.0],
                      "C": [-0.01, 0.01, 0.0, 0.02, -0.02, 0.01]}, index=idx)
    c = fase17._caracteristicas(v)
    assert c.loc["A", "pct_sin_cambio"] == pytest.approx(0.5)
    assert c.loc["B", "volatilidad"] == pytest.approx(2 * c.loc["A", "volatilidad"])
    corr_ab = np.corrcoef(v["A"], v["B"])[0, 1]
    corr_ac = np.corrcoef(v["A"], v["C"])[0, 1]
    assert c.loc["A", "correlacion_media"] == pytest.approx((corr_ab + corr_ac) / 2)


def test_dimson_detecta_reaccion_rezagada():
    """Una acción que responde al mercado con un día de retraso tiene beta
    simple ~0 y beta de Dimson ~1."""
    rng = np.random.default_rng(1)
    idx = pd.bdate_range("2020-01-01", periods=1200)
    otras = pd.DataFrame(rng.normal(0, 0.01, (1200, 3)), index=idx, columns=list("XYZ"))
    mercado = otras.mean(axis=1)
    lenta = mercado.shift(1).fillna(0) + rng.normal(0, 0.001, 1200)
    datos = otras.assign(L=lenta)
    t, _ = fase17.b_dimson(datos, iliquidos=["L"])
    fila = t.set_index("empresa").loc["L"]
    assert abs(fila["beta_simple"]) < 0.15
    assert fila["beta_dimson"] == pytest.approx(1.0, abs=0.15)


def test_autocorrelacion_de_primer_orden():
    rng = np.random.default_rng(2)
    e = rng.normal(size=3000)
    r = e[1:] - 0.5 * e[:-1]                       # MA(1): autocorrelación teórica -0.4
    datos = pd.DataFrame({"A": r}, index=pd.bdate_range("2015-01-01", periods=len(r)))
    t, _ = fase17.d_autocorrelacion(datos, iliquidos=[])
    assert t.loc[0, "autocorrelacion_1"] == pytest.approx(-0.4, abs=0.05)
