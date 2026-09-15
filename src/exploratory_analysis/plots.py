"""
plots.py — Gráficos del análisis exploratorio
==============================================

Genera y guarda los gráficos académicos de la Fase 3 en
``resultados/graficos/``. Todos los gráficos incluyen título, etiquetas,
fechas formateadas y leyenda cuando corresponde.

Para ejecutar en un entorno sin pantalla se usa el backend "Agg".
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from config.settings import ESTILO_GRAFICOS, TAMANO_FIGURA_DEFAULT, PALETA_COLORES
from config.environment import RUTA_GRAFICOS

sns.set_palette(PALETA_COLORES)
try:
    plt.style.use(ESTILO_GRAFICOS)
except Exception:
    plt.style.use("default")
plt.rcParams["figure.figsize"] = TAMANO_FIGURA_DEFAULT


def _guardar(fig, nombre_archivo):
    """Guarda una figura y cierra para liberar memoria."""
    ruta = RUTA_GRAFICOS / nombre_archivo
    RUTA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(ruta, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(ruta)


def _grid(n_empresas):
    """Calcula una rejilla de subplots razonable para n empresas."""
    columnas = 3
    filas = int(np.ceil(n_empresas / columnas))
    return filas, columnas


def plot_precios(df_precios, nombre_archivo="01_precios.png"):
    """Gráfico 1: precio de cada empresa a lo largo del tiempo."""
    filas, columnas = _grid(df_precios.shape[1])
    fig, ejes = plt.subplots(filas, columnas, figsize=(15, 3 * filas),
                             sharex=True)
    ejes = np.array(ejes).flatten()
    for i, (columna, ax) in enumerate(zip(df_precios.columns, ejes)):
        ax.plot(df_precios.index, df_precios[columna], linewidth=1.0)
        ax.set_title(columna, fontsize=10)
        ax.set_ylabel("Precio (COP)")
        ax.grid(True, alpha=0.3)
    for ax in ejes[df_precios.shape[1]:]:
        ax.axis("off")
    fig.suptitle("Precio ajustado por empresa (2020 – presente)",
                 fontsize=14, y=1.02)
    fig.autofmt_xdate()
    return _guardar(fig, nombre_archivo)


def plot_rendimientos(df_rendimientos, nombre_archivo="02_rendimientos_log.png"):
    """Gráfico 2: rendimientos logarítmicos de cada empresa."""
    filas, columnas = _grid(df_rendimientos.shape[1])
    fig, ejes = plt.subplots(filas, columnas, figsize=(15, 3 * filas),
                             sharex=True)
    ejes = np.array(ejes).flatten()
    for i, (columna, ax) in enumerate(zip(df_rendimientos.columns, ejes)):
        serie = df_rendimientos[columna].dropna()
        ax.plot(serie.index, serie.values, linewidth=0.6)
        ax.set_title(columna, fontsize=10)
        ax.set_ylabel("r_t (log)")
        ax.grid(True, alpha=0.3)
    for ax in ejes[df_rendimientos.shape[1]:]:
        ax.axis("off")
    fig.suptitle("Rendimientos logarítmicos diarios por empresa",
                 fontsize=14, y=1.02)
    fig.autofmt_xdate()
    return _guardar(fig, nombre_archivo)


def plot_distribucion(df_rendimientos, nombre_archivo="03_distribucion_rendimientos.png"):
    """Gráfico 3: distribución de rendimientos (histograma + normal teórica)."""
    filas, columnas = _grid(df_rendimientos.shape[1])
    fig, ejes = plt.subplots(filas, columnas, figsize=(15, 3 * filas))
    ejes = np.array(ejes).flatten()
    for i, (columna, ax) in enumerate(zip(df_rendimientos.columns, ejes)):
        serie = df_rendimientos[columna].dropna()
        ax.hist(serie, bins=60, density=True, alpha=0.7, color=sns.color_palette(PALETA_COLORES)[0])
        x = np.linspace(serie.min(), serie.max(), 200)
        ax.plot(x, 1 / (serie.std() * np.sqrt(2 * np.pi)) * np.exp(
            -(x - serie.mean()) ** 2 / (2 * serie.std() ** 2)), "r-", linewidth=1.0)
        ax.set_title(columna, fontsize=10)
        ax.set_xlabel("Rendimiento logarítmico")
        ax.set_ylabel("Densidad")
    for ax in ejes[df_rendimientos.shape[1]:]:
        ax.axis("off")
    fig.suptitle("Distribución de rendimientos logarítmicos (vs. normal)",
                 fontsize=14, y=1.02)
    return _guardar(fig, nombre_archivo)


def plot_volatilidad(df_rendimientos, dias_anio=252,
                     nombre_archivo="04_volatilidad.png"):
    """Gráfico 4: volatilidad anualizada por activo (barra)."""
    vol = df_rendimientos.std() * np.sqrt(dias_anio)
    fig, ax = plt.subplots(figsize=TAMANO_FIGURA_DEFAULT)
    colores = sns.color_palette(PALETA_COLORES, len(vol))
    ax.bar(range(len(vol)), vol.values, tick_label=vol.index, color=colores)
    ax.set_title("Volatilidad anualizada por activo "
                 r"($\sigma_{anual}=\sigma_{diaria}\sqrt{252}$)")
    ax.set_ylabel("Volatilidad anualizada")
    ax.set_xlabel("Activo")
    ax.grid(True, axis="y", alpha=0.3)
    fig.autofmt_xdate()
    return _guardar(fig, nombre_archivo)


def plot_matriz_correlacion(matriz_corr, nombre_archivo="05_matriz_correlacion.png"):
    """Gráfico 5: heatmap de la matriz de correlación."""
    fig, ax = plt.subplots(figsize=(11, 9))
    sns.heatmap(matriz_corr, annot=True, fmt=".2f", cmap="coolwarm",
                vmin=-1, vmax=1, square=True, ax=ax,
                cbar_kws={"label": "Correlación de Pearson"})
    ax.set_title("Matriz de correlación entre rendimientos")
    return _guardar(fig, nombre_archivo)


def plot_imputacion_kalman(empresa, serie_original, serie_imputada, bandera,
                           ventana=20, nombre_archivo=None):
    """Gráfico "antes/después" de la imputación de Kalman para una serie.

    Muestra la serie original (con el hueco NaN) y la serie reconstruida,
    resaltando el(los) punto(s) imputados, en una ventana alrededor de ellos.

    Parámetros:
        empresa: nombre del activo.
        serie_original: pd.Series original (puede contener NaN).
        serie_imputada: pd.Series tras la imputación.
        bandera: pd.Series booleana (True donde el valor fue imputado).
        ventana: número de días de contexto alrededor del punto imputado.
        nombre_archivo: nombre del PNG (se guarda en graficos/kalman/).
    """
    fechas_imputadas = bandera.index[bandera]
    if len(fechas_imputadas) == 0:
        return None

    centro = fechas_imputadas.min()
    inicio = centro - pd.Timedelta(days=ventana)
    fin = centro + pd.Timedelta(days=ventana)

    orig = serie_original.loc[inicio:fin]
    imp = serie_imputada.loc[inicio:fin]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(imp.index, imp.values, label="Serie reconstruida (Kalman)",
            color="tab:blue", linewidth=1.2)
    ax.plot(orig.index, orig.values, label="Serie original", color="tab:gray",
            linewidth=1.0, linestyle="--", alpha=0.8)
    for f in fechas_imputadas:
        if inicio <= f <= fin:
            ax.scatter(f, serie_imputada.loc[f], color="red", zorder=5, s=40,
                       label="Valor imputado" if f == fechas_imputadas[0] else None)
    ax.set_title(f"Imputación Kalman — {empresa}", fontsize=13)
    ax.set_ylabel("Adj Close (COP)")
    ax.set_xlabel("Fecha")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()

    if nombre_archivo is None:
        nombre_archivo = f"{empresa.replace(' ', '_')}_kalman.png"
    ruta = RUTA_GRAFICOS / "kalman"
    ruta.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(ruta / nombre_archivo, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(ruta / nombre_archivo)