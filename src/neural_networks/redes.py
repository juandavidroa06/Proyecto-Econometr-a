"""
redes.py — MLP y LSTM en PyTorch (Fase 9, DEC-026)
===================================================

Responsabilidad única: definir las redes y entrenarlas de forma
reproducible.

    - Pérdida MSE, optimizador Adam, minilotes en orden aleatorio con
      semilla fija.
    - Parada temprana con un conjunto de PARADA tomado del final de
      entrenamiento (nunca validación); se restauran los mejores pesos.
    - Objetivo en % (x 100) para estabilidad numérica; las predicciones se
      devuelven en la escala original.
"""

import copy

import numpy as np
import torch
from torch import nn

ESCALA_OBJETIVO = 100.0


def fijar_semilla(semilla):
    np.random.seed(semilla)
    torch.manual_seed(semilla)
    torch.use_deterministic_algorithms(True)


class MLP(nn.Module):
    def __init__(self, n_entradas, ocultas=(32,), abandono=0.2):
        super().__init__()
        capas, previo = [], n_entradas
        for n in ocultas:
            capas += [nn.Linear(previo, n), nn.ReLU(), nn.Dropout(abandono)]
            previo = n
        capas.append(nn.Linear(previo, 1))
        self.red = nn.Sequential(*capas)

    def forward(self, x):
        return self.red(x).squeeze(-1)


class LSTMRed(nn.Module):
    """LSTM de una capa sobre la secuencia + indicadores de empresa al final."""

    def __init__(self, n_variables, n_estaticas, oculta=16, abandono=0.2):
        super().__init__()
        self.lstm = nn.LSTM(n_variables, oculta, batch_first=True)
        self.salida = nn.Sequential(nn.Dropout(abandono),
                                    nn.Linear(oculta + n_estaticas, 1))

    def forward(self, x):
        secuencia, estaticas = x
        _, (h, _) = self.lstm(secuencia)
        return self.salida(torch.cat([h[-1], estaticas], dim=1)).squeeze(-1)


def _tensores(X):
    if isinstance(X, tuple):
        return tuple(torch.as_tensor(np.asarray(x), dtype=torch.float32) for x in X)
    return torch.as_tensor(np.asarray(X), dtype=torch.float32)


def _lote(X, idx):
    return tuple(x[idx] for x in X) if isinstance(X, tuple) else X[idx]


def _n(X):
    return len(X[0]) if isinstance(X, tuple) else len(X)


def entrenar(crear_red, X, y, X_parada=None, y_parada=None, semilla=42,
             epocas=200, paciencia=15, tam_lote=256, tasa=1e-3, decaimiento=1e-4):
    """Entrena la red. Con conjunto de parada, se detiene cuando su MSE no
    mejora en ``paciencia`` épocas y restaura los mejores pesos.

    Retorna (red, historia) con la época óptima y el MSE de parada.
    """
    fijar_semilla(semilla)
    red = crear_red()
    X, y = _tensores(X), torch.as_tensor(np.asarray(y) * ESCALA_OBJETIVO,
                                         dtype=torch.float32)
    if not torch.isfinite(y).all():
        raise ValueError("El objetivo tiene valores no finitos.")
    usar_parada = X_parada is not None
    if usar_parada:
        X_p = _tensores(X_parada)
        y_p = torch.as_tensor(np.asarray(y_parada) * ESCALA_OBJETIVO, dtype=torch.float32)
    optimizador = torch.optim.Adam(red.parameters(), lr=tasa, weight_decay=decaimiento)
    perdida = nn.MSELoss()
    generador = torch.Generator().manual_seed(semilla)
    mejor, mejor_estado, mejor_epoca, sin_mejora = np.inf, None, epocas, 0
    for epoca in range(1, epocas + 1):
        red.train()
        orden = torch.randperm(_n(X), generator=generador)
        for i in range(0, _n(X), tam_lote):
            idx = orden[i:i + tam_lote]
            optimizador.zero_grad()
            perdida(red(_lote(X, idx)), y[idx]).backward()
            optimizador.step()
        if usar_parada:
            red.eval()
            with torch.no_grad():
                mse = float(perdida(red(X_p), y_p))
            if mse < mejor - 1e-9:
                mejor, mejor_estado, mejor_epoca, sin_mejora = (
                    mse, copy.deepcopy(red.state_dict()), epoca, 0)
            else:
                sin_mejora += 1
                if sin_mejora >= paciencia:
                    break
    if usar_parada:
        red.load_state_dict(mejor_estado)
    return red, {"epoca_optima": mejor_epoca,
                 "mse_parada": mejor / ESCALA_OBJETIVO ** 2 if usar_parada else np.nan}


def predecir(red, X):
    red.eval()
    with torch.no_grad():
        return red(_tensores(X)).numpy().astype(float) / ESCALA_OBJETIVO
