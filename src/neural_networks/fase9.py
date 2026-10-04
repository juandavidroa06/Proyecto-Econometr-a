"""
fase9.py — Ejecución de la Fase 9: MLP y LSTM
==============================================

Flujo (DEC-026):
    1. Mismo panel y filas que la Fase 8 (``construir_panel`` / ``separar``),
       cargado SOLO con entrenamiento y validación.
    2. Dentro de entrenamiento: el último 20 % de fechas objetivo es el
       conjunto de PARADA (elige hiperparámetros y época). Escaladores
       ajustados solo con la parte de ajuste; en el modelo final, con todo
       entrenamiento.
    3. Modelo final por semilla: se reentrena con todo entrenamiento durante
       la época óptima encontrada; se promedian 5 semillas (conjunto).
    4. Evaluación en validación sobre las MISMAS filas que todos los demás
       modelos (Random Forest, Gradient Boosting, ARIMA, media, cero).

No toca el bloque de prueba.

Ejecutar:  python -m src.neural_networks.fase9
"""

import itertools
import logging

import numpy as np
import pandas as pd

from config.environment import RUTA_RESULTADOS
from config.settings import FECHA_FIN_TRAIN, FECHA_FIN_VALIDACION, SEMILLA_ALEATORIA
from src.econometrics import evaluacion
from src.machine_learning import variables
from src.machine_learning.fase8 import cargar_datos, matriz_variables
from src.neural_networks import datos as dnn
from src.neural_networks import redes
from src.portfolio.markowitz import seleccionar_universo_liquido

logger = logging.getLogger(__name__)

SEMILLAS = [SEMILLA_ALEATORIA + k for k in range(5)]
LONGITUD_SECUENCIA = 30
REJILLAS = {
    "mlp": {"ocultas": [(32,), (64, 32)], "decaimiento": [1e-4, 1e-2]},
    "lstm": {"oculta": [16, 32], "decaimiento": [1e-4, 1e-2]},
}


# --- Preparación de entradas -----------------------------------------------------

def _entradas_mlp(base, otros, columnas, empresas):
    """Escala con ``base`` (solo train) y aplica a ``otros``."""
    X_base = matriz_variables(base, columnas, empresas)
    esc = dnn.Escalador().ajustar(X_base)
    return [esc.transformar(X_base).to_numpy()] + [
        esc.transformar(matriz_variables(o, columnas, empresas)).to_numpy() for o in otros]


def _entradas_lstm(panel, base, otros, empresas):
    """Secuencias escaladas con media/desv de ``base`` + indicadores de empresa."""
    media = base[dnn.VARIABLES_SECUENCIA].mean().to_numpy()
    desv = base[dnn.VARIABLES_SECUENCIA].std(ddof=0).to_numpy()
    salida = []
    for df in [base] + list(otros):
        X, mascara = dnn.secuencias(panel, df, LONGITUD_SECUENCIA)
        estaticas = np.column_stack([(df["empresa"].to_numpy()[mascara] == e).astype(float)
                                     for e in empresas])
        salida.append(((dnn.escalar_secuencias(X, media, desv), estaticas), mascara))
    return salida


def _fabrica(tipo, n_entradas, n_estaticas, hiper):
    if tipo == "mlp":
        return lambda: redes.MLP(n_entradas, ocultas=hiper["ocultas"])
    return lambda: redes.LSTMRed(n_entradas, n_estaticas, oculta=hiper["oculta"])


def _preparar(tipo, panel, base, otros, columnas, empresas):
    """Entradas y objetivos para ``base`` y ``otros`` (filtra por máscara)."""
    if tipo == "mlp":
        Xs = _entradas_mlp(base, otros, columnas, empresas)
        return [(X, df["objetivo"].to_numpy(), np.ones(len(df), bool))
                for X, df in zip(Xs, [base] + list(otros))]
    pares = _entradas_lstm(panel, base, otros, empresas)
    return [(X, df["objetivo"].to_numpy()[m], m)
            for (X, m), df in zip(pares, [base] + list(otros))]


def _dimensiones(tipo, X):
    if tipo == "mlp":
        return X.shape[1], 0
    return X[0].shape[2], X[1].shape[1]


# --- Selección, ajuste final y conjunto -----------------------------------------

def seleccionar(tipo, panel, train, columnas, empresas):
    """Elige hiperparámetros con el conjunto de parada (semilla base)."""
    ajuste, parada = dnn.separar_interno(train["fecha_objetivo"])
    t_aj, t_pa = train[ajuste].reset_index(drop=True), train[parada].reset_index(drop=True)
    (X_aj, y_aj, _), (X_pa, y_pa, _) = _preparar(tipo, panel, t_aj, [t_pa], columnas, empresas)
    n_ent, n_est = _dimensiones(tipo, X_aj)
    filas = []
    nombres = list(REJILLAS[tipo])
    for valores in itertools.product(*REJILLAS[tipo].values()):
        hiper = dict(zip(nombres, valores))
        _, hist = redes.entrenar(_fabrica(tipo, n_ent, n_est, hiper), X_aj, y_aj,
                                 X_pa, y_pa, semilla=SEMILLAS[0],
                                 decaimiento=hiper["decaimiento"])
        filas.append({"modelo": tipo, **{k: str(v) for k, v in hiper.items()},
                      **hist, "mse_parada_media": float(np.mean((y_pa - y_aj.mean()) ** 2)),
                      "n_ajuste": len(y_aj), "n_parada": len(y_pa)})
        logger.info("%s %s -> %s", tipo, hiper, hist)
    tabla = pd.DataFrame(filas).sort_values("mse_parada").reset_index(drop=True)
    indice = int(np.argmin([f["mse_parada"] for f in filas]))
    mejor = dict(zip(nombres, list(itertools.product(*REJILLAS[tipo].values()))[indice]))
    return mejor, tabla


def conjunto_final(tipo, hiper, panel, train, valid, columnas, empresas):
    """Por semilla: época óptima con parada y reentreno con todo train.

    Retorna (DataFrame de predicciones de validación por semilla, épocas).
    """
    ajuste, parada = dnn.separar_interno(train["fecha_objetivo"])
    t_aj, t_pa = train[ajuste].reset_index(drop=True), train[parada].reset_index(drop=True)
    (X_aj, y_aj, _), (X_pa, y_pa, _) = _preparar(tipo, panel, t_aj, [t_pa], columnas, empresas)
    (X_tr, y_tr, _), (X_va, _, m_va) = _preparar(tipo, panel, train, [valid], columnas, empresas)
    n_ent, n_est = _dimensiones(tipo, X_tr)
    claves = valid.loc[m_va, ["fecha_objetivo", "empresa"]].reset_index(drop=True)
    preds, epocas = {}, []
    for semilla in SEMILLAS:
        _, hist = redes.entrenar(_fabrica(tipo, n_ent, n_est, hiper), X_aj, y_aj,
                                 X_pa, y_pa, semilla=semilla,
                                 decaimiento=hiper["decaimiento"])
        red, _ = redes.entrenar(_fabrica(tipo, n_ent, n_est, hiper), X_tr, y_tr,
                                semilla=semilla, epocas=hist["epoca_optima"],
                                decaimiento=hiper["decaimiento"])
        preds[f"semilla_{semilla}"] = redes.predecir(red, X_va)
        epocas.append({"modelo": tipo, "semilla": semilla, **hist,
                       "n_train": len(y_tr), "n_validacion": len(claves)})
    p = pd.concat([claves, pd.DataFrame(preds)], axis=1)
    p[tipo] = p[[c for c in p.columns if c.startswith("semilla_")]].mean(axis=1)
    return p, pd.DataFrame(epocas)


# --- Ejecución ---------------------------------------------------------------------

def ejecutar_fase9(guardar=True):
    rend, vol, ext, rend_train = cargar_datos()
    panel = variables.construir_panel(rend, vol, ext)
    train, valid, _ = variables.separar(panel, FECHA_FIN_TRAIN, FECHA_FIN_VALIDACION)
    columnas = variables.columnas_variables(panel)
    empresas = list(rend.columns)

    tablas, hiper, preds, epocas = [], {}, {}, []
    for tipo in ("mlp", "lstm"):
        hiper[tipo], tabla = seleccionar(tipo, panel, train, columnas, empresas)
        tablas.append(tabla)
        logger.info("%s: hiperparámetros elegidos %s", tipo, hiper[tipo])
        preds[tipo], ep = conjunto_final(tipo, hiper[tipo], panel, train, valid,
                                         columnas, empresas)
        epocas.append(ep)

    previos = pd.read_csv(RUTA_RESULTADOS / "fase8_pronosticos_validacion.csv",
                          parse_dates=["fecha_objetivo"])
    clave = ["fecha_objetivo", "empresa"]
    comp = previos.merge(preds["mlp"][clave + ["mlp"]], on=clave, how="inner")
    comp = comp.merge(preds["lstm"][clave + ["lstm"]], on=clave, how="inner")
    logger.info("Filas comunes de validación: %d (Fase 8: %d)", len(comp), len(previos))

    modelos_eval = ("mlp", "lstm", "random_forest", "gradient_boosting", "arima",
                    "media_train", "cero")
    _, iliquidos, _ = seleccionar_universo_liquido(rend_train)
    filas = []
    for empresa, g in [("Todas", comp)] + list(comp.groupby("empresa", sort=False)):
        y = g["objetivo"].reset_index(drop=True)
        fila = {"empresa": empresa, "n": len(g), "iliquida_train": empresa in iliquidos}
        perdida_media = evaluacion.perdida_cuadratica(y, g["media_train"].reset_index(drop=True))
        for nombre in modelos_eval:
            f = g[nombre].reset_index(drop=True)
            fila[f"rmse_{nombre}"] = evaluacion.rmse(y, f)
            fila[f"mae_{nombre}"] = evaluacion.mae(y, f)
        for nombre in ("mlp", "lstm", "random_forest", "gradient_boosting"):
            dm = evaluacion.diebold_mariano(
                evaluacion.perdida_cuadratica(y, g[nombre].reset_index(drop=True)),
                perdida_media)
            fila[f"dm_pvalor_{nombre}_vs_media"] = dm["dm_pvalor"]
        filas.append(fila)
    metricas = pd.DataFrame(filas)

    # Dispersión entre semillas (RMSE de cada semilla sobre las filas comunes).
    dispersion = []
    for tipo in ("mlp", "lstm"):
        p = comp[clave + ["objetivo"]].merge(preds[tipo], on=clave)
        for c in [c for c in p.columns if c.startswith("semilla_")]:
            dispersion.append({"modelo": tipo, "semilla": int(c.split("_")[1]),
                               "rmse": evaluacion.rmse(p["objetivo"], p[c])})

    res = {
        "seleccion": pd.concat(tablas, ignore_index=True),
        "hiperparametros": pd.DataFrame([{"modelo": t, **{k: str(v) for k, v in h.items()}}
                                         for t, h in hiper.items()]),
        "epocas": pd.concat(epocas, ignore_index=True),
        "metricas": metricas,
        "dispersion_semillas": pd.DataFrame(dispersion),
        "pronosticos": comp,
    }
    if guardar:
        RUTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
        for clave_res, archivo in (("seleccion", "fase9_seleccion.csv"),
                                   ("hiperparametros", "fase9_hiperparametros.csv"),
                                   ("epocas", "fase9_epocas.csv"),
                                   ("metricas", "fase9_metricas.csv"),
                                   ("dispersion_semillas", "fase9_dispersion_semillas.csv"),
                                   ("pronosticos", "fase9_pronosticos_validacion.csv")):
            res[clave_res].to_csv(RUTA_RESULTADOS / archivo, index=False)
    return res


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    r = ejecutar_fase9()
    pd.set_option("display.width", 250)
    print(r["seleccion"].to_string(index=False))
    print(r["epocas"].to_string(index=False))
    cols = ["empresa", "n"] + [f"rmse_{m}" for m in ("mlp", "lstm", "random_forest",
                                                    "gradient_boosting", "arima", "media_train")] + \
           ["dm_pvalor_mlp_vs_media", "dm_pvalor_lstm_vs_media"]
    print(r["metricas"][cols].round(5).to_string(index=False))
    print(r["dispersion_semillas"].groupby("modelo")["rmse"].describe().round(6))
