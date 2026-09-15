# Portafolio Colombiano — Proyecto de Econometría

> **Estado del proyecto:** En desarrollo — Fases 1, 2, 3 y 3.5 completadas
> **Última actualización:** Septiembre 2026

---

## Problema

Construir y evaluar un portafolio de acciones colombianas que cotizan en la Bolsa de Valores de Colombia (BVC), utilizando una combinación de métodos estadísticos, modelos econométricos, machine learning y redes neuronales, con el objetivo de lograr una buena relación entre rentabilidad y riesgo.

## Objetivo general

Estudiar si la integración de técnicas de distintas disciplinas —estadística, econometría, inteligencia artificial— puede mejorar la construcción de un portafolio diversificado y robusto frente a la incertidumbre del mercado.

## Metodología general

El proyecto se desarrolla en las siguientes fases:

1. **Selección de activos** — Definición de empresas y criterios de inclusión.
2. **Obtención de datos** — Descarga y validación de series de precios.
3. **Limpieza y calidad** — Manejo de datos faltantes, duplicados y outliers.
4. **Análisis exploratorio** — Estadísticas descriptivas y visualización.
5. **Análisis estadístico** — Distribuciones, correlaciones y pruebas formales.
6. **Econometría** — Modelos de series de tiempo (ARIMA, GARCH, VAR, cointegración).
7. **Machine Learning** — Modelos supervisados y no supervisados para predicción y clasificación.
8. **Redes neuronales** — Arquitecturas LSTM y MLP para pronóstico de rendimientos.
9. **Estimación del riesgo** — VaR, CVaR, volatilidad y métricas de riesgo.
10. **Optimización del portafolio** — Markowitz, Black-Litterman y métodos alternativos.
11. **Backtesting** — Evaluación fuera de muestra con estrategias definidas.
12. **Análisis de robustez** — Pruebas de sensibilidad y validación cruzada temporal.
13. **Informe final** — Documentación completa de resultados y decisiones.

## Tecnologías

| Categoría | Herramientas probables |
|---|---|
| Lenguaje | Python 3.10+ |
| Datos | pandas, numpy, yfinance |
| Estadística | scipy, statsmodels |
| Visualización | matplotlib, seaborn |
| Econometría | statsmodels, arch |
| Machine Learning | scikit-learn (por definir) |
| Redes neuronales | TensorFlow / PyTorch (por definir) |
| Control de versiones | Git |
| Notebooks | Jupyter |

## Estructura del proyecto

```
├── datos/
│   ├── crudos/        # Datos originales de Yahoo Finance (sin modificar)
│   ├── procesados/    # Precios y rendimientos (simple y logarítmico)
│   └── metadata/      # Metadatos de la descarga (JSON)
├── notebooks/         # Notebooks Jupyter por fase
├── src/
│   ├── data/          # Descarga, validación, gestión de datos, metadatos
│   ├── preprocessing/ # Cálculo de rendimientos
│   └── exploratory_analysis/  # Estadística descriptiva, correlaciones, gráficos, outliers
├── modelos/           # Modelos entrenados (fases posteriores)
├── resultados/        # Métricas, reportes y gráficos
│   └── graficos/      # Gráficos del análisis exploratorio
├── informes/          # Diario de decisiones metodológicas
├── tests/             # Pruebas unitarias (pytest)
├── config/            # Configuración y parámetros
└── docs/              # Documentación académica
```

## Equipo

Estudiantes de Estadística — Semestre VIII.

## Avance actual

Fases completadas:

1. **Fase 1 — Cimientos:** estructura del proyecto y documentación inicial.
2. **Fase 2 — Adquisición y validación:** descarga de datos desde Yahoo Finance, guardado de datos crudos, metadatos y reporte de calidad.
3. **Fase 3 — Preparación y análisis exploratorio:** cálculo de rendimientos (simple y logarítmico), estadística descriptiva, volatilidad, correlaciones, gráficos y detección de outliers.
4. **Fase 3.5 — Auditoría e imputación:** auditoría de tickers y de calidad, formalización de buenas prácticas (`AGENTS.md`), e **imputación del valor faltante con Filtro de Kalman** (con bandera de imputación y validación MAE/RMSE).

Empresas incluidas (tickers de Yahoo Finance):

| Empresa | Ticker |
|---|---|
| Celsia | `CELSIA.CL` |
| Banco de Bogotá | `BOGOTA.CL` |
| Ecopetrol | `ECOPETROL.CL` |
| ETB | `ETB.CL` |
| Nutresa | `NUTRESA.CL` |
| Banco Davivienda PF | `PFDAVVNDA.CL` |
| Promigas | `PROMIGAS.CL` |
| Mineros SA | `MINEROS.CL` |
| Grupo Bolívar | `GRUBOLIVAR.CL` |

## Cómo ejecutar

```bash
# 1. Crear un entorno virtual e instalar dependencias
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 2. Ejecutar el pipeline completo (descarga, validación, procesamiento, EDA)
python -m src.pipeline

# 3. Ejecutar las pruebas
python -m pytest tests -v

# 4. Abrir el notebook de exploración
jupyter notebook notebooks/01_exploracion.ipynb
```

## Nota importante

Este proyecto está en fase de desarrollo. Los resultados, conclusiones y métodos aquí documentados son preliminares y están sujetos a revisión.

---

*Proyecto académico — Econometría y Construcción de Portafolios*
