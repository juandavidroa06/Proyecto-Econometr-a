"""
anomalies.py — Saltos anómalos reversibles (Fase 4, EDA)
=========================================================

Un salto grande que se revierte casi por completo en pocos días es
sospechoso de error de dato / precio anómalo. Este módulo SOLO detecta y
contextualiza; no modifica ni elimina datos (DEC-009, DEC-018).
"""

import numpy as np
import pandas as pd

from config.settings import UMBRAL_SALTO_LOG, VENTANA_REVERSION_DIAS


def detectar_saltos_reversibles(rend_log, umbral=UMBRAL_SALTO_LOG,
                                ventana=VENTANA_REVERSION_DIAS,
                                tolerancia=0.25):
    """Busca |r_t| >= umbral seguido, en <= ``ventana`` días, de una
    reversión que devuelve al menos (1 - tolerancia) del salto.

    Retorna DataFrame: empresa, fecha_salto, ret_salto, fecha_reversion,
    ret_acumulado_ventana.
    """
    registros = []
    for col in rend_log.columns:
        r = rend_log[col].dropna()
        valores = r.to_numpy()
        for i in np.flatnonzero(np.abs(valores) >= umbral):
            for k in range(1, ventana + 1):
                if i + k >= len(valores):
                    break
                acumulado = valores[i:i + k + 1].sum()
                if abs(acumulado) <= tolerancia * abs(valores[i]):
                    registros.append({
                        "empresa": col,
                        "fecha_salto": r.index[i],
                        "ret_salto": float(valores[i]),
                        "fecha_reversion": r.index[i + k],
                        "ret_acumulado_ventana": float(acumulado),
                    })
                    break
    return pd.DataFrame(registros, columns=[
        "empresa", "fecha_salto", "ret_salto", "fecha_reversion",
        "ret_acumulado_ventana"])


def contexto_evento(crudo, fecha, dias=2):
    """Filas OHLCV alrededor de ``fecha`` + indicadores de contexto.

    Incluye volumen relativo a la mediana histórica y si la vela es 'plana'
    (Open = High = Low = Close), que junto con una reversión inmediata es
    típico de un precio anómalo aislado.
    """
    fecha = pd.Timestamp(fecha)
    if fecha not in crudo.index:
        raise KeyError(f"{fecha.date()} no está en los datos.")
    pos = crudo.index.get_loc(fecha)
    ventana = crudo.iloc[max(pos - dias, 0):pos + dias + 1].copy()
    mediana = crudo["Volume"].median()
    ventana["volumen_vs_mediana"] = ventana["Volume"] / mediana
    ventana["vela_plana"] = ((ventana["Open"] == ventana["High"])
                             & (ventana["High"] == ventana["Low"])
                             & (ventana["Low"] == ventana["Close"]))
    return ventana


def sensibilidad_volatilidad_movil(rend_log, empresa, desde, hasta,
                                   ventana=30, dias=252):
    """Volatilidad móvil anualizada máxima con y sin las fechas [desde, hasta].

    Solo diagnóstico: cuantifica cuánto pesa el evento en la volatilidad.
    """
    serie = rend_log[empresa]
    sin = serie.copy()
    sin.loc[desde:hasta] = np.nan
    vol = lambda s: s.rolling(ventana, min_periods=int(ventana * 0.8)).std() * np.sqrt(dias)
    return {"vol_max_con_evento": float(vol(serie).max()),
            "vol_max_sin_evento": float(vol(sin).max())}
