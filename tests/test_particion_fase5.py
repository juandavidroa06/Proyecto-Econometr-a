"""Tests de la Fase 5: partición cronológica blindada contra data leakage."""

import numpy as np
import pandas as pd
import pytest

from src.preprocessing.split import (
    particion_temporal,
    verificar_sin_leakage,
    guardar_particiones,
    cargar_particion,
    huella,
    guardar_huellas,
    verificar_huellas,
)

CORTE_TRAIN = "2022-06-30"
CORTE_VAL = "2022-12-31"


def _df(n=400, semilla=0):
    rng = np.random.default_rng(semilla)
    idx = pd.date_range("2022-01-03", periods=n, freq="B", name="Date")
    return pd.DataFrame(rng.normal(0, 0.01, (n, 3)),
                        index=idx, columns=["a", "b", "c"])


def test_bloques_son_consecutivos_y_reconstruyen_el_original():
    df = _df()
    p = particion_temporal(df, CORTE_TRAIN, CORTE_VAL)
    verificar_sin_leakage(p, df)
    assert p["train"].index.max() <= pd.Timestamp(CORTE_TRAIN)
    assert p["validacion"].index.min() > pd.Timestamp(CORTE_TRAIN)
    assert p["validacion"].index.max() <= pd.Timestamp(CORTE_VAL)
    assert p["test"].index.min() > pd.Timestamp(CORTE_VAL)


def test_train_no_cambia_si_se_agregan_datos_futuros():
    """Lo que ve el entrenamiento no puede depender de datos posteriores."""
    completo = _df(400)
    truncado = completo.iloc[:300]
    p_completo = particion_temporal(completo, CORTE_TRAIN, CORTE_VAL)
    p_truncado = particion_temporal(truncado, CORTE_TRAIN, CORTE_VAL)
    pd.testing.assert_frame_equal(p_completo["train"], p_truncado["train"])
    pd.testing.assert_frame_equal(p_completo["validacion"], p_truncado["validacion"])


def test_verificar_detecta_solape_y_perdida_de_filas():
    df = _df()
    p = particion_temporal(df, CORTE_TRAIN, CORTE_VAL)
    solapada = dict(p)
    solapada["validacion"] = pd.concat([p["train"].iloc[-5:], p["validacion"]])
    with pytest.raises(ValueError):
        verificar_sin_leakage(solapada)
    incompleta = dict(p)
    incompleta["test"] = p["test"].iloc[1:]
    with pytest.raises(ValueError):
        verificar_sin_leakage(incompleta, df)


def test_verificar_detecta_bloques_en_orden_invertido():
    df = _df()
    p = particion_temporal(df, CORTE_TRAIN, CORTE_VAL)
    invertida = {"train": p["test"], "validacion": p["validacion"], "test": p["train"]}
    with pytest.raises(ValueError):
        verificar_sin_leakage(invertida)


def test_guardar_y_cargar_reproduce_exactamente(tmp_path):
    df = _df()
    p = particion_temporal(df, CORTE_TRAIN, CORTE_VAL)
    guardar_particiones(p, tmp_path, "rend")
    for bloque in ("train", "validacion"):
        cargado = cargar_particion(tmp_path, "rend", bloque)
        pd.testing.assert_frame_equal(cargado, p[bloque], check_freq=False)
        assert huella(cargado) == huella(p[bloque])


def test_test_exige_confirmacion_explicita(tmp_path):
    df = _df()
    p = particion_temporal(df, CORTE_TRAIN, CORTE_VAL)
    guardar_particiones(p, tmp_path, "rend")
    with pytest.raises(PermissionError):
        cargar_particion(tmp_path, "rend", "test")
    test = cargar_particion(tmp_path, "rend", "test", confirmar_evaluacion_final=True)
    assert len(test) == len(p["test"])


def test_bloque_desconocido_se_rechaza(tmp_path):
    with pytest.raises(ValueError):
        cargar_particion(tmp_path, "rend", "otro")


def test_huellas_detectan_alteracion_de_un_archivo(tmp_path):
    df = _df()
    p = particion_temporal(df, CORTE_TRAIN, CORTE_VAL)
    guardar_particiones(p, tmp_path, "rend")
    huellas = {f"rend_{b}": huella(p[b]) for b in p}
    ruta = tmp_path / "huellas.json"
    guardar_huellas(huellas, ruta)
    verificar_huellas(tmp_path, "rend", ruta)  # intacto: no lanza

    alterado = p["train"].copy()
    alterado.iloc[0, 0] += 0.5
    alterado.to_csv(tmp_path / "rend_train.csv", encoding="utf-8")
    with pytest.raises(ValueError):
        verificar_huellas(tmp_path, "rend", ruta)


def test_huella_es_estable_entre_ejecuciones():
    df = _df()
    assert huella(df) == huella(df.copy())
    otro = df.copy()
    otro.iloc[3, 1] += 1e-9
    assert huella(otro) != huella(df)


def test_configuracion_de_cortes_es_coherente():
    from config.settings import FECHA_FIN_TRAIN, FECHA_FIN_VALIDACION
    assert pd.Timestamp(FECHA_FIN_TRAIN) < pd.Timestamp(FECHA_FIN_VALIDACION)
    assert pd.Timestamp(FECHA_FIN_TRAIN) == pd.Timestamp("2023-12-31")
    assert pd.Timestamp(FECHA_FIN_VALIDACION) == pd.Timestamp("2024-12-31")
