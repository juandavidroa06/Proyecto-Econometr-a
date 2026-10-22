"""
reproducir.py — Reejecuta las fases y comprueba que reproducen lo publicado
===========================================================================

Corre en orden las fases que generan resultados (6 a 14, la extensión
semanal, 16, 17 y 21), compara cada CSV con la versión del último commit
(``git show HEAD:<archivo>``) y al final restaura los archivos publicados:
no deja cambios. No ejecuta la evaluación final (Fase 15), que se hace una
sola vez (DEC-034), ni descarga datos.

Una tabla reproduce si tiene la misma forma, las mismas columnas, las mismas
columnas no numéricas y una diferencia numérica máxima <= TOLERANCIA (el
optimizador SLSQP de la Fase 6 reproduce los pesos a ~1e-8, DEC-021).

Ejecutar:
    python -m src.reproducir             # todas las fases
    python -m src.reproducir --rapido    # sin las fases lentas (9, 16 y 21)
"""

import argparse
import io
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
TOLERANCIA = 1e-6

# (nombre, módulo, patrones de resultados relativos a resultados/, lenta)
FASES = [
    ("fase6", "src.portfolio.fase6", ["fase6_*.csv"], False),
    ("fase7", "src.econometrics.fase7", ["fase7_*.csv"], False),
    ("fase8", "src.machine_learning.fase8", ["fase8_*.csv"], False),
    ("fase9", "src.neural_networks.fase9", ["fase9_*.csv"], True),
    ("fase10", "src.comparacion.fase10", ["fase10_*.csv"], False),
    ("fase11", "src.riesgo.fase11", ["fase11_*.csv"], False),
    ("semanal", "src.volatilidad_semanal.ejecutar", ["semanal_*.csv"], False),
    ("fase12", "src.optimizacion.fase12", ["fase12_*.csv"], False),
    ("fase14", "src.backtesting.fase14", ["fase14_*.csv"], False),
    ("fase16", "src.robustez.fase16", ["fase16/*.csv"], True),
    ("fase17", "src.interpretacion.fase17", ["fase17/*.csv"], False),
    ("fase21", "src.extensiones.fase21", ["fase21/validacion/*.csv", "fase21/exploratorio_prueba/*.csv"], True),
]


def _git(*args):
    return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout


def comparar(nuevo, publicado):
    """(reproduce, diferencia numérica máxima, motivo)."""
    if nuevo.shape != publicado.shape or list(nuevo.columns) != list(publicado.columns):
        return False, np.nan, f"forma {publicado.shape} -> {nuevo.shape}"
    num = [c for c in nuevo.columns if pd.api.types.is_numeric_dtype(nuevo[c])
           and pd.api.types.is_numeric_dtype(publicado[c])]
    otras = [c for c in nuevo.columns if c not in num]
    for c in otras:
        # fillna: con pandas 3, astype(str) conserva NaN y NaN != NaN.
        a = nuevo[c].fillna("").astype(str).to_numpy()
        b = publicado[c].fillna("").astype(str).to_numpy()
        if not np.array_equal(a, b):
            return False, np.nan, f"columna {c!r} distinta"
    if not num:
        return True, 0.0, ""
    a, b = nuevo[num].to_numpy(float), publicado[num].to_numpy(float)
    if not np.array_equal(np.isnan(a), np.isnan(b)):
        return False, np.nan, "faltantes en posiciones distintas"
    dif = float(np.nanmax(np.abs(a - b))) if np.isfinite(a).any() else 0.0
    return dif <= TOLERANCIA, dif, "" if dif <= TOLERANCIA else f"diferencia {dif:.2e}"


def ejecutar(rapido=False):
    resultados = RAIZ / "resultados"
    if _git("status", "--porcelain", "--", "resultados").strip():
        raise RuntimeError("Hay cambios sin commitear en resultados/: no se reejecuta para no "
                           "sobrescribir trabajo del equipo.")
    filas = []
    try:
        for nombre, modulo, patrones, lenta in FASES:
            if rapido and lenta:
                continue
            inicio = time.time()
            proc = subprocess.run([sys.executable, "-m", modulo], cwd=RAIZ, capture_output=True,
                                  text=True, encoding="utf-8", errors="replace")
            segundos = round(time.time() - inicio, 1)
            if proc.returncode != 0:
                filas.append({"fase": nombre, "archivo": "-", "reproduce": False, "max_dif": np.nan,
                              "motivo": f"falló (código {proc.returncode}): {proc.stderr[-300:]}",
                              "segundos": segundos})
                continue
            archivos = sorted(p for pat in patrones for p in resultados.glob(pat))
            for p in archivos:
                rel = str(p.relative_to(RAIZ)).replace("\\", "/")
                try:
                    publicado = pd.read_csv(io.StringIO(_git("show", f"HEAD:{rel}")))
                except subprocess.CalledProcessError:
                    filas.append({"fase": nombre, "archivo": rel, "reproduce": False, "max_dif": np.nan,
                                  "motivo": "archivo nuevo (no publicado)", "segundos": segundos})
                    continue
                ok, dif, motivo = comparar(pd.read_csv(p), publicado)
                filas.append({"fase": nombre, "archivo": rel, "reproduce": ok, "max_dif": dif,
                              "motivo": motivo, "segundos": segundos})
            print(f"{nombre}: {segundos} s", flush=True)
    finally:
        # Restaura todo lo publicado (tablas y gráficos) y borra lo que no lo estaba.
        _git("checkout", "--", "resultados")
        _git("clean", "-fdq", "--", "resultados")
    return pd.DataFrame(filas)


if __name__ == "__main__":
    sys.path.insert(0, str(RAIZ))
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Reejecuta las fases y compara con lo publicado.")
    p.add_argument("--rapido", action="store_true", help="Omite las fases lentas (9, 16 y 21).")
    a = p.parse_args()
    informe = ejecutar(a.rapido)
    pd.set_option("display.width", 200)
    print(informe.to_string(index=False))
    n_ok = int(informe["reproduce"].sum())
    print(f"\n{n_ok} de {len(informe)} tablas reproducen (tolerancia {TOLERANCIA:g}).")
    sys.exit(0 if n_ok == len(informe) else 1)
