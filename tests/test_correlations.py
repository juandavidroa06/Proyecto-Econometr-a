"""Pruebas de la matriz de correlación."""

from src.exploratory_analysis.correlations import matriz_correlacion


def test_matriz_correlacion_dimensiones_9x9(df_renderimientos_sintetico):
    m = matriz_correlacion(df_renderimientos_sintetico)
    assert m.shape == (9, 9)


def test_matriz_correlacion_valores_en_rango(df_renderimientos_sintetico):
    m = matriz_correlacion(df_renderimientos_sintetico)
    assert (m.values >= -1).all() and (m.values <= 1).all()


def test_diagonal_unos(df_renderimientos_sintetico):
    m = matriz_correlacion(df_renderimientos_sintetico)
    import numpy as np
    assert np.allclose(np.diag(m.values), 1.0)