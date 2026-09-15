"""
outliers.py — Detección exploratoria de valores extremos
=========================================================

Detecta observaciones que *merecen investigación*, pero NO las elimina.

Métodos implementados:
    - z-score: observaciones con |z| mayor que un umbral.
    - percentiles: observaciones fuera del rango [p_baja, p_alta].

IMPORTANTE: el resultado es únicamente informativo. La decisión de excluir
una observación se tomará más adelante y quedará documentada.
"""

import numpy as np
import pandas as pd

from config.settings import (
    PERCENTIL_OUTLIER_BAJA,
    PERCENTIL_OUTLIER_ALTA,
    UMBRAL_ZSCORE,
)


def detectar_outliers_zscore(df_rendimientos, umbral=UMBRAL_ZSCORE):
    """Detecta outliers por z-score (media y sd de toda la serie).

    Retorna:
        pd.DataFrame con columnas: empresa, fecha, rendimiento, metodo, motivo.
    """
    registros = []
    for columna in df_rendimientos.columns:
        serie = df_rendimientos[columna].dropna()
        if len(serie) == 0:
            continue
        media = serie.mean()
        desv = serie.std()
        if desv == 0 or np.isnan(desv):
            continue
        z = (serie - media) / desv
        for fecha, valor_z in z.items():
            if abs(valor_z) > umbral:
                registros.append({
                    "empresa": columna,
                    "fecha": fecha,
                    "rendimiento": float(serie.loc[fecha]),
                    "metodo": "z_score",
                    "motivo": f"|z| = {valor_z:.2f} > {umbral}",
                })
    return pd.DataFrame(registros)


def detectar_outliers_percentil(df_rendimientos,
                                p_baja=PERCENTIL_OUTLIER_BAJA,
                                p_alta=PERCENTIL_OUTLIER_ALTA):
    """Detecta outliers por percentiles extremos.

    Retorna:
        pd.DataFrame con columnas: empresa, fecha, rendimiento, metodo, motivo.
    """
    registros = []
    for columna in df_rendimientos.columns:
        serie = df_rendimientos[columna].dropna()
        if len(serie) == 0:
            continue
        limite_bajo = serie.quantile(p_baja)
        limite_alto = serie.quantile(p_alta)
        for fecha, valor in serie.items():
            if valor < limite_bajo:
                registros.append({
                    "empresa": columna,
                    "fecha": fecha,
                    "rendimiento": float(valor),
                    "metodo": "percentil",
                    "motivo": f"valor < percentil {p_baja:.0%}",
                })
            elif valor > limite_alto:
                registros.append({
                    "empresa": columna,
                    "fecha": fecha,
                    "rendimiento": float(valor),
                    "metodo": "percentil",
                    "motivo": f"valor > percentil {p_alta:.0%}",
                })
    return pd.DataFrame(registros)


def detectar_outliers(df_rendimientos, umbral_z=UMBRAL_ZSCORE,
                      p_baja=PERCENTIL_OUTLIER_BAJA,
                      p_alta=PERCENTIL_OUTLIER_ALTA):
    """Combina ambos métodos y devuelve un reporte único (sin duplicados).

    Retorna:
        pd.DataFrame con columnas: empresa, fecha, rendimiento, metodo, motivo.
    """
    por_z = detectar_outliers_zscore(df_rendimientos, umbral_z)
    por_p = detectar_outliers_percentil(df_rendimientos, p_baja, p_alta)

    if por_z.empty and por_p.empty:
        return pd.DataFrame(columns=["empresa", "fecha", "rendimiento", "metodo", "motivo"])

    conjunto = pd.concat([por_z, por_p], ignore_index=True)
    conjunto = conjunto.drop_duplicates(subset=["empresa", "fecha"])
    conjunto = conjunto.sort_values(["empresa", "fecha"]).reset_index(drop=True)
    return conjunto