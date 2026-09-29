"""
liquidity.py — Auditoría de iliquidez (Fase 4, EDA)
====================================================

Mide, por empresa y sobre los datos CRUDOS (nunca se modifican):

    - % de días con precio de cierre igual al del día anterior.
    - Racha máxima de días consecutivos sin cambio de precio.
    - % de días con volumen cero y mediana de volumen.

Compara contra umbrales de REFERENCIA (config/settings.py). Superar el umbral
NO elimina la empresa: solo la marca para decisión del equipo (DEC-018).
"""

import pandas as pd

from config.settings import UMBRAL_PCT_PRECIO_REPETIDO, UMBRAL_RACHA_MAX_DIAS


def racha_maxima_sin_cambio(precios):
    """Mayor número de días consecutivos en que el precio no cambió."""
    repetido = precios.diff() == 0
    grupos = (~repetido).cumsum()
    if len(repetido) == 0:
        return 0
    return int(repetido.groupby(grupos).sum().max())


def auditar_iliquidez(crudos, columna="Close",
                      umbral_pct=UMBRAL_PCT_PRECIO_REPETIDO,
                      umbral_racha=UMBRAL_RACHA_MAX_DIAS):
    """Auditoría de iliquidez para un dict {nombre: DataFrame OHLCV}.

    Retorna un DataFrame con una fila por empresa. La columna ``decision``
    queda siempre en 'pendiente': la inclusión/exclusión la decide el equipo.
    """
    filas = []
    for nombre, df in crudos.items():
        if columna not in df.columns or "Volume" not in df.columns:
            raise ValueError(f"{nombre}: faltan columnas '{columna}'/'Volume'.")
        precio = df[columna].round(6)
        pct_rep = float((precio.diff() == 0).sum() / max(len(precio) - 1, 1))
        racha = racha_maxima_sin_cambio(precio)
        filas.append({
            "empresa": nombre,
            "observaciones": len(df),
            "pct_precio_repetido": round(pct_rep, 4),
            "racha_max_dias": racha,
            "pct_volumen_cero": round(float((df["Volume"] == 0).mean()), 4),
            "mediana_volumen": float(df["Volume"].median()),
            "incumple_pct": pct_rep > umbral_pct,
            "incumple_racha": racha > umbral_racha,
        })
    res = pd.DataFrame(filas)
    res["supera_umbral"] = res["incumple_pct"] | res["incumple_racha"]
    res["decision"] = "pendiente"
    return res.sort_values("pct_precio_repetido", ascending=False,
                           ignore_index=True)
