"""Pruebas de la Fase 15 (DEC-034): regla de fechas sospechosas y seguros del
modo final. Ninguna de estas pruebas abre el bloque de prueba."""

import numpy as np
import pandas as pd
import pytest

from src import evaluacion_final as ef
from src.preprocessing.invalid_data import (
    detectar_reversiones_simultaneas,
    invalidar_fechas_rendimientos,
)


@pytest.fixture
def rend():
    idx = pd.bdate_range("2025-02-17", periods=6)
    r = pd.DataFrame(0.001, index=idx, columns=list("ABC"))
    # 2025-02-19: A y B saltan y revierten al día siguiente; C no.
    r.loc["2025-02-19", ["A", "B"]] = [0.20, -0.10]
    r.loc["2025-02-20", ["A", "B"]] = [-0.19, 0.095]
    # 2025-02-21: solo C salta y revierte (una acción: no cuenta).
    r.loc["2025-02-21", "C"] = 0.08
    r.loc["2025-02-24", "C"] = -0.08
    return r


def test_detecta_solo_dias_con_dos_o_mas_acciones(rend):
    d = detectar_reversiones_simultaneas(rend)
    assert list(d["fecha"].dt.strftime("%Y-%m-%d")) == ["2025-02-19"]
    assert d.loc[0, "acciones"] == "A, B" and d.loc[0, "n_acciones"] == 2


def test_no_detecta_saltos_que_no_revierten(rend):
    r = rend.copy()
    r.loc["2025-02-20", ["A", "B"]] = [0.01, 0.01]
    assert detectar_reversiones_simultaneas(r).empty


def test_invalidacion_aplica_dec022_a_todas_las_acciones(rend):
    vol = pd.DataFrame(100.0, index=rend.index, columns=rend.columns)
    r, v = invalidar_fechas_rendimientos(rend, vol, [pd.Timestamp("2025-02-19")])
    assert r.loc["2025-02-19"].isna().all()                      # las 3, no solo A y B
    np.testing.assert_allclose(r.loc["2025-02-20"],
                               rend.loc["2025-02-19"] + rend.loc["2025-02-20"])
    assert v.loc["2025-02-19"].isna().all()
    # El rendimiento acumulado se conserva: no se inventa ni se pierde nada.
    np.testing.assert_allclose(r.sum(), rend.sum())


def test_invalidacion_rechaza_fechas_inexistentes(rend):
    with pytest.raises(ValueError):
        invalidar_fechas_rendimientos(rend, rend, [pd.Timestamp("2025-03-30")])


def test_modo_final_exige_ensayo_que_reproduzca(tmp_path, monkeypatch):
    monkeypatch.setattr(ef, "RUTA_FASE15", tmp_path)
    abiertos = []
    monkeypatch.setattr(ef, "cargar_bloques", lambda modo: abiertos.append(modo))
    with pytest.raises(RuntimeError, match="no se abre"):
        ef.ejecutar("final")                                        # sin ensayo
    (tmp_path / "ensayo").mkdir()
    pd.DataFrame({"reproduce": [True, False]}).to_csv(tmp_path / "ensayo" / "reproduccion.csv")
    with pytest.raises(RuntimeError):
        ef.ejecutar("final")                                        # ensayo que no reprodujo
    assert abiertos == []                                           # nunca se cargó la prueba


def test_modo_final_se_ejecuta_una_sola_vez(tmp_path, monkeypatch):
    monkeypatch.setattr(ef, "RUTA_FASE15", tmp_path)
    monkeypatch.setattr(ef, "cargar_bloques", lambda modo: pytest.fail("no debía abrir la prueba"))
    (tmp_path / "ensayo").mkdir()
    pd.DataFrame({"reproduce": [True]}).to_csv(tmp_path / "ensayo" / "reproduccion.csv")
    (tmp_path / "final").mkdir()
    (tmp_path / "final" / "algo.csv").write_text("x")
    with pytest.raises(FileExistsError):
        ef.ejecutar("final")
