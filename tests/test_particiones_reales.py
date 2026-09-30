"""Auditoría automática de la Fase 5 sobre los archivos reales.

Comprueba, sobre ``datos/particiones/``, que: (1) las tres bases están
identificadas sin ambigüedad (train <= 2023, validación = 2024, test >= 2025);
(2) no hay solapamiento y las tres reconstruyen la base procesada; (3) los
archivos no fueron alterados; (4) la imputación de Kalman no tocó train ni
validación; (5) ningún módulo de ``src`` abre el bloque de prueba.

Nota: las pruebas (1) y (2) leen el bloque de prueba solo para verificar
fechas (estructura), nunca valores para decidir modelos.
"""

import pandas as pd
import pytest

from config.environment import RUTA_PARTICIONES, RUTA_DATOS_PROCESADOS, RAIZ
from config.settings import FECHA_FIN_TRAIN, FECHA_FIN_VALIDACION
from src.preprocessing.split import cargar_particion, verificar_huellas

BASES = {"rendimientos_log": "rendimientos_log.csv", "precios": "precios.csv"}

pytestmark = pytest.mark.skipif(
    not (RUTA_PARTICIONES / "huellas.json").exists(),
    reason="Aún no se generaron las particiones (ejecutar etapa_fase5).",
)

T = pd.Timestamp(FECHA_FIN_TRAIN)
V = pd.Timestamp(FECHA_FIN_VALIDACION)


def _cargar_todo(base):
    return {b: cargar_particion(RUTA_PARTICIONES, base, b,
                                confirmar_evaluacion_final=True)
            for b in ("train", "validacion", "test")}


@pytest.mark.parametrize("base", list(BASES))
def test_tres_bases_identificadas_sin_ambiguedad(base):
    p = _cargar_todo(base)
    assert p["train"].index.max() <= T
    assert p["validacion"].index.min() > T
    assert p["validacion"].index.max() <= V
    assert p["validacion"].index.min().year == 2024
    assert p["validacion"].index.max().year == 2024
    assert p["test"].index.min() > V
    assert p["test"].index.min() >= pd.Timestamp("2025-01-01")


@pytest.mark.parametrize("base", list(BASES))
def test_sin_solapamiento_y_reconstruyen_la_base_procesada(base):
    p = _cargar_todo(base)
    t, v, s = p["train"].index, p["validacion"].index, p["test"].index
    assert len(t.intersection(v)) == 0
    assert len(t.intersection(s)) == 0
    assert len(v.intersection(s)) == 0
    original = pd.read_csv(RUTA_DATOS_PROCESADOS / BASES[base],
                           index_col=0, parse_dates=True)
    assert t.append(v).append(s).equals(original.index)


@pytest.mark.parametrize("base", list(BASES))
def test_archivos_de_train_y_validacion_no_fueron_alterados(base):
    verificar_huellas(RUTA_PARTICIONES, base, RUTA_PARTICIONES / "huellas.json")


def test_imputacion_kalman_no_toca_train_ni_validacion():
    """El suavizado de Kalman usa información posterior (ver kalman_imputation).

    Si una imputación cae en train o validación, hay que registrar una decisión
    en el diario antes de continuar.
    """
    banderas = pd.read_csv(RUTA_DATOS_PROCESADOS / "banderas_imputacion.csv",
                           index_col=0, parse_dates=True)
    imputadas = banderas.index[banderas.any(axis=1)]
    assert (imputadas > V).all(), (
        f"Hay imputaciones en train/validación: {list(imputadas[imputadas <= V])}")


def test_ningun_modulo_de_src_abre_el_bloque_de_prueba():
    """La prueba se abre solo en la evaluación final (módulo dedicado)."""
    permitidos = {"split.py", "evaluacion_final.py"}
    for ruta in (RAIZ / "src").rglob("*.py"):
        if ruta.name in permitidos:
            continue
        texto = ruta.read_text(encoding="utf-8")
        assert "confirmar_evaluacion_final=True" not in texto, ruta
        assert "_test.csv" not in texto, ruta
