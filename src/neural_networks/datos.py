"""
datos.py — Preparación de datos para redes neuronales (Fase 9, DEC-026)
========================================================================

Responsabilidad única: escalar variables y construir secuencias, sin
información futura.

    - El escalador (media y desviación) se ajusta SOLO con las filas de
      entrenamiento y se aplica igual a validación.
    - Una secuencia de origen t contiene los ``longitud`` días de la empresa
      que terminan en t (fechas <= t). Si algún día de la ventana tiene
      faltantes, la secuencia se descarta (se cuenta; no se imputa).
"""

import numpy as np
import pandas as pd

# Variables diarias que alimentan la LSTM (una por paso de tiempo).
VARIABLES_SECUENCIA = ["r_lag0", "log_volumen_rel", "mercado_r0", "TRM_r1", "Brent_r1"]


class Escalador:
    """Estandarización z = (x - media) / desv ajustada solo con train."""

    def __init__(self):
        self.media_ = None
        self.desv_ = None

    def ajustar(self, X):
        if not isinstance(X, pd.DataFrame):
            raise TypeError("Se esperaba un DataFrame.")
        if X.isna().any().any():
            raise ValueError("No se puede ajustar el escalador con faltantes.")
        self.media_ = X.mean()
        desv = X.std(ddof=0)
        # Columnas constantes (p. ej. indicadores de empresa) no se escalan.
        self.desv_ = desv.where(desv > 0, 1.0)
        return self

    def transformar(self, X):
        if self.media_ is None:
            raise RuntimeError("El escalador no está ajustado.")
        if list(X.columns) != list(self.media_.index):
            raise ValueError("Las columnas no coinciden con las del ajuste.")
        return (X - self.media_) / self.desv_


def secuencias(panel, filas, longitud=30, variables=VARIABLES_SECUENCIA):
    """Arreglo (n, longitud, n_variables) para cada fila (Date, empresa).

    ``panel``: panel completo (todas las fechas disponibles de train y
    validación). ``filas``: DataFrame con columnas Date y empresa (las filas
    de origen). Retorna (X, mascara) donde ``mascara`` indica qué filas
    tienen secuencia completa; X solo contiene esas filas.
    """
    faltan = [v for v in variables if v not in panel.columns]
    if faltan:
        raise ValueError(f"Faltan variables en el panel: {faltan}")
    salida, mascara = [], []
    por_empresa = {e: g.set_index("Date").sort_index()[variables]
                   for e, g in panel.groupby("empresa")}
    for fecha, empresa in zip(filas["Date"], filas["empresa"]):
        datos = por_empresa[empresa]
        pos = datos.index.get_loc(fecha)
        if pos + 1 < longitud:
            mascara.append(False)
            continue
        ventana = datos.iloc[pos + 1 - longitud:pos + 1].to_numpy(dtype=float)
        if np.isnan(ventana).any():
            mascara.append(False)
            continue
        salida.append(ventana)
        mascara.append(True)
    X = (np.stack(salida) if salida
         else np.empty((0, longitud, len(variables))))
    return X, np.array(mascara, dtype=bool)


def escalar_secuencias(X, media, desv):
    """Escala cada variable de la secuencia con media/desv de train."""
    desv = np.where(desv > 0, desv, 1.0)
    return (X - media.reshape(1, 1, -1)) / desv.reshape(1, 1, -1)


def separar_interno(fechas_objetivo, fraccion=0.2):
    """Máscaras (ajuste, parada) dentro de train: el último ``fraccion`` de
    fechas objetivo sirve para elegir hiperparámetros y parar temprano."""
    fechas = pd.Series(pd.to_datetime(fechas_objetivo)).reset_index(drop=True)
    unicas = np.sort(fechas.unique())
    corte = unicas[int(len(unicas) * (1 - fraccion)) - 1]
    ajuste = (fechas <= corte).to_numpy()
    return ajuste, ~ajuste
