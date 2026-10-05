"""Pruebas de la Fase 14 (DEC-032/033): motor walk-forward sin información futura."""

import numpy as np
import pandas as pd
import pytest

from config.settings import SECTORES
from src.backtesting import fase14, motor
from src.optimizacion import optimizadores as opt


@pytest.fixture
def rend():
    rng = np.random.default_rng(14)
    idx = pd.bdate_range("2023-01-02", "2023-06-30")
    return pd.DataFrame(rng.normal(0.0005, 0.01, (len(idx), 3)), index=idx, columns=list("ABC"))


def test_fechas_rebalanceo_fin_de_mes_y_trimestre(rend):
    m = motor.fechas_rebalanceo(rend.index, "2023-01-01", "2023-06-30", "M")
    assert list(m.strftime("%Y-%m-%d")) == ["2023-01-31", "2023-02-28", "2023-03-31",
                                            "2023-04-28", "2023-05-31", "2023-06-30"]
    q = motor.fechas_rebalanceo(rend.index, "2023-01-01", "2023-06-30", "Q")
    assert list(q.strftime("%Y-%m-%d")) == ["2023-03-31", "2023-06-30"]


def test_comprar_y_mantener_sin_costos(rend):
    f0 = pd.Timestamp("2023-01-31")
    w = pd.Series([0.5, 0.3, 0.2], index=list("ABC"))
    diario, rot = motor.simular(rend, {f0: w}, 0.0, "2023-06-30")
    despues = rend.loc[rend.index > f0]
    esperado = float((w * (1 + despues).prod()).sum())
    assert (1 + diario["neto"]).prod() == pytest.approx(esperado)
    assert rot.iloc[0] == 1.0


def test_rotacion_y_costos(rend):
    fechas = motor.fechas_rebalanceo(rend.index, "2023-01-01", "2023-03-31", "M")
    w = pd.Series([1 / 3] * 3, index=list("ABC"))
    obj = {f: w for f in fechas}
    sin, rot = motor.simular(rend, obj, 0.0, "2023-03-31")
    con, _ = motor.simular(rend, obj, 0.01, "2023-03-31")
    # Rotación del 2023-02-28 = |w - w derivado| calculado a mano.
    tramo = rend.loc["2023-02-01":"2023-02-28"]
    deriva = w * (1 + tramo).prod()
    deriva = deriva / deriva.sum()
    assert rot[pd.Timestamp("2023-02-28")] == pytest.approx(float((w - deriva).abs().sum()))
    # Costo del rebalanceo descontado ese mismo día; compra inicial en el primer día.
    assert con.loc["2023-02-28", "costo"] == pytest.approx(0.01 * rot[pd.Timestamp("2023-02-28")])
    assert con["costo"].iloc[0] == pytest.approx(0.01)
    riqueza_sin = (1 + sin["neto"]).prod()
    riqueza_con = (1 + con["neto"]).prod()
    factor = np.prod([1 - 0.01 * x for x in rot.to_numpy()])
    assert riqueza_con == pytest.approx(riqueza_sin * factor)


def test_rendimiento_faltante_vale_cero(rend):
    r = rend.copy()
    r.loc["2023-03-15", "A"] = np.nan
    w = pd.Series([1.0, 0.0, 0.0], index=list("ABC"))
    diario, _ = motor.simular(r, {pd.Timestamp("2023-02-28"): w}, 0.0, "2023-03-31")
    assert diario.loc["2023-03-15", "bruto"] == 0.0


def test_pesos_no_usan_datos_posteriores(rend):
    restr = opt.Restricciones(list("ABC"), 0.6, {"A": "x", "B": "y", "C": "z"}, None)
    f = pd.Timestamp("2023-04-28")
    base = fase14.pesos_estrategia("min_var_muestral", motor.ventana_estimacion(rend, f, 60), restr)
    alterado = rend.copy()
    alterado.loc[alterado.index > f] *= 50
    otro = fase14.pesos_estrategia("min_var_muestral",
                                   motor.ventana_estimacion(alterado, f, 60), restr)
    pd.testing.assert_series_equal(base, otro)
    ventana = motor.ventana_estimacion(rend, f, 60)
    assert ventana.index.max() == f and len(ventana) == 60


def test_ventana_insuficiente_falla(rend):
    with pytest.raises(ValueError):
        motor.ventana_estimacion(rend, rend.index[10], 60)


def test_diferencia_sharpe_identica_y_mejor():
    rng = np.random.default_rng(2)
    a = rng.normal(0.0005, 0.01, 800)
    d = motor.diferencia_sharpe(a, a, 300, 21, 1)
    assert d["dif_sharpe"] == pytest.approx(0.0) and d["pvalor"] == pytest.approx(1.0)
    mejor = motor.diferencia_sharpe(a + 0.002, a, 300, 21, 1)
    assert mejor["dif_sharpe"] > 0 and mejor["pvalor"] < 0.01


def test_tasa_diaria_usa_el_ultimo_ibr_publicado():
    tasas = pd.DataFrame({"IBR": [10.0, 12.0]},
                         index=pd.to_datetime(["2024-01-02", "2024-01-05"]))
    idx = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-05"])
    rf = fase14.tasa_diaria(tasas, idx)
    ef10 = (1 + 0.10 / 360) ** 365 - 1
    assert rf.iloc[1] == pytest.approx((1 + ef10) ** (1 / 252) - 1)
    with pytest.raises(ValueError):
        fase14.tasa_diaria(tasas, pd.to_datetime(["2024-01-01"]))


def test_metricas_sharpe_indefinido_sin_variacion():
    idx = pd.bdate_range("2024-01-01", periods=30)
    rf = pd.Series(0.0004, index=idx)
    m = motor.metricas(rf, rf)
    assert np.isnan(m["sharpe"]) and m["max_drawdown"] == 0.0


def test_sectores_cubren_el_universo():
    assert set(SECTORES) == {"Banco de Bogota", "Banco Davivienda PF", "Grupo Bolivar",
                             "Ecopetrol", "Celsia", "Promigas", "ETB", "Nutresa", "Mineros SA"}
