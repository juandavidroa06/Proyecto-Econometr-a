"""Pruebas del comparador de src/reproducir.py (no reejecutan fases)."""

import numpy as np
import pandas as pd

from src.reproducir import comparar


def test_vacios_en_texto_reproducen():
    a = pd.DataFrame({"avisos": ["no convergió", np.nan], "x": [1.0, 2.0]})
    assert comparar(a, a.copy())[0]


def test_texto_distinto_no_reproduce():
    a = pd.DataFrame({"avisos": ["si", np.nan]})
    b = pd.DataFrame({"avisos": ["no", np.nan]})
    ok, _, motivo = comparar(a, b)
    assert not ok and "avisos" in motivo


def test_diferencia_numerica_sobre_tolerancia():
    a = pd.DataFrame({"x": [1.0, 2.0]})
    assert comparar(a + 1e-9, a)[0]
    assert not comparar(a + 1e-3, a)[0]
