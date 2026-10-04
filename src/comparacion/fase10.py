"""
fase10.py — Ejecución de la Fase 10: comparación de modelos
============================================================

Consolida los pronósticos de VALIDACIÓN de las Fases 7 a 9 (DEC-027):

    Media condicional (r_{t+1}), mismas 1 631 filas para todos:
        cero, media de entrenamiento, ARIMA, Random Forest, Gradient
        Boosting, MLP y LSTM.
        - Pérdida cuadrática promediada por fecha (las empresas de un mismo
          día no son independientes) -> MCS, Diebold-Mariano y R²_OS con
          intervalo bootstrap por bloques.
        - Por empresa: Diebold-Mariano frente a la media con corrección de
          Holm sobre toda la familia de pruebas.
        - Acierto direccional y prueba de Pesaran-Timmermann.
    Varianza condicional: GARCH(1,1), EWMA y varianza constante (QLIKE),
        MCS con las 4 empresas líquidas y Holm por empresa.
    Complejidad: parámetros y método de ajuste de cada modelo.

Requiere haber ejecutado las Fases 7, 8 y 9 (lee sus CSV de resultados).
No toca el bloque de prueba.

Ejecutar:  python -m src.comparacion.fase10
"""

import logging

import numpy as np
import pandas as pd

from config.environment import RUTA_GRAFICOS, RUTA_PARTICIONES, RUTA_RESULTADOS
from config.settings import SEMILLA_ALEATORIA
from src.comparacion import estadistica as est
from src.econometrics import evaluacion
from src.econometrics.garch import ESCALA
from src.portfolio.markowitz import seleccionar_universo_liquido
from src.preprocessing.split import cargar_particion

logger = logging.getLogger(__name__)

MODELOS_MEDIA = ["cero", "media_train", "arima", "random_forest",
                 "gradient_boosting", "mlp", "lstm"]
APRENDIDOS = ["arima", "random_forest", "gradient_boosting", "mlp", "lstm"]
MODELOS_VARIANZA = ["garch", "ewma", "constante"]
ALFA_MCS = 0.10
OPCIONES_BOOT = dict(n_remuestras=2000, largo_bloque=10, semilla=SEMILLA_ALEATORIA)


def _leer(nombre, **kw):
    ruta = RUTA_RESULTADOS / nombre
    if not ruta.exists():
        raise FileNotFoundError(f"Falta {ruta}: ejecute antes las Fases 7, 8 y 9.")
    return pd.read_csv(ruta, **kw)


def _perdida_por_fecha(df, columna_fecha, columnas_perdida):
    """Promedio por fecha de las pérdidas (una serie de tiempo por modelo)."""
    return df.groupby(columna_fecha)[columnas_perdida].mean().sort_index()


# --- Media condicional -----------------------------------------------------------

def comparar_media(pron, iliquidos):
    perdidas = pron[["fecha_objetivo", "empresa"]].copy()
    for m in MODELOS_MEDIA:
        perdidas[m] = (pron["objetivo"] - pron[m]) ** 2
    por_fecha = _perdida_por_fecha(perdidas, "fecha_objetivo", MODELOS_MEDIA)

    mcs = est.model_confidence_set(por_fecha, alfa=ALFA_MCS, **OPCIONES_BOOT)
    filas = []
    for m in MODELOS_MEDIA:
        r2 = est.r2_fuera_de_muestra(por_fecha[m], por_fecha["media_train"],
                                     **OPCIONES_BOOT)
        dm = evaluacion.diebold_mariano(por_fecha[m], por_fecha["media_train"]) \
            if m != "media_train" else {"dm_estadistico": np.nan, "dm_pvalor": np.nan}
        pt = est.pesaran_timmermann(pron["objetivo"], pron[m]) if m != "cero" else \
            {"acierto": np.nan, "pt_estadistico": np.nan, "pt_pvalor": np.nan, "n": np.nan}
        filas.append({
            "modelo": m,
            "rmse": evaluacion.rmse(pron["objetivo"], pron[m]),
            "mae": evaluacion.mae(pron["objetivo"], pron[m]),
            "r2_os_vs_media": r2["r2_os"], "r2_ic95_inf": r2["ic_inf"],
            "r2_ic95_sup": r2["ic_sup"],
            "dm_vs_media": dm["dm_estadistico"], "dm_pvalor_vs_media": dm["dm_pvalor"],
            "acierto_direccional": pt["acierto"], "pt_pvalor": pt["pt_pvalor"],
            "n_direccional": pt["n"],
        })
    agregado = pd.DataFrame(filas).merge(mcs[["modelo", "pvalor_mcs", "en_mcs"]],
                                         on="modelo")
    # Familias de pruebas: DM frente a la media y Pesaran-Timmermann.
    agregado["dm_pvalor_holm"] = est.holm(agregado["dm_pvalor_vs_media"]).to_numpy()
    agregado["pt_pvalor_holm"] = est.holm(agregado["pt_pvalor"]).to_numpy()

    # Por empresa: familia de pruebas (modelos aprendidos y cero) x empresas.
    pruebas = []
    for empresa, g in pron.groupby("empresa", sort=False):
        y = g["objetivo"].reset_index(drop=True)
        ref = evaluacion.perdida_cuadratica(y, g["media_train"].reset_index(drop=True))
        for m in APRENDIDOS + ["cero"]:
            perd = evaluacion.perdida_cuadratica(y, g[m].reset_index(drop=True))
            dm = evaluacion.diebold_mariano(perd, ref)
            pruebas.append({"empresa": empresa, "iliquida_train": empresa in iliquidos,
                            "modelo": m, "n": len(g),
                            "rmse_modelo": float(np.sqrt(perd.mean())),
                            "rmse_media": float(np.sqrt(ref.mean())),
                            "dm_estadistico": dm["dm_estadistico"],
                            "pvalor": dm["dm_pvalor"]})
    por_empresa = pd.DataFrame(pruebas)
    por_empresa["pvalor_holm"] = est.holm(por_empresa["pvalor"]).to_numpy()
    por_empresa["mejor_que_media_holm_5pct"] = ((por_empresa["pvalor_holm"] < 0.05)
                                                & (por_empresa["dm_estadistico"] < 0))
    por_empresa["peor_que_media_holm_5pct"] = ((por_empresa["pvalor_holm"] < 0.05)
                                               & (por_empresa["dm_estadistico"] > 0))
    return agregado.sort_values("rmse").reset_index(drop=True), por_empresa, mcs


# --- Varianza condicional ---------------------------------------------------------

def comparar_varianza(pron_var, liquidos, iliquidos):
    proxy = (pron_var["rendimiento"] * ESCALA) ** 2
    perdidas = pron_var[["Date", "empresa"]].copy()
    for m in MODELOS_VARIANZA:
        h = pron_var[f"varianza_{m}"]
        perdidas[m] = np.log(h) + proxy / h
    liq = perdidas[perdidas["empresa"].isin(liquidos)]
    por_fecha = _perdida_por_fecha(liq, "Date", MODELOS_VARIANZA)
    mcs = est.model_confidence_set(por_fecha, alfa=ALFA_MCS, **OPCIONES_BOOT)
    mcs.insert(0, "universo", "liquidas")

    pruebas = []
    for empresa, g in perdidas.groupby("empresa", sort=False):
        for ref in ("ewma", "constante"):
            dm = evaluacion.diebold_mariano(g["garch"].reset_index(drop=True),
                                            g[ref].reset_index(drop=True))
            pruebas.append({"empresa": empresa, "iliquida_train": empresa in iliquidos,
                            "comparacion": f"garch_vs_{ref}",
                            "qlike_garch": float(g["garch"].mean()),
                            "qlike_referencia": float(g[ref].mean()),
                            "dm_estadistico": dm["dm_estadistico"],
                            "pvalor": dm["dm_pvalor"]})
    por_empresa = pd.DataFrame(pruebas)
    por_empresa["pvalor_holm"] = est.holm(por_empresa["pvalor"]).to_numpy()
    return mcs, por_empresa


# --- Complejidad -------------------------------------------------------------------

def tabla_complejidad():
    from src.neural_networks import redes

    arima = _leer("fase7_arima.csv")
    n_arima = int((arima["p"] + arima["q"] + 2).sum())    # AR + MA + constante + varianza
    hip8 = _leer("fase8_hiperparametros.csv").set_index("modelo")
    hip9 = _leer("fase9_hiperparametros.csv").set_index("modelo")
    n_var = len(_leer("fase8_importancia_permutacion.csv")
                .query("modelo == 'random_forest'"))       # variables + indicadores
    ocultas = tuple(int(x) for x in hip9.loc["mlp", "ocultas"].strip("()").split(",") if x.strip())
    mlp = redes.MLP(n_var, ocultas=ocultas)
    lstm = redes.LSTMRed(5, 9, oculta=int(hip9.loc["lstm", "oculta"]))
    contar = lambda red: int(sum(p.numel() for p in red.parameters()))
    rf, gb = hip8.loc["random_forest"], hip8.loc["gradient_boosting"]
    filas = [
        ("cero", "Ninguno", 0, "—", "Muy baja"),
        ("media_train", "Media de entrenamiento por empresa", 9, "—", "Muy baja"),
        ("arima", "ARIMA(p,0,q) por empresa, máxima verosimilitud", n_arima,
         "Orden por BIC en entrenamiento", "Baja"),
        ("random_forest", f"300 árboles, profundidad ≤ {int(rf['max_depth'])}, "
                          f"hoja ≥ {int(rf['min_samples_leaf'])}", np.nan,
         "Validación cruzada temporal en entrenamiento", "Media"),
        ("gradient_boosting", f"300 iteraciones, profundidad ≤ {int(gb['max_depth'])}, "
                              f"tasa {gb['learning_rate']}", np.nan,
         "Validación cruzada temporal en entrenamiento", "Media"),
        ("mlp", f"Capas ocultas {ocultas}, 5 semillas", contar(mlp),
         "Final de entrenamiento (parada temprana)", "Alta"),
        ("lstm", f"LSTM {int(hip9.loc['lstm', 'oculta'])} unidades, 30 días, 5 semillas",
         contar(lstm), "Final de entrenamiento (parada temprana)", "Alta"),
    ]
    return pd.DataFrame(filas, columns=["modelo", "especificacion",
                                        "parametros_por_red_o_total",
                                        "seleccion_hiperparametros", "complejidad"])


# --- Ejecución ---------------------------------------------------------------------

def ejecutar_fase10(guardar=True):
    pron = _leer("fase9_pronosticos_validacion.csv", parse_dates=["fecha_objetivo"])
    pron_var = _leer("fase7_pronosticos_validacion.csv", parse_dates=["Date"])
    faltan = [c for c in MODELOS_MEDIA + ["objetivo"] if c not in pron.columns]
    if faltan or pron[MODELOS_MEDIA + ["objetivo"]].isna().any().any():
        raise ValueError(f"Pronósticos de media incompletos (faltan {faltan} o hay NaN).")
    rend_train = cargar_particion(RUTA_PARTICIONES, "rendimientos_log", "train")
    liquidos, iliquidos, _ = seleccionar_universo_liquido(rend_train)

    media, media_emp, mcs_media = comparar_media(pron, iliquidos)
    mcs_var, var_emp = comparar_varianza(pron_var, liquidos, iliquidos)
    complejidad = tabla_complejidad()
    res = {"media": media, "media_por_empresa": media_emp, "mcs_media": mcs_media,
           "mcs_varianza": mcs_var, "varianza_por_empresa": var_emp,
           "complejidad": complejidad}
    if guardar:
        RUTA_RESULTADOS.mkdir(parents=True, exist_ok=True)
        for clave, archivo in (("media", "fase10_media.csv"),
                               ("media_por_empresa", "fase10_media_por_empresa.csv"),
                               ("mcs_varianza", "fase10_varianza_mcs.csv"),
                               ("varianza_por_empresa", "fase10_varianza_por_empresa.csv"),
                               ("complejidad", "fase10_complejidad.csv")):
            res[clave].to_csv(RUTA_RESULTADOS / archivo, index=False)
        _graficar(media, mcs_var)
    return res


def _graficar(media, mcs_var):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    RUTA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    fig, (a, b) = plt.subplots(1, 2, figsize=(13, 4.8),
                               gridspec_kw={"width_ratios": [1.4, 1]})
    d = media[media["modelo"] != "media_train"].sort_values("r2_os_vs_media")
    y = np.arange(len(d))
    color = np.where(d["en_mcs"], "black", "gray")
    a.errorbar(d["r2_os_vs_media"] * 100, y,
               xerr=[(d["r2_os_vs_media"] - d["r2_ic95_inf"]) * 100,
                     (d["r2_ic95_sup"] - d["r2_os_vs_media"]) * 100],
               fmt="none", ecolor="lightgray", capsize=3)
    a.scatter(d["r2_os_vs_media"] * 100, y, c=color, zorder=3)
    a.axvline(0, color="tab:red", lw=1)
    a.set_yticks(y, d["modelo"])
    a.set_xlabel("R² fuera de muestra frente a la media de entrenamiento (%)")
    a.set_title("Rendimiento del día siguiente — validación 2024\n"
                "(IC 95 % bootstrap por bloques; negro = en el MCS al 10 %)", fontsize=9)
    v = mcs_var.sort_values("perdida_media")
    b.barh(v["modelo"], v["perdida_media"], color=np.where(v["en_mcs"], "black", "gray"))
    b.set_xlim(v["perdida_media"].min() * 0.97, v["perdida_media"].max() * 1.01)
    b.set_xlabel("QLIKE medio (menor es mejor)")
    b.set_title("Volatilidad — 4 acciones líquidas\n(negro = en el MCS al 10 %)", fontsize=9)
    fig.tight_layout()
    fig.savefig(RUTA_GRAFICOS / "fase10_comparacion.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    r = ejecutar_fase10()
    pd.set_option("display.width", 250)
    print(r["media"].round(5).to_string(index=False))
    e = r["media_por_empresa"]
    print("Pruebas por empresa:", len(e), "| p<0.05 sin corregir:", int((e["pvalor"] < 0.05).sum()),
          "| significativas tras Holm:", int((e["pvalor_holm"] < 0.05).sum()))
    print(e[e["pvalor"] < 0.05].round(4).to_string(index=False))
    print(r["mcs_varianza"].round(4).to_string(index=False))
    print(r["varianza_por_empresa"].round(4).to_string(index=False))
    print(r["complejidad"].to_string(index=False))
