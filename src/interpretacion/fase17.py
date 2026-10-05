"""
fase17.py — Interpretación económica (plan DEC-039, resultados DEC-040)
=======================================================================

Análisis explicativos (no confirmatorios). A–E usan solo entrenamiento y
validación; F resume resultados ya publicados.

    A  Características que explican los pesos (rebalanceos de la Fase 14).
    B  Beta simple frente a beta de Dimson (negociación no sincrónica).
    C  Volatilidad ex ante frente a ex post (error de estimación).
    D  Autocorrelación de primer orden frente a iliquidez.
    E  Ecopetrol y el petróleo Brent.
    F  Contexto: IBR y rendimiento anual del 1/N.

Ejecutar:  python -m src.interpretacion.fase17
"""

import logging

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.covariance import LedoitWolf

from config.environment import RUTA_GRAFICOS, RUTA_PARTICIONES, RUTA_RESULTADOS
from config.settings import DIAS_BURSATILES_ANIO
from src.backtesting import motor
from src.data.externos import ibr_efectiva_anual
from src.portfolio.markowitz import log_a_simple, seleccionar_universo_liquido
from src.preprocessing.split import cargar_entrenamiento_validacion

logger = logging.getLogger(__name__)

RUTA = RUTA_RESULTADOS / "fase17"
VENTANA = 252
ESTRATEGIAS_OPT = ["min_var_muestral", "min_var_lw", "min_cvar", "paridad_riesgo"]


def _datos():
    rend = cargar_entrenamiento_validacion(RUTA_PARTICIONES, "rendimientos_log")
    ext = cargar_entrenamiento_validacion(RUTA_PARTICIONES, "externos")
    tasas = cargar_entrenamiento_validacion(RUTA_PARTICIONES, "tasas")
    return rend, ext, tasas


def _pesos_fase14():
    p = pd.read_csv(RUTA_RESULTADOS / "fase14_pesos.csv", parse_dates=["fecha"])
    return p[p["universo"] == "9_empresas"]


def _caracteristicas(ventana):
    """Volatilidad, correlación media con las demás, % sin cambio y media."""
    completos = ventana.dropna(how="any")
    corr = completos.corr().to_numpy().copy()
    np.fill_diagonal(corr, np.nan)
    return pd.DataFrame({
        "volatilidad": completos.std() * np.sqrt(DIAS_BURSATILES_ANIO),
        "correlacion_media": np.nanmean(corr, axis=1),
        "pct_sin_cambio": (completos == 0).mean(),
        "rendimiento_medio": completos.mean() * DIAS_BURSATILES_ANIO,
    })


# --- A ----------------------------------------------------------------------------------

def a_pesos(rend_simple, iliquidos):
    pesos = _pesos_fase14()
    empresas = list(rend_simple.columns)
    filas, rho = [], []
    for (estrategia, fecha), g in pesos.groupby(["estrategia", "fecha"]):
        w = g.iloc[0][empresas].astype(float)
        car = _caracteristicas(motor.ventana_estimacion(rend_simple, fecha, VENTANA))
        filas.append({"estrategia": estrategia, "fecha": fecha,
                      "peso_iliquidas": float(w[iliquidos].sum())})
        if estrategia == "igual":
            continue
        for c in car.columns:
            r = stats.spearmanr(w.to_numpy(), car[c].to_numpy()).statistic
            rho.append({"estrategia": estrategia, "fecha": fecha, "caracteristica": c, "spearman": r})
    rho = pd.DataFrame(rho)
    resumen = (rho.groupby(["estrategia", "caracteristica"])["spearman"]
               .agg(spearman_medio="mean", fraccion_negativa=lambda x: float((x < 0).mean()))
               .reset_index())
    ilq = (pd.DataFrame(filas).groupby("estrategia")["peso_iliquidas"]
           .agg(peso_medio="mean", minimo="min", maximo="max").reset_index())
    medios = pesos.groupby("estrategia")[empresas].mean().T
    return resumen, ilq, medios.rename_axis("empresa").reset_index()


# --- B ----------------------------------------------------------------------------------------

def _ols(y, X):
    X = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return beta[1:]


def b_dimson(rend_log_train, iliquidos):
    filas = []
    for e in rend_log_train.columns:
        mercado = rend_log_train.drop(columns=e).mean(axis=1)
        d = pd.DataFrame({"r": rend_log_train[e], "m0": mercado,
                          "m_1": mercado.shift(1), "m1": mercado.shift(-1)}).dropna()
        simple = _ols(d["r"].to_numpy(), d[["m0"]].to_numpy())[0]
        dimson = _ols(d["r"].to_numpy(), d[["m_1", "m0", "m1"]].to_numpy())
        filas.append({"empresa": e, "iliquida_train": e in iliquidos,
                      "pct_sin_cambio_train": float((rend_log_train[e].dropna() == 0).mean()),
                      "beta_simple": simple, "beta_dimson": float(dimson.sum()),
                      "beta_rezago_menos1": dimson[0], "beta_rezago_mas1": dimson[2],
                      "n": len(d)})
    t = pd.DataFrame(filas)
    t["subestimacion_pct"] = 100 * (1 - t["beta_simple"] / t["beta_dimson"])
    rho = stats.spearmanr(t["pct_sin_cambio_train"], t["subestimacion_pct"])
    return t, {"spearman_iliquidez_vs_subestimacion": rho.statistic, "pvalor": rho.pvalue}


# --- C --------------------------------------------------------------------------------------------

def c_error_estimacion(rend_simple):
    pesos = _pesos_fase14()
    empresas = list(rend_simple.columns)
    fechas = sorted(pesos["fecha"].unique())
    filas = []
    for i, fecha in enumerate(fechas[:-1]):
        ventana = motor.ventana_estimacion(rend_simple, pd.Timestamp(fecha), VENTANA).dropna(how="any")
        cov_m = ventana.cov().to_numpy() * DIAS_BURSATILES_ANIO
        cov_lw = LedoitWolf().fit(ventana.to_numpy()).covariance_ * DIAS_BURSATILES_ANIO
        siguiente = rend_simple.loc[(rend_simple.index > fecha) & (rend_simple.index <= fechas[i + 1]),
                                    empresas].dropna(how="any")
        if len(siguiente) < 10:
            continue
        for estrategia, g in pesos[pesos["fecha"] == fecha].groupby("estrategia"):
            w = g.iloc[0][empresas].astype(float).to_numpy()
            cov = cov_lw if estrategia in ("min_var_lw", "paridad_riesgo") else cov_m
            ex_ante = float(np.sqrt(w @ cov @ w))
            ex_post = float((siguiente.to_numpy() @ w).std(ddof=1) * np.sqrt(DIAS_BURSATILES_ANIO))
            filas.append({"estrategia": estrategia, "fecha": fecha, "vol_ex_ante": ex_ante,
                          "vol_ex_post": ex_post, "razon": ex_post / ex_ante})
    d = pd.DataFrame(filas)
    resumen = d.groupby("estrategia").agg(
        vol_ex_ante_media=("vol_ex_ante", "mean"), vol_ex_post_media=("vol_ex_post", "mean"),
        razon_mediana=("razon", "median"), fraccion_subestima=("razon", lambda x: float((x > 1).mean())),
        n_meses=("razon", "size")).reset_index()
    return resumen, d


# --- D ----------------------------------------------------------------------------------------------

def d_autocorrelacion(rend_log_train, iliquidos):
    filas = []
    for e in rend_log_train.columns:
        s = rend_log_train[e]
        par = pd.DataFrame({"r": s, "r1": s.shift(1)}).dropna()
        ac = float(np.corrcoef(par["r"], par["r1"])[0, 1])
        filas.append({"empresa": e, "iliquida_train": e in iliquidos,
                      "pct_sin_cambio_train": float((s.dropna() == 0).mean()),
                      "autocorrelacion_1": ac, "ic95_aprox": 1.96 / np.sqrt(len(par))})
    t = pd.DataFrame(filas)
    rho = stats.spearmanr(t["pct_sin_cambio_train"], t["autocorrelacion_1"])
    return t, {"spearman_iliquidez_vs_autocorrelacion": rho.statistic, "pvalor": rho.pvalue}


# --- E ------------------------------------------------------------------------------------------------

def e_petroleo(rend_log, externos):
    brent = np.log(externos["Brent"].dropna()).diff().dropna()
    filas = []
    for bloque, r in rend_log.items():
        b = brent[(brent.index >= r.index.min() - pd.Timedelta(days=10)) & (brent.index <= r.index.max())]
        for e in r.columns:
            s = r[e].dropna()
            mismo = b.reindex(s.index)
            # Brent del último día con dato estrictamente anterior.
            izq = pd.DataFrame({"Date": s.index})
            der = b.rename("brent").reset_index().rename(columns={"index": "Date"})
            der.columns = ["Date", "brent"]
            ant = pd.merge_asof(izq, der, on="Date", allow_exact_matches=False,
                                tolerance=pd.Timedelta(days=7))["brent"].to_numpy()
            for nombre, x in (("mismo_dia", mismo.to_numpy()), ("dia_anterior", ant)):
                ok = ~np.isnan(x)
                filas.append({"bloque": bloque, "empresa": e, "brent": nombre, "n": int(ok.sum()),
                              "correlacion": float(np.corrcoef(s.to_numpy()[ok], x[ok])[0, 1]),
                              "beta": float(_ols(s.to_numpy()[ok], x[ok][:, None])[0])})
    return pd.DataFrame(filas)


# --- F ---------------------------------------------------------------------------------------------------

def f_contexto(tasas):
    ibr = pd.concat([tasas["train"], tasas["validacion"]]).iloc[:, 0]
    trayectoria = pd.DataFrame([
        {"dato": "IBR overnight nominal mínimo (2020–2024)", "valor": float(ibr.min()),
         "fecha": ibr.idxmin().date()},
        {"dato": "IBR overnight nominal máximo (2020–2024)", "valor": float(ibr.max()),
         "fecha": ibr.idxmax().date()},
        {"dato": "IBR overnight nominal al cierre de 2024", "valor": float(ibr.iloc[-1]),
         "fecha": ibr.index[-1].date()},
    ])
    ibr_anual = (ibr.groupby(ibr.index.year).mean()).rename("ibr_nominal_medio_%").reset_index()
    ibr_anual["ibr_efectiva_media_%"] = 100 * ibr_efectiva_anual(ibr).groupby(ibr.index.year).mean().to_numpy()
    m14 = pd.read_csv(RUTA_RESULTADOS / "fase14_metricas.csv")
    m15 = pd.read_csv(RUTA_RESULTADOS / "fase15" / "final" / "con_regla" / "portafolios_metricas.csv")
    filas = []
    for m, periodos in ((m14, ("2021-2023", "2024")), (m15, ("2025", "2026"))):
        for per in periodos:
            for est in ("igual", "ibr"):
                fila = m[(m["universo"] == "9_empresas") & (m["estrategia"] == est) & (m["periodo"] == per)
                         & (m["costo"].isin(["20pb", "-"])) & (m["frecuencia"].isin(["mensual", "-"]))]
                filas.append({"periodo": per, "serie": "1/N (9 empresas)" if est == "igual" else "IBR",
                              "retorno_anual": float(fila["retorno_anual"].iloc[0])})
    rendimiento = pd.DataFrame(filas).pivot(index="periodo", columns="serie", values="retorno_anual").reset_index()
    return trayectoria, ibr_anual, rendimiento


# --- Ejecución ---------------------------------------------------------------------------------------------

def ejecutar_fase17(guardar=True):
    rend, ext, tasas = _datos()
    rend_log = pd.concat([rend["train"], rend["validacion"]])
    rend_simple = log_a_simple(rend_log)
    liquidos, iliquidos, _ = seleccionar_universo_liquido(rend["train"])

    a_rho, a_ilq, a_medios = a_pesos(rend_simple, iliquidos)
    b_tabla, b_rho = b_dimson(rend["train"], iliquidos)
    c_res, c_det = c_error_estimacion(rend_simple)
    d_tabla, d_rho = d_autocorrelacion(rend["train"], iliquidos)
    e_tabla = e_petroleo({"train": rend["train"], "validacion": rend["validacion"]},
                         pd.concat([ext["train"], ext["validacion"]]))
    f_tray, f_ibr, f_rend = f_contexto(tasas)
    res = {"a_spearman_pesos": a_rho, "a_peso_iliquidas": a_ilq, "a_pesos_medios": a_medios,
           "b_dimson": b_tabla, "b_resumen": pd.DataFrame([b_rho]),
           "c_error_estimacion": c_res, "c_detalle": c_det,
           "d_autocorrelacion": d_tabla, "d_resumen": pd.DataFrame([d_rho]),
           "e_petroleo": e_tabla, "f_ibr_trayectoria": f_tray, "f_ibr_anual": f_ibr,
           "f_rendimiento_vs_ibr": f_rend}
    if guardar:
        RUTA.mkdir(parents=True, exist_ok=True)
        for clave, df in res.items():
            df.to_csv(RUTA / f"{clave}.csv", index=False)
        _graficar(b_tabla, c_res, a_medios)
    return res


def _graficar(b, c, medios):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    RUTA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    fig, (e1, e2, e3) = plt.subplots(1, 3, figsize=(17, 5))
    b = b.sort_values("pct_sin_cambio_train")
    x = np.arange(len(b))
    e1.bar(x - 0.2, b["beta_simple"], 0.4, label="beta simple", color="lightgray")
    e1.bar(x + 0.2, b["beta_dimson"], 0.4, label="beta de Dimson", color="black")
    e1.set_xticks(x, [f"{n}\n({p:.0%} sin cambio)" for n, p in zip(b["empresa"], b["pct_sin_cambio_train"])],
                  rotation=45, ha="right", fontsize=7)
    e1.set_title("B. Beta simple frente a beta de Dimson\n(ordenadas de más a menos líquida)", fontsize=9)
    e1.legend(fontsize=7)

    m = medios.set_index("empresa")[["igual", "min_var_muestral", "min_cvar", "paridad_riesgo"]]
    m = m.loc[b["empresa"]]
    m.plot(kind="bar", ax=e2, width=0.8, color=["black", "tab:blue", "tab:red", "tab:green"])
    e2.set_title("A. Peso medio por empresa (Fase 14, 2021–2024)\nordenadas de más a menos líquida", fontsize=9)
    e2.tick_params(axis="x", labelsize=7, rotation=45)
    e2.legend(fontsize=7)

    c = c.set_index("estrategia").loc[["igual", "paridad_riesgo", "min_var_lw", "min_var_muestral", "min_cvar"]]
    e3.bar(c.index, c["vol_ex_ante_media"] * 100, 0.4, align="edge", label="ex ante (estimada)", color="lightgray")
    e3.bar(c.index, c["vol_ex_post_media"] * 100, -0.4, align="edge", label="ex post (mes siguiente)", color="tab:red")
    e3.set_ylabel("Volatilidad anual media (%)")
    e3.set_title("C. Riesgo estimado frente a riesgo realizado", fontsize=9)
    e3.tick_params(axis="x", labelsize=7, rotation=30)
    e3.legend(fontsize=7)
    fig.suptitle("Fase 17: interpretación económica (entrenamiento y validación, 2020–2024)", fontsize=10)
    fig.tight_layout()
    fig.savefig(RUTA_GRAFICOS / "fase17_interpretacion.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    r = ejecutar_fase17()
    pd.set_option("display.width", 220)
    for k, v in r.items():
        if k in ("c_detalle", "e_petroleo"):
            continue
        print(f"--- {k}\n{v.round(4).to_string(index=False)}")
    e = r["e_petroleo"]
    print("--- e_petroleo (correlaciones)")
    print(e.pivot_table(index="empresa", columns=["bloque", "brent"], values="correlacion").round(3).to_string())
