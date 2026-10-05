"""
fase15_graficos.py — Gráficos de la evaluación final (solo lectura)
====================================================================

Lee los resultados ya congelados de ``resultados/fase15/final`` y genera
figuras para el informe. No reestima nada ni abre particiones.

Ejecutar:  python -m src.informe.fase15_graficos
"""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from config.environment import RUTA_GRAFICOS, RUTA_RESULTADOS  # noqa: E402

ESTILOS = {"igual": ("black", "-"), "min_var_muestral": ("tab:blue", "-"),
           "min_var_lw": ("tab:cyan", "--"), "min_cvar": ("tab:red", "-"),
           "paridad_riesgo": ("tab:green", "-.")}


def riqueza_prueba(variante="con_regla"):
    ruta = RUTA_RESULTADOS / "fase15" / "final" / variante / "portafolios_riqueza.csv"
    riq = pd.read_csv(ruta, parse_dates=["Date"]).set_index("Date")
    fig, ejes = plt.subplots(1, 2, figsize=(15, 5), sharey=True)
    for eje, u in zip(ejes, ("9_empresas", "liquidas")):
        for e, (c, ls) in ESTILOS.items():
            eje.plot(riq.index, riq[f"{u}|{e}"], color=c, ls=ls, lw=1.2, label=e)
        eje.plot(riq.index, riq["ibr"], color="gray", ls=":", lw=1, label="IBR")
        eje.set_title(f"Universo {u}", fontsize=9)
        eje.set_ylabel("Valor de 1 peso invertido")
        eje.legend(fontsize=7)
    fig.suptitle("Fase 15 — bloque de prueba (ene 2025 – sep 2026): rebalanceo mensual, "
                 "20 pb, ventana móvil de 252 días", fontsize=10)
    fig.tight_layout()
    RUTA_GRAFICOS.mkdir(parents=True, exist_ok=True)
    fig.savefig(RUTA_GRAFICOS / "fase15_riqueza_prueba.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    riqueza_prueba()
