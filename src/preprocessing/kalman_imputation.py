"""
kalman_imputation.py — Imputación de valores faltantes con Filtro de Kalman
===========================================================================

Imputa valores faltantes en series de precios usando un **modelo de nivel
local** (local level) estimado por Filtro de Kalman y suavizado (smoothing).

Uso previsto en esta fase:
    - Reconstrucción **retrospectiva** de valores faltantes en series de
      precios (solo se imputa la variable usada para rendimientos: Adj Close).

Principios:
    1. Los datos crudos NO se modifican. La imputación genera valores nuevos
       en otra estructura, preservando siempre el valor original y una bandera
       que indica si el valor fue imputado.
    2. Se trabaja sobre la serie **propia** de cada empresa (índice continuo),
       de modo que solo se imputan los NaN realmente presentes en la fuente.
       NO se imputan los NaN de "alineación" que aparecen al unir fechas de
       varias empresas en un único DataFrame ancho.

Método:
    - Se ajusta el log-precio con un modelo de estado de nivel local:
          y_t  = mu_t + eps_t
          mu_t = mu_{t-1} + eta_t
      usando ``statsmodels.tsa.statespace``.
    - El suavizador de Kalman reconstruye los valores faltantes combinando
      información anterior y posterior al faltante.

ADVERTENCIA METODOLÓGICA (importante para fases futuras):
    El suavizado (smoothing) utiliza información **posterior** al valor
    faltante. Por ello es válido para reconstrucción histórica, pero NO debe
    usarse directamente como información disponible en tiempo real para
    backtesting o predicción sin adaptar el procedimiento (sería data leakage).
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def detectar_faltantes(serie):
    """Devuelve una máscara booleana de las posiciones con NaN.

    Parámetros:
        serie: pd.Series de precios (índice = fechas).

    Retorna:
        pd.Series booleana alineada al índice, True donde hay NaN.
    """
    return serie.isna()


def _ajustar_y_suavizar(serie):
    """Ajusta el modelo local level en log-precios y devuelve la serie suavizada.

    Retorna la serie de precios suavizada (ya en escala original).
    """
    from statsmodels.tsa.statespace.structural import UnobservedComponents

    log_precio = np.log(serie.astype(float))
    modelo = UnobservedComponents(log_precio, level="local level")
    resultado = modelo.fit(disp=False)
    # El estado suavizado (nivel) en escala logarítmica.
    nivel_log = resultado.smoothed_state[0]
    suavizado_log = pd.Series(nivel_log, index=serie.index)
    return np.exp(suavizado_log)


def imputar_serie(serie):
    """Imputa los NaN de una serie de precios mediante suavizado de Kalman.

    Parámetros:
        serie: pd.Series de precios con índice cronológico continuo.

    Retorna:
        (serie_imputada, bandera_imputado) donde:
        - serie_imputada: conserva los valores observados originales y rellena
          solo las posiciones NaN con la estimación suavizada.
        - bandera_imputado: pd.Series booleana, True donde el valor fue imputado.
    """
    serie = serie.copy()
    faltantes = detectar_faltantes(serie)
    bandera = pd.Series(False, index=serie.index)

    if not faltantes.any():
        return serie, bandera

    # Se requieren al menos 3 observaciones para estimar el modelo.
    if serie.notna().sum() < 3:
        logger.warning("Serie con menos de 3 observaciones válidas; no se imputa.")
        return serie, bandera

    try:
        suavizada = _ajustar_y_suavizar(serie)
        serie_imputada = serie.where(~faltantes, suavizada)
        bandera = faltantes.copy()
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo imputar con Kalman (%s). Se conservan NaN.", exc)
        # No se inventan valores: se mantienen los NaN originales.
        return serie, bandera

    return serie_imputada, bandera


def imputar_series_multiples(series_por_activo):
    """Imputa un diccionario {activo: Serie}.

    Retorna:
        (imputadas, banderas, reporte) donde:
        - imputadas: dict {activo: Serie imputada}.
        - banderas: dict {activo: Serie booleana}.
        - reporte: pd.DataFrame (largo) de las imputaciones realizadas.
    """
    imputadas = {}
    banderas = {}
    registros = []

    for activo, serie in series_por_activo.items():
        imputada, bandera = imputar_serie(serie)
        imputadas[activo] = imputada
        banderas[activo] = bandera

        for fecha in serie.index[bandera]:
            registros.append({
                "empresa": activo,
                "fecha": fecha,
                "variable": serie.name if serie.name else "precio",
                "valor_original": None,  # era NaN
                "valor_imputado": float(imputada.loc[fecha]),
                "metodo": "kalman_smoothing_local_level",
                "observacion": "NaN imputado con suavizado de Kalman (log-precio).",
            })

    reporte = pd.DataFrame(registros)
    return imputadas, banderas, reporte


def validar_imputacion(serie, n_ocultar=30, semilla=42):
    """Evaluación artificial del método: oculta valores observados y los imputa.

    NO modifica los datos reales. Sirve para estimar la capacidad de
    reconstrucción del filtro.

    Parámetros:
        serie: pd.Series de precios (sin depender de que ya haya NaN).
        n_ocultar: número de observaciones a ocultar para la prueba.
        semilla: semilla para reproducibilidad.

    Retorna:
        dict con claves "mae", "rmse", "n_ocultados" y "detalle" (DataFrame).
    """
    serie = serie.astype(float)
    observados = serie.index[serie.notna()]

    # Se ocultan posiciones interiores (con vecinos antes y después).
    candidatos = observados[1:-1] if len(observados) > 2 else observados
    n_ocultar = min(n_ocultar, len(candidatos))

    rng = np.random.default_rng(semilla)
    posiciones = rng.choice(candidatos.values, size=n_ocultar, replace=False)
    posiciones = pd.to_datetime(posiciones)

    serie_oculta = serie.copy()
    reales = serie_oculta.loc[posiciones]
    serie_oculta.loc[posiciones] = np.nan

    suavizada = _ajustar_y_suavizar(serie_oculta)
    estimados = suavizada.loc[posiciones]

    errores = (reales - estimados).abs()
    error_cuad = (reales - estimados) ** 2
    mae = float(errores.mean())
    rmse = float(np.sqrt(error_cuad.mean()))

    detalle = pd.DataFrame({
        "fecha": posiciones,
        "valor_real": reales.values,
        "valor_imputado": estimados.values,
        "error_absoluto": errores.values,
        "error_relativo": (errores / reales.abs()).values,
    }).sort_values("fecha").reset_index(drop=True)

    return {
        "mae": mae,
        "rmse": rmse,
        "mae_relativo": float((errores / reales.abs()).mean()),
        "n_ocultados": int(n_ocultar),
        "detalle": detalle,
    }