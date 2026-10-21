"""Pruebas de la Fase 21 (DEC-046): inferencia adicional con datos simulados."""

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from src.extensiones import inferencia as inf


def test_varianza_largo_plazo_sin_rezagos_es_la_varianza():
    x = np.random.default_rng(0).normal(size=200)
    assert inf.varianza_largo_plazo(x, rezago=0) == pytest.approx(x.var())
    assert inf.rezago_newey_west(100) == 4
    with pytest.raises(ValueError):
        inf.varianza_largo_plazo([1.0, np.nan, 2.0])


def test_bootstrap_estacionario_forma_rango_y_bloques():
    idx = inf.bootstrap_estacionario(100, 400, 10, semilla=1)
    assert idx.shape == (400, 100) and idx.min() >= 0 and idx.max() < 100
    assert np.array_equal(idx, inf.bootstrap_estacionario(100, 400, 10, semilla=1))
    continua = (idx[:, 1:] == (idx[:, :-1] + 1) % 100).mean()
    assert continua == pytest.approx(0.9, abs=0.02)        # 1 - 1/bloque_medio


def test_spa_detecta_un_modelo_mejor_y_no_inventa_mejoras():
    rng = np.random.default_rng(2)
    n = 250
    ref = pd.Series(rng.normal(1.0, 0.3, n))
    iguales = pd.DataFrame({f"m{k}": ref + rng.normal(0, 0.3, n) for k in range(3)})
    peores = iguales + 0.2
    r = inf.prueba_spa(ref, peores, n_remuestras=1000, semilla=3)
    assert r["pvalor_spa_consistente"] > 0.5 and r["pvalor_reality_check"] > 0.5
    mejor = peores.copy()
    mejor["bueno"] = ref - 0.15
    r2 = inf.prueba_spa(ref, mejor, n_remuestras=1000, semilla=3)
    assert r2["pvalor_spa_consistente"] < 0.01
    assert r2["modelos"].iloc[0]["modelo"] == "bueno"
    # Agregar modelos malos no debe destruir la potencia del SPA (sí la del RC).
    assert r2["pvalor_spa_consistente"] <= r2["pvalor_spa_superior"] + 1e-12


def test_spa_valida_entradas():
    ref = pd.Series(np.ones(20))
    with pytest.raises(ValueError):
        inf.prueba_spa(ref, pd.DataFrame({"a": np.ones(20)}, index=range(1, 21)))
    with pytest.raises(ValueError):
        inf.prueba_spa(ref, pd.DataFrame({"a": [np.nan] * 20}))


def _panel_direccional(rng, n_fechas, n_acciones, habilidad, comun):
    """Rendimientos y pronósticos con un choque común por día en cada uno,
    independientes entre sí salvo por ``habilidad``."""
    fechas = np.repeat(pd.bdate_range("2024-01-01", periods=n_fechas), n_acciones)
    choque_y = np.repeat(rng.normal(size=n_fechas), n_acciones)
    choque_f = np.repeat(rng.normal(size=n_fechas), n_acciones)
    y = comun * choque_y + rng.normal(size=n_fechas * n_acciones)
    f = habilidad * y + comun * choque_f + rng.normal(size=n_fechas * n_acciones)
    return fechas, y, f


def test_direccional_hac_controla_el_error_con_dependencia_comun():
    from src.comparacion.estadistica import pesaran_timmermann
    rng = np.random.default_rng(4)
    # Sin habilidad pero con choques comunes a las acciones del mismo día: la
    # prueba original (filas independientes) rechaza de más; la HAC se acerca al 5 %.
    rechazos_pt, rechazos_hac, R = 0, 0, 200
    for _ in range(R):
        fechas, y, f = _panel_direccional(rng, 120, 9, habilidad=0.0, comun=1.5)
        rechazos_pt += pesaran_timmermann(y, f)["pt_pvalor"] < 0.05
        rechazos_hac += inf.direccional_hac(fechas, y, f)["pvalor"] < 0.05
    assert rechazos_pt / R > 0.10                 # nominal: 0,05 (unilateral)
    assert rechazos_hac / R < 0.10 and rechazos_hac < rechazos_pt


def test_direccional_hac_detecta_habilidad_y_maneja_signo_constante():
    rng = np.random.default_rng(5)
    fechas, y, f = _panel_direccional(rng, 200, 9, habilidad=0.8, comun=0.0)
    r = inf.direccional_hac(fechas, y, f)
    assert r["acierto"] > 0.6 and r["pvalor"] < 0.001
    r2 = inf.direccional_hac(fechas, y, np.ones_like(y))
    assert np.isnan(r2["pvalor"])


def test_z2_sin_excesos_vale_uno_y_formula():
    x = np.array([0.01, -0.005, 0.02])
    assert inf.z2(x, [0.05] * 3, [0.06] * 3, 0.05) == pytest.approx(1.0)
    x = np.array([-0.10, 0.0, 0.0, 0.0])
    # Un exceso de -0.10 con ES 0.08 y alfa 0.25: -0.10/0.08/(4*0.25) + 1 = -0.25
    assert inf.z2(x, [0.05] * 4, [0.08] * 4, 0.25) == pytest.approx(-0.25)


def test_acerbi_szekely_bien_calibrado_y_subestimado():
    rng = np.random.default_rng(6)
    T, alfa, sigma = 500, 0.025, 0.01
    z = stats.norm.ppf(alfa)
    var = np.full(T, -z * sigma)
    es = np.full(T, sigma * stats.norm.pdf(z) / alfa)
    simular = lambda g, n: g.normal(0, sigma, (n, T))
    bien = inf.acerbi_szekely_z2(rng.normal(0, sigma, T), var, es, alfa, simular, 2000, 7)
    assert bien["pvalor"] > 0.05 and abs(bien["z2_sim_medio"]) < 0.05
    mal = inf.acerbi_szekely_z2(rng.normal(0, 2 * sigma, T), var, es, alfa, simular, 2000, 7)
    assert mal["pvalor"] < 0.01 and mal["z2"] < 0


def test_sharpe_probabilistico_y_deflactado():
    rng = np.random.default_rng(8)
    bueno = rng.normal(0.002, 0.01, 1000)
    nulo = rng.normal(0.0, 0.01, 1000)
    assert inf.sharpe_probabilistico(bueno) > 0.99
    assert 0.05 < inf.sharpe_probabilistico(nulo - nulo.mean()) < 0.95
    familia = rng.normal(0, 0.05, 10)
    assert inf.umbral_deflactado(familia) > 0
    assert inf.umbral_deflactado(rng.normal(0, 0.05, 100)) > inf.umbral_deflactado(familia[:3])
    assert inf.sharpe_deflactado(bueno, familia) <= inf.sharpe_probabilistico(bueno)


def test_diferencia_sharpe_hac():
    rng = np.random.default_rng(9)
    comun = rng.normal(0, 0.01, 1500)
    a = 0.0005 + comun + rng.normal(0, 0.002, 1500)
    b = comun + rng.normal(0, 0.002, 1500)
    r = inf.diferencia_sharpe_hac(a, b)
    assert r["dif_sharpe"] > 0 and r["pvalor"] < 0.01
    r0 = inf.diferencia_sharpe_hac(b + rng.normal(0, 0.002, 1500), b)
    assert r0["pvalor"] > 0.01
    with pytest.raises(ValueError):
        inf.diferencia_sharpe_hac(a, b[:-1])


# --- Bloque B: portafolios con pronósticos ---------------------------------------------

from src.backtesting import motor
from src.extensiones import portafolios_pronostico as pp


def test_covarianza_ewma_formula_y_lambda_uno():
    idx = pd.bdate_range("2024-01-01", periods=4)
    v = pd.DataFrame({"a": [0.01, -0.02, 0.03, 0.0], "b": [0.0, 0.01, -0.01, 0.02]}, index=idx)
    lam = 0.5
    w = np.array([lam ** 3, lam ** 2, lam, 1.0])
    w /= w.sum()
    esperado = (v.to_numpy() * w[:, None]).T @ v.to_numpy() * 252
    assert np.allclose(pp.covarianza_ewma(v, lam).to_numpy(), esperado)
    casi_uno = pp.covarianza_ewma(v, 0.999999).to_numpy()
    assert np.allclose(casi_uno, v.to_numpy().T @ v.to_numpy() / 4 * 252, rtol=1e-4)
    with pytest.raises(ValueError):
        pp.covarianza_ewma(v.iloc[:3])


def test_exposicion_vol_target():
    rng = np.random.default_rng(10)
    tranquilo = pd.Series(rng.normal(0, 0.01, 600))
    x, s_obj, s_hat = pp.exposicion_vol_target(tranquilo)
    assert 0.7 < x <= 1.0
    agitado = pd.concat([tranquilo, pd.Series(rng.normal(0, 0.05, 15))], ignore_index=True)
    x2, _, s_hat2 = pp.exposicion_vol_target(agitado)
    assert x2 < 0.6 and s_hat2 > s_hat
    with pytest.raises(ValueError):
        pp.exposicion_vol_target(tranquilo.iloc[:100])


def test_motor_sin_costo_cobra_solo_las_acciones():
    idx = pd.bdate_range("2024-01-01", periods=5)
    rend = pd.DataFrame({"a": [0.0, 0.01, 0.0, 0.0, 0.0], "IBR": [0.0] * 5}, index=idx)
    pesos = {idx[0]: pd.Series({"a": 0.5, "IBR": 0.5}), idx[2]: pd.Series({"a": 0.2, "IBR": 0.8})}
    d, _ = motor.simular(rend, pesos, 0.01, idx[-1], sin_costo=("IBR",))
    assert d["costo"].iloc[0] == pytest.approx(0.01 * 0.5)          # compra inicial: solo "a"
    w_a = 0.5 * 1.01 / (1 + 0.005)                                    # deriva tras el día 2
    assert d["costo"].iloc[1] == pytest.approx(0.01 * abs(0.2 - w_a))
    d0, _ = motor.simular(rend, pesos, 0.01, idx[-1])
    assert d0["costo"].iloc[0] == pytest.approx(0.01)                 # comportamiento de DEC-032
    with pytest.raises(ValueError):
        motor.simular(rend, pesos, 0.01, idx[-1], sin_costo=("otro",))


def test_simular_senales_a_mano():
    pron = pd.DataFrame({
        "fecha_objetivo": ["2024-01-02"] * 3 + ["2024-01-03"] * 3,
        "empresa": ["a", "b", "c"] * 2,
        "objetivo": np.log1p([0.02, -0.01, 0.0, 0.01, 0.0, -0.02]),
        "m": [0.3, 0.1, 0.2, 0.1, 0.3, 0.2]})
    neto, rot = pp.simular_senales(pron, "m", 1, 0.0)
    assert neto.iloc[0] == pytest.approx(0.02) and neto.iloc[1] == pytest.approx(0.0)
    assert rot == pytest.approx(2.0)                                   # vende a, compra b
    igual, _ = pp.simular_senales(pron, None, 1, 0.0)
    assert igual.iloc[0] == pytest.approx(np.mean([0.02, -0.01, 0.0]))
    con_costo, _ = pp.simular_senales(pron, "m", 1, 0.01)
    assert con_costo.iloc[0] == pytest.approx(1.02 * 0.99 - 1)


def test_covarianza_ccc_garch_simetrica_y_positiva():
    rng = np.random.default_rng(11)
    idx = pd.bdate_range("2020-01-01", periods=800)
    z = rng.standard_t(6, size=(800, 2)) * 0.01
    rend = pd.DataFrame({"a": z[:, 0], "b": 0.5 * z[:, 0] + z[:, 1]}, index=idx)
    reg = []
    cov = pp.covarianza_ccc_garch(rend, rend.iloc[-252:], reg)
    c = cov.to_numpy()
    assert np.allclose(c, c.T) and (np.linalg.eigvalsh(c) > 0).all()
    corr = c[0, 1] / np.sqrt(c[0, 0] * c[1, 1])
    assert corr == pytest.approx(rend.iloc[-252:].corr().iloc[0, 1])
    assert len(reg) == 2
