"""Pruebas de las Fases 12–13 (DEC-031): optimizadores con restricciones e IBR."""

import numpy as np
import pandas as pd
import pytest

from src.data.externos import cargar_ibr, ibr_efectiva_anual
from src.optimizacion import optimizadores as opt

SECT = {"A": "fin", "B": "fin", "C": "energia", "D": "otro"}


def _cov(vols, rho=0.0):
    v = np.asarray(vols, float)
    c = np.full((len(v), len(v)), rho)
    np.fill_diagonal(c, 1.0)
    act = list("ABCD")[:len(v)]
    return pd.DataFrame(np.outer(v, v) * c, index=act, columns=act)


def test_minima_varianza_dos_activos_formula_cerrada():
    cov = _cov([0.2, 0.3], rho=0.25)
    r = opt.Restricciones(["A", "B"], 1.0)
    w = opt.minima_varianza(cov, r)
    s1, s2, s12 = 0.04, 0.09, 0.25 * 0.2 * 0.3
    esperado = (s2 - s12) / (s1 + s2 - 2 * s12)
    assert w["A"] == pytest.approx(esperado, abs=1e-5)


def test_restricciones_se_respetan_y_limite_sectorial_activo():
    cov = _cov([0.1, 0.12, 0.3, 0.35])          # A y B (financiero) son los menos volátiles
    r = opt.Restricciones(list("ABCD"), 0.45, SECT, 0.40)
    w = opt.minima_varianza(cov, r)
    assert w.sum() == pytest.approx(1.0) and (w >= -1e-9).all() and (w <= 0.45 + 1e-6).all()
    assert w["A"] + w["B"] == pytest.approx(0.40, abs=1e-5)     # el límite es activo
    sin = opt.minima_varianza(cov, opt.Restricciones(list("ABCD"), 0.45))
    assert sin["A"] + sin["B"] > 0.40


def test_restricciones_infactibles_fallan():
    with pytest.raises(ValueError):
        opt.Restricciones(list("ABC"), 0.30)                     # 3 x 0.30 < 1
    with pytest.raises(ValueError):
        opt.Restricciones(["A", "Z"], 0.6, SECT, 0.4)            # Z sin sector
    r = opt.Restricciones(["A", "B", "C"], 0.5, SECT, 0.2)       # fin<=0.2 y C<=0.5: suma < 1
    with pytest.raises(ValueError):
        r.punto_inicial()


def test_paridad_riesgo_con_covarianza_diagonal_es_inversa_de_vol():
    vols = [0.1, 0.2, 0.4]
    cov = _cov(vols)
    w = opt.paridad_riesgo(cov, opt.Restricciones(list("ABC"), 1.0))
    inv = 1 / np.array(vols)
    np.testing.assert_allclose(w.to_numpy(), inv / inv.sum(), atol=1e-4)
    np.testing.assert_allclose(opt.contribuciones_riesgo(w.to_numpy(), cov), 1 / 3, atol=1e-4)


def test_minimo_cvar_coincide_con_busqueda_exhaustiva():
    rng = np.random.default_rng(1)
    esc = pd.DataFrame({"A": rng.standard_t(4, 400) * 0.01,
                        "B": rng.standard_t(4, 400) * 0.02 + 0.001})
    w = opt.minimo_cvar(esc, 0.95, opt.Restricciones(["A", "B"], 1.0))

    def cvar(a):                                  # forma de Rockafellar-Uryasev
        perdida = -(a * esc["A"] + (1 - a) * esc["B"]).to_numpy()
        return min(z + np.maximum(perdida - z, 0).mean() / 0.05 for z in np.sort(perdida))

    grilla = np.linspace(0, 1, 201)
    mejor = grilla[np.argmin([cvar(a) for a in grilla])]
    assert w["A"] == pytest.approx(mejor, abs=0.01)
    assert cvar(w["A"]) <= min(cvar(a) for a in grilla) + 1e-9


def test_maximo_retorno_respeta_volatilidad():
    cov = _cov([0.1, 0.2, 0.3], rho=0.2)
    mu = pd.Series([0.02, 0.06, 0.12], index=list("ABC"))
    r = opt.Restricciones(list("ABC"), 1.0)
    w = opt.maximo_retorno(mu, cov, 0.15, r)
    vol = np.sqrt(w.to_numpy() @ cov.to_numpy() @ w.to_numpy())
    assert vol <= 0.15 + 1e-6
    assert float(w @ mu) >= float(opt.minima_varianza(cov, r) @ mu)
    with pytest.raises(ValueError):
        opt.maximo_retorno(mu, cov, 0.01, r)                       # menor que la vol mínima


def test_maximo_sharpe_mejora_al_1n():
    cov = _cov([0.15, 0.2, 0.25], rho=0.3)
    mu = pd.Series([0.05, 0.10, 0.08], index=list("ABC"))
    r = opt.Restricciones(list("ABC"), 0.6)
    w = opt.maximo_sharpe(mu, cov, 0.03, r).to_numpy()
    sharpe = lambda x: (x @ mu.to_numpy() - 0.03) / np.sqrt(x @ cov.to_numpy() @ x)
    assert sharpe(w) >= sharpe(np.full(3, 1 / 3)) - 1e-9


def test_ibr_efectiva_y_carga(tmp_path, monkeypatch):
    assert ibr_efectiva_anual(np.array([0.0]))[0] == 0.0
    assert ibr_efectiva_anual(np.array([10.0]))[0] == pytest.approx((1 + 0.1 / 360) ** 365 - 1)
    archivo = tmp_path / "ibr.csv"
    archivo.write_text(
        '"Periodo(MMM DD, AAAA)","Indicador Bancario de Referencia (IBR) overnight, nominal","x"\n'
        '"2019/12/31",4.2,\n"2020/01/02",4.25,\n"2020/01/03",4.26,\n"2026/09/15",9.0,\n',
        encoding="utf-8-sig")
    ibr = cargar_ibr(archivo)
    # Recortado a [FECHA_INICIO, FECHA_FIN): sin 2019-12-31 ni 2026-09-15.
    assert list(ibr.index.strftime("%Y-%m-%d")) == ["2020-01-02", "2020-01-03"]
    assert ibr.iloc[:, 0].tolist() == [4.25, 4.26]
