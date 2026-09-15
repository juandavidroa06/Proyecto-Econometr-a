"""Pruebas de integración del procesamiento con imputación (data_manager)."""

import numpy as np
import pandas as pd

from src.data.data_manager import procesar_con_imputacion


def _resultados_sinteticos():
    fechas = pd.date_range("2020-01-01", periods=60, freq="B")
    rng = np.random.default_rng(0)
    precios = 100 + np.cumsum(rng.normal(0, 1.0, 60))
    s = pd.Series(precios, index=fechas)

    df_a = pd.DataFrame({"Close": s, "Adj Close": s})
    s2 = s.copy()
    s2.iloc[30] = np.nan
    df_b = pd.DataFrame({"Close": s2, "Adj Close": s2})

    return {
        "Activo_A": {"dataframe": df_a, "ticker": "A.X"},
        "Activo_B": {"dataframe": df_b, "ticker": "B.X"},
    }


def test_procesar_con_imputacion_integridad():
    datos = _resultados_sinteticos()
    conjunto = procesar_con_imputacion(datos)

    # Solo Activo_B debería tener una imputación (posición 30).
    assert len(conjunto["reporte_imputaciones"]) == 1
    assert conjunto["bandera"]["Activo_B"].sum() == 1
    assert conjunto["bandera"]["Activo_A"].sum() == 0

    # El valor imputado debe ser finito y positivo.
    assert np.isfinite(conjunto["precios"].loc[conjunto["precios"].index[30], "Activo_B"])


def test_bandera_y_dataset_coherentes():
    datos = _resultados_sinteticos()
    conjunto = procesar_con_imputacion(datos)

    dataset = conjunto["dataset"]
    fila_imputada = dataset[
        (dataset["empresa"] == "Activo_B")
        & (dataset["fecha"] == conjunto["precios"].index[30])
    ]
    assert len(fila_imputada) == 1
    assert bool(fila_imputada.iloc[0]["es_imputado_kalman"]) is True


def test_retorno_depende_imputacion():
    datos = _resultados_sinteticos()
    conjunto = procesar_con_imputacion(datos)

    fecha_imp = conjunto["precios"].index[30]
    ret = conjunto["retorno_depende"]
    # El retorno en la fecha del precio imputado depende de la imputación.
    assert bool(ret.loc[fecha_imp, "Activo_B"]) is True


def test_no_modifica_datos_originales():
    datos = _resultados_sinteticos()
    df_b_antes = datos["Activo_B"]["dataframe"].copy(deep=True)

    procesar_con_imputacion(datos)

    df_b_despues = datos["Activo_B"]["dataframe"]
    pd.testing.assert_frame_equal(df_b_antes, df_b_despues)
    # El NaN original sigue presente (no se sobrescribió).
    assert pd.isna(df_b_despues["Adj Close"].iloc[30])