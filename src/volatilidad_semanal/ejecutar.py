"""
ejecutar.py — Volatilidad semanal y rendimiento semanal (DEC-029 / DEC-030)
============================================================================

Ejecuta EXACTAMENTE el plan registrado en DEC-029:

    Objetivo principal: RV de la semana siguiente (4 acciones líquidas).
        Referencias: EWMA, GARCH(1,1)-t y HAR (log RV, MCO por empresa).
        Retadores: Random Forest, Gradient Boosting y MLP (agrupados).
        Pérdida principal QLIKE; H1 = algún retador mejor que HAR
        (Diebold-Mariano con Holm sobre 3 pruebas, 5 %). MCS al 10 %.
    Robustez: rendimiento de la semana siguiente con RF y GB frente a la
        media de entrenamiento y el cero.

Solo entrenamiento y validación; no toca el bloque de prueba.

Ejecutar:  python -m src.volatilidad_semanal.ejecutar
"""

import logging

import numpy as np
import pandas as pd

from config.environment import RUTA_GRAFICOS, RUTA_RESULTADOS
from config.settings import FECHA_FIN_TRAIN, FECHA_FIN_VALIDACION, SEMILLA_ALEATORIA
from src.comparacion import estadistica as est
from src.econometrics import evaluacion, garch
from src.machine_learning import modelos
from src.machine_learning.fase8 import cargar_datos
from src.neural_networks import datos as dnn
from src.neural_networks import redes
from src.portfolio.markowitz import seleccionar_universo_liquido
from src.volatilidad_semanal import panel as pv

logger = logging.getLogger(__name__)

SEMILLAS = [SEMILLA_ALEATORIA + k for k in range(5)]
BOOT = dict(n_remuestras=2000, largo_bloque=4, semilla=SEMILLA_ALEATORIA)
RETADORES = ["random_forest", "gradient_boosting", "mlp"]


def _matriz(df, columnas, empresas):
    X = df[columnas].copy()
    for e in empresas:
        X[f"empresa_{e}"] = (df["empresa"] == e).astype(float)
    return X


# --- Modelos sobre log RV -------------------------------------------------------

def har(train, valid):
    """HAR en log por empresa (MCO). Retorna (predicción en nivel, coeficientes)."""
    pred = pd.Series(np.nan, index=valid.index)
    coefs = []
    for e, g in train.groupby("empresa"):
        X = np.column_stack([np.ones(len(g)), g[pv.VARIABLES_HAR].to_numpy()])
        beta, *_ = np.linalg.lstsq(X, g["log_rv_objetivo"].to_numpy(), rcond=None)
        resid = g["log_rv_objetivo"].to_numpy() - X @ beta
        smearing = float(np.mean(np.exp(resid)))
        v = valid[valid["empresa"] == e]
        Xv = np.column_stack([np.ones(len(v)), v[pv.VARIABLES_HAR].to_numpy()])
        pred.loc[v.index] = np.exp(Xv @ beta) * smearing
        coefs.append({"empresa": e, "constante": beta[0],
                      **{f"beta_{c}": b for c, b in zip(pv.VARIABLES_HAR, beta[1:])},
                      "smearing": smearing, "n_train": len(g)})
    return pred, pd.DataFrame(coefs)


def arbol(tipo, train, valid, columnas, empresas, objetivo, en_log):
    """RF o GB con CV temporal en train; smearing con residuos fuera de pliegue."""
    X_tr, X_va = _matriz(train, columnas, empresas), _matriz(valid, columnas, empresas)
    y = train[objetivo]
    mejores, tabla = modelos.validacion_cruzada(tipo, X_tr, y, train["fecha_objetivo"])
    final = modelos.ajustar_final(tipo, mejores, X_tr, y)
    pred = pd.Series(final.predict(X_va), index=valid.index)
    if en_log:
        resid = []
        for idx_tr, idx_te in modelos.pliegues_por_fecha(train["fecha_objetivo"]):
            m = modelos.crear_modelo(tipo, **mejores).fit(X_tr.iloc[idx_tr], y.iloc[idx_tr])
            resid.append(y.iloc[idx_te].to_numpy() - m.predict(X_tr.iloc[idx_te]))
        pred = np.exp(pred) * float(np.mean(np.exp(np.concatenate(resid))))
    tabla.insert(0, "objetivo", objetivo)
    return pred, mejores, tabla


def mlp(train, valid, columnas, empresas):
    """MLP sobre log RV: selección con el final de train, 5 semillas, smearing
    con los residuos del conjunto de parada."""
    ajuste, parada = dnn.separar_interno(train["fecha_objetivo"])
    t_aj, t_pa = train[ajuste].reset_index(drop=True), train[parada].reset_index(drop=True)

    def entradas(base, otros):
        Xb = _matriz(base, columnas, empresas)
        esc = dnn.Escalador().ajustar(Xb)
        return [esc.transformar(Xb).to_numpy()] + [
            esc.transformar(_matriz(o, columnas, empresas)).to_numpy() for o in otros]

    X_aj, X_pa = entradas(t_aj, [t_pa])
    X_tr, X_va = entradas(train, [valid])
    y_aj, y_pa = t_aj["log_rv_objetivo"].to_numpy(), t_pa["log_rv_objetivo"].to_numpy()
    y_tr = train["log_rv_objetivo"].to_numpy()
    n = X_tr.shape[1]
    # El objetivo log RV ya está en una escala O(1): se divide por 100 para
    # compensar el escalado interno de ``redes.entrenar``. Misma rejilla y
    # lote que la Fase 9 (DEC-029).
    kw = {}
    seleccion = []
    for ocultas in [(32,), (64, 32)]:
        for dec in [1e-4, 1e-2]:
            _, h = redes.entrenar(lambda o=ocultas: redes.MLP(n, ocultas=o), X_aj, y_aj / 100,
                                  X_pa, y_pa / 100, semilla=SEMILLAS[0], decaimiento=dec, **kw)
            # mse_parada en unidades de (log RV)^2 (se deshace el reescalado).
            seleccion.append({"ocultas": ocultas, "decaimiento": dec,
                              "epoca_optima": h["epoca_optima"],
                              "mse_parada": h["mse_parada"] * 100 ** 2})
    mejor = min(seleccion, key=lambda f: f["mse_parada"])
    preds_va, preds_pa = [], []
    for semilla in SEMILLAS:
        crear = lambda: redes.MLP(n, ocultas=mejor["ocultas"])
        red_pa, h = redes.entrenar(crear, X_aj, y_aj / 100, X_pa, y_pa / 100,
                                   semilla=semilla, decaimiento=mejor["decaimiento"], **kw)
        preds_pa.append(redes.predecir(red_pa, X_pa) * 100)
        red, _ = redes.entrenar(crear, X_tr, y_tr / 100, semilla=semilla,
                                epocas=h["epoca_optima"], decaimiento=mejor["decaimiento"], **kw)
        preds_va.append(redes.predecir(red, X_va) * 100)
    smearing = float(np.mean(np.exp(y_pa - np.mean(preds_pa, axis=0))))
    pred = pd.Series(np.exp(np.mean(preds_va, axis=0)) * smearing, index=valid.index)
    sel = pd.DataFrame(seleccion)
    sel["ocultas"] = sel["ocultas"].astype(str)
    return pred, mejor, sel


# --- Referencias diarias agregadas a la semana -------------------------------------

def referencias_diarias(rend_log, valid):
    """EWMA y GARCH-t: varianza de la semana objetivo (en %^2) pronosticada al
    cierre de la semana anterior, para las filas de ``valid``."""
    ewma = pd.Series(np.nan, index=valid.index)
    garch_pred = pd.Series(np.nan, index=valid.index)
    for e, g in valid.groupby("empresa"):
        serie = rend_log[e].dropna()
        tr = serie[serie.index <= pd.Timestamp(FECHA_FIN_TRAIN)]
        va = serie[serie.index > pd.Timestamp(FECHA_FIN_TRAIN)]
        completa = pd.concat([tr, va])
        pos = {d: i for i, d in enumerate(completa.index)}
        h_ewma = garch.varianza_ewma(tr, va, 0.94)        # h de cada día de validación
        res = garch.ajustar_garch(tr, va, "t")
        if res.convergence_flag != 0:
            raise RuntimeError(f"GARCH no convergió para {e}.")
        f = res.forecast(horizon=5, start=len(tr) - 1, reindex=False).variance
        for idx, fila in g.iterrows():
            origen = pos[fila["ultimo_dia"]]
            n = int(fila["n_dias_objetivo"])
            dia_siguiente = completa.index[origen + 1]
            ewma[idx] = h_ewma.loc[dia_siguiente] * n
            garch_pred[idx] = float(f.iloc[origen - (len(tr) - 1)].iloc[:n].sum())
    return ewma, garch_pred


# --- Evaluación -------------------------------------------------------------------

def _por_semana(valid, perdidas):
    return perdidas.groupby(valid["fecha_objetivo"]).mean().sort_index()


def evaluar_volatilidad(valid, pron):
    proxy = valid["rv_objetivo"]
    qlike = pd.DataFrame({m: np.log(h) + proxy / h for m, h in pron.items()})
    mse = pd.DataFrame({m: (proxy - h) ** 2 for m, h in pron.items()})
    q_sem = _por_semana(valid, qlike)
    mcs = est.model_confidence_set(q_sem, alfa=0.10, **BOOT)

    pruebas = []
    for ret in RETADORES:
        dm = evaluacion.diebold_mariano(q_sem[ret], q_sem["har"])
        pruebas.append({"familia": "H1: retador vs HAR", "modelo": ret, "referencia": "har", **dm})
    for ref in ("ewma", "garch"):
        dm = evaluacion.diebold_mariano(q_sem["har"], q_sem[ref])
        pruebas.append({"familia": "secundaria: HAR vs referencia", "modelo": "har",
                        "referencia": ref, **dm})
    pruebas = pd.DataFrame(pruebas)
    for fam, g in pruebas.groupby("familia"):
        pruebas.loc[g.index, "pvalor_holm"] = est.holm(g["dm_pvalor"]).to_numpy()
    pruebas["significativa_5pct"] = pruebas["pvalor_holm"] < 0.05

    agregado = pd.DataFrame({"qlike": qlike.mean(), "mse": mse.mean()}).rename_axis("modelo")
    agregado = agregado.reset_index().merge(mcs[["modelo", "pvalor_mcs", "en_mcs"]], on="modelo")
    por_empresa = qlike.groupby(valid["empresa"]).mean()
    return agregado.sort_values("qlike").reset_index(drop=True), pruebas, por_empresa


def evaluar_rendimiento(valid, pred, media):
    y = valid["ret_objetivo"]
    perd = pd.DataFrame({"random_forest": (y - pred["random_forest"]) ** 2,
                         "gradient_boosting": (y - pred["gradient_boosting"]) ** 2,
                         "media_train": (y - media) ** 2, "cero": y ** 2})
    sem = _por_semana(valid, perd)
    filas = []
    for m in ("random_forest", "gradient_boosting"):
        for ref in ("media_train", "cero"):
            dm = evaluacion.diebold_mariano(sem[m], sem[ref])
            filas.append({"modelo": m, "referencia": ref,
                          "rmse_modelo": float(np.sqrt(perd[m].mean())),
                          "rmse_referencia": float(np.sqrt(perd[ref].mean())), **dm})
    t = pd.DataFrame(filas)
    t["pvalor_holm"] = est.holm(t["dm_pvalor"]).to_numpy()
    return t


def ejecutar(guardar=True):
    rend, vol, ext, rend_train = cargar_datos()
    liquidos, _, _ = seleccionar_universo_liquido(rend_train)
    panel = pv.construir_panel_semanal(rend, vol, ext, liquidos)
    panel, columnas = pv.variables_modelo(panel)

    # --- Volatilidad (objetivo principal) ---
    tr, va, filas_v = pv.separar(panel, columnas, FECHA_FIN_TRAIN, FECHA_FIN_VALIDACION,
                                 "rv_objetivo")
    logger.info("Volatilidad: %s", filas_v.to_dict("records"))
    pron = {}
    pron["har"], coef_har = har(tr, va)
    ewma, garch_pred = referencias_diarias(rend, va)
    pron["ewma"], pron["garch"] = ewma, garch_pred
    tablas_cv, hiper = [], {}
    for tipo in ("random_forest", "gradient_boosting"):
        pron[tipo], hiper[tipo], t = arbol(tipo, tr, va, columnas, liquidos,
                                           "log_rv_objetivo", en_log=True)
        tablas_cv.append(t)
    pron["mlp"], hiper["mlp"], sel_mlp = mlp(tr, va, columnas, liquidos)
    if any(pd.Series(h).isna().any() or (pd.Series(h) <= 0).any() for h in pron.values()):
        raise ValueError("Hay pronósticos de varianza faltantes o no positivos.")
    agregado, pruebas, por_empresa = evaluar_volatilidad(va, pron)

    # --- Rendimiento semanal (robustez) ---
    tr_r, va_r, filas_r = pv.separar(panel, columnas, FECHA_FIN_TRAIN, FECHA_FIN_VALIDACION,
                                     "ret_objetivo")
    pred_r = {}
    for tipo in ("random_forest", "gradient_boosting"):
        pred_r[tipo], hiper[f"{tipo}_rendimiento"], t = arbol(
            tipo, tr_r, va_r, columnas, liquidos, "ret_objetivo", en_log=False)
        tablas_cv.append(t)
    media = va_r["empresa"].map(tr_r.groupby("empresa")["ret_objetivo"].mean())
    rendimiento = evaluar_rendimiento(va_r, pred_r, media)

    pronosticos = va[["fecha_objetivo", "empresa", "rv_objetivo", "n_dias_objetivo"]].copy()
    for m, h in pron.items():
        pronosticos[m] = h
    res = {"filas": pd.concat([filas_v.assign(objetivo="rv"), filas_r.assign(objetivo="ret")]),
           "volatilidad": agregado, "pruebas": pruebas,
           "volatilidad_por_empresa": por_empresa.reset_index(),
           "rendimiento": rendimiento, "har": coef_har,
           "cv": pd.concat(tablas_cv, ignore_index=True), "mlp_seleccion": sel_mlp,
           "hiperparametros": pd.DataFrame([{"modelo": k, **{a: str(b) for a, b in v.items()}}
                                            for k, v in hiper.items()]),
           "pronosticos": pronosticos}
    if guardar:
        RUTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
        for clave in ("filas", "volatilidad", "pruebas", "volatilidad_por_empresa",
                      "rendimiento", "har", "cv", "mlp_seleccion", "hiperparametros",
                      "pronosticos"):
            res[clave].to_csv(RUTA_RESULTADOS / f"semanal_{clave}.csv", index=False)
        _graficar(pronosticos)
    return res


def _graficar(p):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    RUTA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    fig, ejes = plt.subplots(2, 2, figsize=(14, 7), sharex=True)
    estilos = {"har": ("black", "-"), "ewma": ("tab:blue", "-"), "garch": ("tab:green", "--"),
               "random_forest": ("tab:orange", "-"), "gradient_boosting": ("tab:purple", ":"),
               "mlp": ("tab:red", "-.")}
    for eje, (e, g) in zip(ejes.ravel(), p.groupby("empresa")):
        g = g.set_index("fecha_objetivo")
        eje.bar(g.index, np.sqrt(g["rv_objetivo"]), width=4, color="lightgray",
                label="volatilidad realizada")
        for m, (c, ls) in estilos.items():
            eje.plot(g.index, np.sqrt(g[m]), color=c, ls=ls, lw=1, label=m)
        eje.set_title(e, fontsize=9)
        eje.tick_params(labelsize=7)
    ejes[0, 0].legend(fontsize=7, ncol=2)
    ejes[0, 0].set_ylabel("Volatilidad semanal (%)")
    fig.suptitle("Validación 2024: volatilidad de la semana siguiente (raíz de la RV) y pronósticos",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(RUTA_GRAFICOS / "semanal_volatilidad_validacion.png", dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    r = ejecutar()
    pd.set_option("display.width", 250)
    for clave in ("filas", "volatilidad", "pruebas", "volatilidad_por_empresa", "rendimiento",
                  "har", "hiperparametros"):
        print(f"--- {clave}")
        print(r[clave].round(4).to_string(index=False))
