"""Pruebas de la Fase 8 (DEC-025): variables sin información futura y CV temporal."""

import numpy as np
import pandas as pd
import pytest

from src.machine_learning import modelos, variables


@pytest.fixture
def datos():
    rng = np.random.default_rng(3)
    fechas = pd.bdate_range("2023-01-02", periods=160)
    rend = pd.DataFrame(rng.normal(0, 0.01, (160, 2)), index=fechas, columns=["A", "B"])
    vol = pd.DataFrame(rng.integers(100, 1000, (160, 2)).astype(float),
                       index=fechas, columns=["A", "B"])
    # Externas en su propio calendario (incluye un sábado que la BVC no tiene).
    f_ext = fechas.union(pd.DatetimeIndex(["2023-03-04"]))
    ext = pd.DataFrame({"TRM": 4000 * np.exp(np.cumsum(rng.normal(0, 0.005, len(f_ext)))),
                        "Brent": 80 * np.exp(np.cumsum(rng.normal(0, 0.01, len(f_ext))))},
                       index=f_ext)
    return rend, vol, ext


def test_objetivo_es_el_rendimiento_siguiente(datos):
    rend, vol, ext = datos
    panel = variables.construir_panel(rend, vol, ext)
    fila = panel[(panel["empresa"] == "A") & (panel["Date"] == rend.index[50])].iloc[0]
    assert fila["objetivo"] == rend["A"].iloc[51]
    assert fila["fecha_objetivo"] == rend.index[51]
    assert fila["r_lag0"] == rend["A"].iloc[50]


def test_variables_no_cambian_al_alterar_el_futuro(datos):
    rend, vol, ext = datos
    corte = rend.index[100]
    base = variables.construir_panel(rend, vol, ext)
    rend2, vol2, ext2 = rend.copy(), vol.copy(), ext.copy()
    rend2.loc[rend2.index > corte] += 0.5
    vol2.loc[vol2.index > corte] *= 10
    ext2.loc[ext2.index >= corte] *= 3      # externas del MISMO día t también
    otro = variables.construir_panel(rend2, vol2, ext2)
    cols = variables.columnas_variables(base)
    hasta = base["Date"] <= corte
    pd.testing.assert_frame_equal(base.loc[hasta, cols], otro.loc[hasta, cols])


def test_externas_usan_fecha_estrictamente_anterior(datos):
    _, _, ext = datos
    fechas = pd.DatetimeIndex(["2023-03-06"])    # lunes; hubo dato el sábado 4
    v = variables.variables_externas(ext, fechas)
    r = np.log(ext["TRM"]).diff()
    assert v.loc["2023-03-06", "TRM_r1"] == pytest.approx(r.loc["2023-03-04"])


def test_externas_sin_dato_reciente_quedan_nan():
    ext = pd.DataFrame({"TRM": [4000.0, 4010.0, 4020.0]},
                       index=pd.to_datetime(["2023-01-02", "2023-01-03", "2023-01-04"]))
    v = variables.variables_externas(ext, pd.DatetimeIndex(["2023-02-01"]))
    assert np.isnan(v.loc["2023-02-01", "TRM_r1"])


def test_separar_por_fecha_objetivo(datos):
    rend, vol, ext = datos
    panel = variables.construir_panel(rend, vol, ext)
    fin_train, fin_val = rend.index[99], rend.index[159]
    train, valid, resumen = variables.separar(panel, fin_train, fin_val)
    assert train["fecha_objetivo"].max() <= fin_train
    assert valid["fecha_objetivo"].min() > fin_train
    # La fila con origen = último día de train va a validación (su objetivo es posterior).
    assert (valid["Date"] == fin_train).any()
    assert not train[variables.columnas_variables(panel) + ["objetivo"]].isna().any().any()
    assert set(resumen["bloque"]) == {"train", "validacion"}


def test_pliegues_por_fecha_sin_solape():
    fechas = pd.Series(np.repeat(pd.bdate_range("2023-01-02", periods=60), 3))
    for idx_tr, idx_te in modelos.pliegues_por_fecha(fechas, 4):
        f_tr, f_te = fechas.iloc[idx_tr], fechas.iloc[idx_te]
        assert f_tr.max() < f_te.min()
        assert set(f_tr).isdisjoint(set(f_te))
        # Todas las filas de una fecha de prueba están en la prueba.
        assert len(idx_te) == 3 * f_te.nunique()


def test_validacion_cruzada_reproducible(datos):
    rend, vol, ext = datos
    panel = variables.construir_panel(rend, vol, ext)
    train, _, _ = variables.separar(panel, rend.index[119], rend.index[159])
    X = train[variables.columnas_variables(panel)]
    a, tabla_a = modelos.validacion_cruzada("gradient_boosting", X, train["objetivo"],
                                            train["Date"], n_pliegues=3)
    b, tabla_b = modelos.validacion_cruzada("gradient_boosting", X, train["objetivo"],
                                            train["Date"], n_pliegues=3)
    assert a == b
    pd.testing.assert_frame_equal(tabla_a, tabla_b)
    assert len(tabla_a) == 8


def test_validacion_cruzada_rechaza_faltantes():
    X = pd.DataFrame({"x": [1.0, np.nan] * 20})
    with pytest.raises(ValueError):
        modelos.validacion_cruzada("random_forest", X, pd.Series(np.zeros(40)),
                                   pd.Series(pd.bdate_range("2023-01-02", periods=40)))
