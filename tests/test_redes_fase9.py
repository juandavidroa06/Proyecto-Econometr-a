"""Pruebas de la Fase 9 (DEC-026): escalado, secuencias sin futuro y redes."""

import numpy as np
import pandas as pd
import pytest

from src.machine_learning import variables
from src.neural_networks import datos as dnn
from src.neural_networks import redes


@pytest.fixture
def panel():
    rng = np.random.default_rng(5)
    fechas = pd.bdate_range("2023-01-02", periods=120)
    rend = pd.DataFrame(rng.normal(0, 0.01, (120, 2)), index=fechas, columns=["A", "B"])
    vol = pd.DataFrame(rng.integers(100, 1000, (120, 2)).astype(float),
                       index=fechas, columns=["A", "B"])
    ext = pd.DataFrame({"TRM": 4000 * np.exp(np.cumsum(rng.normal(0, 0.005, 120))),
                        "Brent": 80 * np.exp(np.cumsum(rng.normal(0, 0.01, 120)))},
                       index=fechas)
    return variables.construir_panel(rend, vol, ext)


def test_escalador_usa_solo_datos_de_ajuste():
    train = pd.DataFrame({"x": [1.0, 2.0, 3.0], "c": [1.0, 1.0, 1.0]})
    otro = pd.DataFrame({"x": [100.0], "c": [1.0]})
    esc = dnn.Escalador().ajustar(train)
    assert esc.media_["x"] == 2.0
    z = esc.transformar(otro)
    assert z.loc[0, "x"] == pytest.approx((100 - 2) / np.std([1, 2, 3]))
    assert z.loc[0, "c"] == 0.0           # columna constante: sin división por 0


def test_escalador_rechaza_columnas_distintas():
    esc = dnn.Escalador().ajustar(pd.DataFrame({"x": [1.0, 2.0]}))
    with pytest.raises(ValueError):
        esc.transformar(pd.DataFrame({"y": [1.0]}))


def test_secuencia_termina_en_el_origen_y_no_usa_futuro(panel):
    filas = panel[(panel["empresa"] == "A")].iloc[[60]][["Date", "empresa"]]
    X, mascara = dnn.secuencias(panel, filas, longitud=10)
    assert mascara.all() and X.shape == (1, 10, len(dnn.VARIABLES_SECUENCIA))
    a = panel[panel["empresa"] == "A"].reset_index(drop=True)
    esperado = a.loc[51:60, dnn.VARIABLES_SECUENCIA].to_numpy()
    np.testing.assert_allclose(X[0], esperado)
    # Alterar filas posteriores al origen no cambia la secuencia.
    alterado = panel.copy()
    alterado.loc[alterado["Date"] > filas["Date"].iloc[0], "r_lag0"] = 99.0
    X2, _ = dnn.secuencias(alterado, filas, longitud=10)
    np.testing.assert_allclose(X[0], X2[0])


def test_secuencia_con_faltantes_se_descarta(panel):
    p = panel.copy()
    fila = p[p["empresa"] == "B"].iloc[[70]][["Date", "empresa"]]
    p.loc[(p["empresa"] == "B") & (p["Date"] == p[p["empresa"] == "B"]["Date"].iloc[65]),
          "TRM_r1"] = np.nan
    X, mascara = dnn.secuencias(p, fila, longitud=10)
    assert not mascara.any() and len(X) == 0


def test_separar_interno_toma_el_final():
    fechas = pd.Series(np.repeat(pd.bdate_range("2023-01-02", periods=50), 2))
    ajuste, parada = dnn.separar_interno(fechas, 0.2)
    assert fechas[ajuste].max() < fechas[parada].min()
    assert parada.sum() == 20


def test_entrenamiento_reproducible_y_aprende():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(400, 3)).astype(np.float32)
    y = 0.01 * X[:, 0]                       # relación lineal simple (en proporción)
    crear = lambda: redes.MLP(3, ocultas=(8,), abandono=0.0)
    kw = dict(semilla=7, epocas=150, tam_lote=32)
    r1, h1 = redes.entrenar(crear, X[:300], y[:300], X[300:], y[300:], **kw)
    r2, h2 = redes.entrenar(crear, X[:300], y[:300], X[300:], y[300:], **kw)
    np.testing.assert_allclose(redes.predecir(r1, X[300:]), redes.predecir(r2, X[300:]))
    assert h1 == h2
    assert h1["mse_parada"] < np.var(y[300:]) * 0.2


def test_lstm_forma_de_salida():
    red = redes.LSTMRed(n_variables=5, n_estaticas=2, oculta=4)
    secuencia = np.zeros((6, 10, 5), dtype=np.float32)
    estaticas = np.zeros((6, 2), dtype=np.float32)
    assert redes.predecir(red, (secuencia, estaticas)).shape == (6,)
