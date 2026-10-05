# Portafolio Colombiano — Proyecto de Econometría

> **Estado del proyecto:** En desarrollo — Fases 0 a 19 completadas; pendiente: Fase 20 (Informe final)
> **Última actualización:** Octubre 2026

---

## Problema

Construir y evaluar un portafolio de acciones colombianas que cotizan en la Bolsa de Valores de Colombia (BVC), utilizando una combinación de métodos estadísticos, modelos econométricos, machine learning y redes neuronales, con el objetivo de lograr una buena relación entre rentabilidad y riesgo.

## Objetivo general

Estudiar si la integración de técnicas de distintas disciplinas —estadística, econometría, inteligencia artificial— puede mejorar la construcción de un portafolio diversificado y robusto frente a la incertidumbre del mercado.

## Metodología general

Datos → Estadística → Econometría → IA → Riesgo → Optimización → Backtesting → Agente IA → Informe

El proyecto se desarrolla en las siguientes fases (numeración usada en el
código y en `informes/diario_decisiones.md`):

0. **Definición del problema** — Pregunta de investigación: ¿mejoran los modelos econométricos y las redes neuronales la relación rentabilidad-riesgo frente a métodos tradicionales?
1. **Selección de empresas** — 6 a 10 empresas de distintos sectores, verificando cotización en la BVC, observaciones, confiabilidad y liquidez.
2. **Construcción de la base de datos** — Precios, rendimientos logarítmicos y variables externas (índice de mercado, TRM, tasa de interés, inflación, petróleo); regla de sincronización de fechas.
3. **Limpieza de datos** — Faltantes, duplicados, precios anormales y extremos, documentando todo cambio (sin eliminar extremos automáticamente).
4. **Análisis exploratorio** — Tendencia, rendimiento, volatilidad, distribución y correlación.
5. **Separación entrenamiento / validación / prueba** — Cronológica, sin data leakage; la prueba queda intocable hasta la evaluación final.
6. **Modelo de referencia** — Markowitz tradicional como benchmark.
7. **Econometría** — ARIMA y GARCH, con diagnósticos (estacionariedad, autocorrelación, heterocedasticidad, residuos, calidad de pronóstico).
8. **Machine Learning** — Random Forest / XGBoost.
9. **Red neuronal** — MLP y, si los datos lo permiten, LSTM.
10. **Comparación de modelos** — MAE, RMSE y otras métricas; predicción ≠ inversión.
11. **Estimación del riesgo** — Volatilidad, VaR y CVaR.
12. **Optimización del portafolio** — Mínimo riesgo, máximo Sharpe y máxima rentabilidad con restricciones de riesgo.
13. **Restricciones realistas** — Suma 1, sin cortos, peso máximo por activo y límites sectoriales.
14. **Backtesting** — Walk-forward con rebalanceo periódico.
15. **Comparación final** — Portafolio tradicional vs. econométrico vs. ML vs. LSTM (rentabilidad, volatilidad, Sharpe, drawdown, VaR, CVaR).
16. **Análisis de robustez** — Cambios de período, número de empresas, restricciones, rebalanceo y ventana de entrenamiento.
17. **Interpretación económica** — Por qué los modelos asignan los pesos que asignan, en el contexto colombiano.
18. **Agente de IA** — Coordina y supervisa el pipeline; no modifica datos ni metodología sin registro y revisión humana.
19. **Evaluación del agente** — Elección de modelos, detección de errores, respeto del orden temporal, documentación y reproducibilidad.
20. **Informe final**.

## Tecnologías

| Categoría | Herramientas probables |
|---|---|
| Lenguaje | Python 3.10+ |
| Datos | pandas, numpy, yfinance |
| Estadística | scipy, statsmodels |
| Visualización | matplotlib, seaborn |
| Econometría | statsmodels, arch 8.0.0 |
| Machine Learning | scikit-learn 1.9.1 |
| Redes neuronales | PyTorch 2.14.1 (CPU) |
| Control de versiones | Git |
| Notebooks | Jupyter |

## Estructura del proyecto

```
├── datos/
│   ├── crudos/        # Datos originales de Yahoo Finance (sin modificar); externos/ = TRM y Brent
│   ├── procesados/    # Precios y rendimientos (simple y logarítmico)
│   ├── particiones/   # Entrenamiento / validación / prueba congelados + huellas SHA-256
│   └── metadata/      # Metadatos de la descarga (JSON)
├── notebooks/         # Notebooks Jupyter por fase
├── src/
│   ├── data/          # Descarga, validación, gestión de datos, metadatos
│   ├── preprocessing/ # Rendimientos, imputación Kalman, partición temporal
│   ├── exploratory_analysis/  # Estadística descriptiva, correlaciones, gráficos, outliers
│   ├── portfolio/     # Markowitz y métricas de portafolio (Fase 6)
│   ├── econometrics/  # ARIMA, GARCH y métricas de pronóstico (Fase 7)
│   ├── machine_learning/  # Variables, Random Forest y Gradient Boosting (Fase 8)
│   ├── neural_networks/   # MLP y LSTM en PyTorch (Fase 9)
│   ├── comparacion/       # MCS, Holm, R² fuera de muestra, Pesaran-Timmermann (Fase 10)
│   ├── riesgo/            # VaR, Expected Shortfall y backtesting (Fase 11)
│   ├── volatilidad_semanal/  # Volatilidad y rendimiento semanales (DEC-029/030)
│   ├── optimizacion/      # Optimización con restricciones y sectores (Fases 12–13)
│   ├── backtesting/       # Simulación walk-forward con costos (Fase 14)
│   ├── informe/           # Gráficos de resultados ya congelados
│   ├── robustez/          # Análisis de robustez exploratorio (Fase 16)
│   ├── interpretacion/    # Interpretación económica (Fase 17)
│   ├── agente/            # Agente de IA y su evaluación (Fases 18–19)
│   └── evaluacion_final.py  # Fase 15: único módulo que abre el bloque de prueba
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

Fases implementadas (las decisiones marcadas como pendientes requieren aprobación del equipo):

1. **Fases 0 y 1 — Problema y selección de empresas:** estructura del proyecto, documentación inicial y universo de 9 empresas (DEC-006), con tickers auditados (DEC-010).
2. **Fase 2 — Base de datos:** descarga desde Yahoo Finance, datos crudos inmutables, metadatos y reporte de calidad. La muestra está fija: del 2020-01-01 al 2026-09-14 (DEC-021). Variables externas: TRM y petróleo Brent (DEC-024) e IBR overnight del Banco de la República como tasa libre de riesgo (DEC-031). **Pendiente:** índice de mercado (COLCAP, no disponible en Yahoo), tasa de interés e inflación.
3. **Fase 3 — Limpieza:** auditoría de calidad y liquidez, **imputación del único valor faltante con Filtro de Kalman** (con bandera y validación MAE/RMSE) y precio inválido de la fuente del 2024-05-03 marcado con bandera, sin imputar (DEC-022).
4. **Fase 4 — Análisis exploratorio:** rendimientos, estadística descriptiva, volatilidad, correlaciones, outliers, auditoría de iliquidez, saltos reversibles y pruebas formales (Jarque-Bera, ADF/KPSS, Ljung-Box, ARCH-LM) sobre entrenamiento. El hallazgo DEC-018 se resolvió en DEC-022: el precio de Yahoo del 2024-05-03 es un error de la fuente en las 9 empresas (contrastado con el ADR de Ecopetrol) y queda marcado como inválido en la capa procesada.
5. **Fase 5 — Entrenamiento / validación / prueba:** partición cronológica en `datos/particiones/` (entrenamiento hasta 2023, validación 2024, prueba desde 2025), verificación anti-leakage, huellas SHA-256 y acceso controlado a la prueba (DEC-017, DEC-019, pendientes de aprobación).
6. **Fase 6 — Modelo de referencia, Markowitz:** benchmark con portafolios de igual ponderación (1/N), mínima varianza y máximo Sharpe, estimados solo con entrenamiento y evaluados en entrenamiento y validación, con restricciones de suma 1, sin posiciones cortas y peso máximo de 30 % por activo (DEC-020). Código en `src/portfolio/`; se ejecuta con `python -m src.portfolio.fase6`. No se usó el bloque de prueba. Pendiente: definir cuál portafolio es el benchmark oficial y la tasa libre de riesgo (hoy 0, provisional).
7. **Fase 7 — Econometría:** ARIMA(p,0,q) elegido por BIC y GARCH(1,1) con errores t, estimados solo con entrenamiento y evaluados con pronósticos a un paso en validación frente a referencias simples (media, cero, varianza constante y EWMA), con pruebas de Diebold-Mariano (DEC-023). Código en `src/econometrics/`; se ejecuta con `python -m src.econometrics.fase7`. Hallazgos: ningún ARIMA supera a la media de entrenamiento; GARCH supera a la varianza constante en Banco de Bogotá y Ecopetrol, pero no a EWMA en ninguna acción líquida; en acciones ilíquidas (ETB sobre todo) el GARCH no es fiable.
8. **Fase 8 — Machine Learning:** Random Forest y Gradient Boosting (scikit-learn) agrupados para las 9 empresas, que predicen el rendimiento del día siguiente con rezagos, volatilidad, volumen, mercado, TRM y Brent. Los hiperparámetros se eligen con validación cruzada temporal dentro de entrenamiento y los modelos se comparan en validación contra la media, el cero y ARIMA (DEC-025). Código en `src/machine_learning/`; se ejecuta con `python -m src.machine_learning.fase8`. Hallazgo: la mejora frente a la media (≈ 0,3 % del RMSE) no es significativa.
9. **Fase 9 — Redes neuronales:** MLP y LSTM (PyTorch; la LSTM usa los últimos 30 días) para el rendimiento del día siguiente, con hiperparámetros y parada temprana elegidos con el final de entrenamiento y un conjunto de 5 semillas (DEC-026). Código en `src/neural_networks/`; se ejecuta con `python -m src.neural_networks.fase9` (unos 5 minutos en CPU). Hallazgo: ninguna red supera a la media de entrenamiento en validación, igual que ARIMA, Random Forest y Gradient Boosting.
10. **Fase 10 — Comparación de modelos:** consolida los pronósticos de validación de las Fases 7 a 9 con Model Confidence Set, R² fuera de muestra con intervalos bootstrap, Diebold-Mariano, Pesaran-Timmermann y corrección de Holm por comparaciones múltiples (DEC-027). Código en `src/comparacion/`; se ejecuta con `python -m src.comparacion.fase10` (requiere las Fases 7 a 9). Hallazgos: para el rendimiento diario ningún modelo se distingue de la media (los 7 quedan en el MCS); para la volatilidad, EWMA es el único en el MCS.
11. **Fase 11 — Estimación del riesgo:** VaR y Expected Shortfall a un día (95 % y 99 %) de las 4 acciones líquidas y los 6 portafolios de la Fase 6 por simulación histórica, normal con EWMA, GARCH-t y simulación histórica filtrada, validados con Kupiec, Christoffersen, semáforo de Basilea, prueba de ES y MCS (DEC-028). Código en `src/riesgo/`; se ejecuta con `python -m src.riesgo.fase11`. Hallazgos: ningún método se rechaza tras Holm; el VaR normal subestima la cola al 99 %, GARCH-t la sobreestima y la simulación histórica filtrada es la mejor calibrada.
12. **Extensión — volatilidad semanal (plan registrado antes de ejecutar, DEC-029/DEC-030):** varianza realizada de la semana siguiente de las 4 acciones líquidas con EWMA, GARCH, HAR, Random Forest, Gradient Boosting y MLP. Código en `src/volatilidad_semanal/`; se ejecuta con `python -m src.volatilidad_semanal.ejecutar`. Hallazgos: los modelos de ML quedan numéricamente por delante de HAR pero sin significancia (Holm p = 0,40; los 6 en el MCS); el rendimiento semanal tampoco es predecible.
13. **Fases 12–13 — Optimización con restricciones:** 1/N, mínima varianza (muestral y Ledoit-Wolf), mínimo CVaR 95 %, paridad de riesgo, máximo Sharpe y máximo retorno con volatilidad acotada, con máximo 30 % por acción y 40 % por sector, y el IBR como tasa libre de riesgo (DEC-031). Código en `src/optimizacion/`; se ejecuta con `python -m src.optimizacion.fase12`. Hallazgos: con 9 empresas los portafolios basados en riesgo superan al 1/N y el máximo Sharpe es el peor en validación; con las 4 líquidas ningún portafolio supera al IBR en 2024.
14. **Fase 14 — Backtesting walk-forward (plan registrado, DEC-032/DEC-033):** enero 2021–diciembre 2024, rebalanceo mensual con ventana móvil de 252 días y costos de 20 pb (sensibilidad 0 y 50 pb; robustez trimestral). Código en `src/backtesting/`; se ejecuta con `python -m src.backtesting.fase14`. Hallazgos: ninguna estrategia supera al IBR; el 1/N tiene el mejor Sharpe en ambos universos y ninguna estrategia de riesgo lo supera (diferencias negativas, no significativas tras Holm); los costos no explican el resultado.
15. **Fase 15 — Evaluación final en el bloque de prueba (plan aprobado DEC-034; resultados DEC-036):** ejecutada una sola vez sobre enero 2025–septiembre 2026, tras un ensayo que reprodujo las Fases 7–14. Código en `src/evaluacion_final.py`. Se confirman fuera de muestra: el rendimiento diario no es predecible mejor que la media; EWMA es una referencia difícil de superar en volatilidad; el VaR normal subestima la cola; ninguna estrategia de riesgo supera al 1/N (aunque en 2025–2026 la renta variable superó al IBR). RF y GB superan a HAR en volatilidad semanal en el análisis principal, pero no en la sensibilidad sin tratamiento de fechas sospechosas.
16. **Fase 16 — Robustez (exploratoria; plan DEC-037, resultados DEC-038):** 24 configuraciones de portafolio (ventana × peso máximo × universo), volatilidad y VaR año por año y rendimiento año por año, 2021–2026. Código en `src/robustez/fase16.py`; se ejecuta con `python -m src.robustez.fase16`. Las cuatro conclusiones centrales son robustas: ninguna estrategia supera al 1/N en ninguna configuración; EWMA está en el MCS todos los años; el VaR normal subestima la cola todos los años; el rendimiento no es predecible en ningún año.
17. **Fase 17 — Interpretación económica (DEC-039/DEC-040):** qué explica los pesos (sobre todo la volatilidad), beta simple frente a Dimson, riesgo prometido frente a realizado, reversión diaria por microestructura, Ecopetrol y el petróleo, y el ciclo de tasas. Texto en `docs/interpretacion_economica.md`; código en `src/interpretacion/fase17.py`.
18. **Fase 18 — Agente de IA (DEC-041):** agente de línea de comandos con la API de Claude (`claude-opus-5-5`) y 9 herramientas: consulta el diario y los resultados, ejecuta pruebas sobre entrenamiento o validación, verifica la reproducibilidad de las fases y **solo propone** cambios, que requieren revisión humana. No tiene acceso al bloque de prueba ni puede modificar datos. Cada sesión queda en `informes/bitacora_agente/`. Código en `src/agente/`. La evaluación (Fase 19, plan DEC-042) está en `src/agente/evaluacion.py`.
19. **Fases 18–19 sobre Claude Code (DEC-043/DEC-044):** el agente funciona dentro de Claude Code con la skill `/investigador`, las mismas herramientas (`python -m src.agente.cli`) y un hook que bloquea el acceso a la prueba, las descargas y la escritura en `datos/` (`.claude/settings.json`). Evaluado con 7 escenarios y agentes nuevos: 38 de 39 criterios (97 %) e integridad del 100 %.

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

# 2. Reprocesar desde los datos crudos guardados (no descarga; DEC-021)
python -m src.pipeline
#    Descarga nueva: solo con datos/crudos/ vacío y registrando la decisión
#    python -m src.pipeline --descargar

# 3. Ejecutar las pruebas
python -m pytest tests -v

# 4. Agente de IA (requiere credenciales de Anthropic en el entorno; nunca en el código)
#    set ANTHROPIC_API_KEY=...            (Windows)   |   export ANTHROPIC_API_KEY=...   (Linux/macOS)
python -m src.agente "¿Qué modelo de volatilidad recomiendan los resultados?"

# 5. Abrir el notebook de exploración
jupyter notebook notebooks/01_exploracion.ipynb
```

## Nota importante

Este proyecto está en fase de desarrollo. Los resultados, conclusiones y métodos aquí documentados son preliminares y están sujetos a revisión.

---

*Proyecto académico — Econometría y Construcción de Portafolios*
