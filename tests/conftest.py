"""
conftest.py — Configuración y fixtures para pytest.

Asegura que la raíz del proyecto esté en sys.path para que los tests
puedan importar los paquetes ``config`` y ``src``.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


@pytest.fixture
def serie_precios():
    """Serie de precios sintética ordenada cronológicamente."""
    fechas = pd.date_range("2020-01-01", periods=30, freq="B")
    return pd.Series(np.linspace(100, 130, 30), index=fechas)


@pytest.fixture
def df_precios_sintetico():
    """DataFrame de precios de 9 activos (para pruebas de correlación)."""
    fechas = pd.date_range("2020-01-01", periods=100, freq="B")
    rng = np.random.default_rng(42)
    data = {
        f"Activo_{i}": 100 * (1 + rng.normal(0, 0.01, len(fechas))).cumprod()
        for i in range(9)
    }
    return pd.DataFrame(data, index=fechas)


@pytest.fixture
def df_renderimientos_sintetico(df_precios_sintetico):
    """Rendimientos logarítmicos sintéticos de 9 activos."""
    return np.log(df_precios_sintetico / df_precios_sintetico.shift(1))