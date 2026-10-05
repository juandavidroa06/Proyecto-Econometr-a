"""Pruebas del análisis semanal (DEC-029/DEC-030): panel sin futuro y HAR."""

import numpy as np
import pandas as pd
import pytest

from src.volatilidad_semanal import ejecutar as ej
from src.volatilidad_semanal import panel as pv


@pytest.fixture
def datos():
    rng = np.random.default_rng(21)
    fechas = pd.bdate_range("2022-01-03", periods=300)
    rend = pd.DataFrame(rng.normal(0, 0.01, (300, 2)), index=fechas, columns=["A", "B"])
    vol = pd.DataFrame(rng.integers(100, 1000, (300, 2)).astype(float), index=fechas,
                       columns=["A", "B"])
    ext = pd.DataFrame({"TRM": 4000 * np.exp(np.cumsum(rng.normal(0, 0.005, 300)))},
                       index=fechas)
    return rend, vol, ext


def test_rv_semanal_es_suma_de_cuadrados(datos):
    rend, vol, _ = datos
    s = pv.resumen_semanal(rend["A"], vol["A"])
    semana = s.index[3]
    dias = rend["A"][rend.index.to_period("W-FRI") == semana]
    assert s.loc[semana, "rv"] == pytest.approx(((100 * dias) ** 2).sum())
    assert s.loc[semana, "n_dias"] == len(dias)
    assert s.loc[semana, "rv_dia"] == pytest.approx((100 * dias.iloc[-1]) ** 2)


def test_objetivo_es_la_semana_siguiente(datos):
    rend, vol, ext = datos
    p = pv.construir_panel_semanal(rend, vol, ext, ["A", "B"])
    a = p[p["empresa"] == "A"].reset_index(drop=True)
    assert a.loc[10, "rv_objetivo"] == pytest.approx(a.loc[11, "rv_sem"])
    assert a.loc[10, "semana_objetivo"] == a.loc[11, "semana"]


def test_semana_con_pocos_dias_no_es_objetivo(datos):
    rend, vol, ext = datos
    r = rend.copy()
    semana = r.index.to_period("W-FRI")[40]
    en_semana = r.index[r.index.to_period("W-FRI") == semana]
    r.loc[en_semana[2:], "A"] = np.nan                  # deja 2 días: semana inválida
    p = pv.construir_panel_semanal(r, vol, ext, ["A", "B"])
    a = p[p["empresa"] == "A"]
    assert semana not in set(a["semana"])
    previa = a[a["semana"] == semana - 1]
    assert previa["rv_objetivo"].isna().all()


def test_variables_no_cambian_al_alterar_el_futuro(datos):
    rend, vol, ext = datos
    base, cols = pv.variables_modelo(pv.construir_panel_semanal(rend, vol, ext, ["A", "B"]))
    corte = base["ultimo_dia"].iloc[100]
    r2, v2, e2 = rend.copy(), vol.copy(), ext.copy()
    r2.loc[r2.index > corte] *= 5
    v2.loc[v2.index > corte] *= 9
    e2.loc[e2.index >= corte] *= 2            # externas del último día también
    otro, _ = pv.variables_modelo(pv.construir_panel_semanal(r2, v2, e2, ["A", "B"]))
    hasta = base["ultimo_dia"] <= corte
    pd.testing.assert_frame_equal(base.loc[hasta, cols].reset_index(drop=True),
                                  otro.loc[hasta, cols].reset_index(drop=True))


def test_separar_por_semana_objetivo(datos):
    rend, vol, ext = datos
    p, cols = pv.variables_modelo(pv.construir_panel_semanal(rend, vol, ext, ["A", "B"]))
    fin = p["fecha_objetivo"].sort_values().iloc[len(p) // 2]
    tr, va, _ = pv.separar(p, cols, fin, p["fecha_objetivo"].max(), "rv_objetivo")
    assert tr["fecha_objetivo"].max() <= fin < va["fecha_objetivo"].min()


def test_har_recupera_coeficientes_y_smearing():
    rng = np.random.default_rng(3)
    n = 400
    X = rng.normal(size=(n, 3))
    y = 0.5 + X @ np.array([0.4, 0.3, 0.1]) + rng.normal(0, 0.2, n)
    df = pd.DataFrame(X, columns=pv.VARIABLES_HAR)
    df["log_rv_objetivo"] = y
    df["empresa"] = "A"
    pred, coefs = ej.har(df.iloc[:300], df.iloc[300:])
    assert coefs.loc[0, "beta_log_rv_sem"] == pytest.approx(0.4, abs=0.05)
    # Smearing ~ E[exp(e)] = exp(sigma^2 / 2) con sigma = 0.2.
    assert coefs.loc[0, "smearing"] == pytest.approx(np.exp(0.02), abs=0.02)
    assert (pred > 0).all()


def test_referencias_en_semana_que_cruza_la_frontera():
    """La semana objetivo empieza con días de la historia (fin de historia a
    mitad de semana): EWMA y GARCH deben usar el origen correcto (DEC-035)."""
    from src.econometrics import garch

    rng = np.random.default_rng(8)
    fechas = pd.bdate_range("2022-01-03", periods=700)
    r = pd.DataFrame({"A": rng.normal(0, 0.01, 700)}, index=fechas)
    fin_historia = pd.Timestamp("2024-09-03")             # martes
    origen = pd.Timestamp("2024-08-30")                   # viernes anterior
    valid = pd.DataFrame({"empresa": ["A"], "ultimo_dia": [origen], "n_dias_objetivo": [5]})
    ewma, garch_pred = ej.referencias_diarias(r, valid, fin_historia)

    serie = r["A"]
    y = serie.to_numpy() * 100
    tr = serie[serie.index <= fin_historia]
    h = np.empty(len(y))
    h[0] = float((tr * 100).var(ddof=1))
    for t in range(1, len(y)):
        h[t] = 0.94 * h[t - 1] + 0.06 * y[t - 1] ** 2
    i = serie.index.get_loc(origen)
    assert ewma.iloc[0] == pytest.approx(h[i + 1] * 5)

    res = garch.ajustar_garch(tr, serie[serie.index > fin_historia], "t")
    esperado = res.forecast(horizon=5, start=i, reindex=False).variance.iloc[0].sum()
    assert garch_pred.iloc[0] == pytest.approx(esperado)
