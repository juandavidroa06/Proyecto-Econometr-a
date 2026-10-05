"""Pruebas de la Fase 16 (DEC-037/038). No abren el bloque de prueba."""

import numpy as np
import pandas as pd
import pytest

from src import evaluacion_final as ef
from src.optimizacion import optimizadores as opt
from src.robustez import fase16


def test_muestra_completa_exige_evaluacion_final_hecha(tmp_path, monkeypatch):
    monkeypatch.setattr(ef, "RUTA_FASE15", tmp_path)
    monkeypatch.setattr(ef, "cargar_bloques", lambda modo: pytest.fail("no debía abrir la prueba"))
    with pytest.raises(RuntimeError, match="aún no se ha hecho"):
        ef.cargar_muestra_completa()


def test_rejilla_de_robustez_registrada():
    assert fase16.VENTANAS == (126, 252, 504)
    assert fase16.PESOS_MAX == (0.20, 0.30, 0.50)
    assert fase16.LAMBDAS == (0.90, 0.94, 0.97)
    assert fase16.ANIOS == [2021, 2022, 2023, 2024, 2025, 2026]


def test_configuracion_infactible_se_detecta():
    # 4 acciones con máximo 20 % no pueden sumar 1: R1 la omite y la registra.
    with pytest.raises(ValueError):
        opt.Restricciones(list("ABCD"), 0.20)


def test_r2_un_anio_no_depende_de_anios_posteriores():
    rng = np.random.default_rng(16)
    idx = pd.bdate_range("2020-01-01", "2026-09-14")
    r = pd.DataFrame({"A": rng.standard_t(5, len(idx)) * 0.01}, index=idx)
    _, var1, perd1 = fase16.r2_volatilidad({"rendimientos_log": r}, ["A"])
    r2 = r.copy()
    r2.loc[r2.index >= "2023-01-01"] *= 4
    _, var2, perd2 = fase16.r2_volatilidad({"rendimientos_log": r2}, ["A"])
    a = perd1[perd1["anio"] <= 2022].reset_index(drop=True)
    b = perd2[perd2["anio"] <= 2022].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b)
    pd.testing.assert_frame_equal(var1[var1["anio"] <= 2022].reset_index(drop=True),
                                  var2[var2["anio"] <= 2022].reset_index(drop=True))
    assert set(perd1["anio"]) == set(fase16.ANIOS)
