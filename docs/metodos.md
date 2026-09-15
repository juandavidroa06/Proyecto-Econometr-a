# Metodología del Proyecto

> **Estado:** En progreso — Las etapas 1 a 5 (adquisición, validación, limpieza,
> exploración y estadística descriptiva) y la **Fase 3.5** (auditoría, buenas
> prácticas e imputación con Filtro de Kalman) ya han sido ejecutadas. Las etapas
> 6 en adelante (econometría, ML, redes, riesgo, optimización, backtesting,
> robustez y agente) están planificadas pero aún no se han ejecutado.
> **Última actualización:** Septiembre 2026

Este documento describe la metodología que seguiremos para construir y evaluar un portafolio de acciones colombianas. Cada sección representa una fase del proyecto que se implementará de manera progresiva.

---

## 1. Selección de activos

**Objetivo:** Definir qué empresas de la BVC incluiremos en el análisis.

**Criterios de selección (propuestos):**
- Empresas que cotizan de manera continua en la BVC.
- Liquidez mínima (volumen de negociación suficiente).
- Horizonte de datos suficiente para el análisis.
- Diversificación por sectores (si es posible).

**Pendiente por definir:**
- Número mínimo de empresas.
- Sectores a incluir.
- Criterios formales de filtrado.

---

## 2. Obtención de datos

**Objetivo:** Descargar series de precios históricos de las empresas seleccionadas.

**Fuentes consideradas:**
- Yahoo Finance (vía `yfinance`)
- Datos descargados manualmente de la BVC
- Otras APIs financieras

**Variables a obtener:**
- Precio de apertura, cierre, máximo, mínimo.
- Volumen negociado.
- Fechas de negociación.

**Consideraciones:**
- Verificar que los datos descargados sean consistentes.
- Registrar la fuente y fecha de descarga para reproducibilidad.

---

## 3. Limpieza y calidad de datos

**Objetivo:** Asegurar que los datos sean confiables para el análisis.

**Tareas:**
- Identificar y tratar datos faltantes.
- Detectar y justificar el manejo de outliers.
- Verificar la consistencia temporal (días sin negociación).
- Eliminar duplicados.
- Registrar cada transformación aplicada.

**Principios:**
- No eliminar datos sin justificación documentada.
- Mantener una copia de los datos crudos intacta.

---

## 3.5 Imputación de valores faltantes (Filtro de Kalman)

**Objetivo:** Tratar el único valor faltante de precios detectado (Grupo Bolívar,
`Adj Close` en `2026-03-10`) sin modificar los datos crudos.

### ¿Qué es la imputación?

La imputación es el proceso de estimar un valor que falta en una serie usando un
modelo estadístico. En este proyecto **solo** se imputa el valor faltante, y
siempre **quedando marcado** con una bandera para distinguirlo de un valor
realmente observado.

### ¿Por qué calman?

El **Filtro de Kalman** es un método estándar para series de tiempo que estima el
estado no observado de un proceso y permite **interpolar** valores faltantes de
manera estadísticamente fundamentada. Se usa un modelo de **nivel local**:

```
y_t   = mu_t + eps_t        (ecuación de observación)
mu_t  = mu_{t-1} + eta_t    (ecuación de transición: camino aleatorio)
```

Se implementa con `statsmodels` (ya en el proyecto, sin librerías nuevas).

### ¿Qué variable se imputa?

Únicamente **`Adj Close`** (precio ajustado), que es la variable usada para
calcular rendimientos. El resto de columnas OHLCV se conservan intactas.

### ¿Qué significa "smoothing"?

Al usar **suavizado** (smoothing), se emplea información **anterior y posterior**
al valor faltante para estimarlo. Esto produce una mejor reconstrucción histórica,
pero implica que el valor imputado no podría conocerse "en el momento" si solo
tuviéramos información pasada.

### ¿Por qué no se modifica el dato crudo?

El archivo `datos/crudos/` es inmutable. La imputación es una transformación que
se guarda en `datos/procesados/` con columnas/archivos nuevos:

- `es_imputado_kalman`: marca si el precio fue imputado.
- `retorno_depende_imputacion`: marca si un rendimiento usa un precio imputado.

### ¿Cómo se valida?

Se hace una **prueba artificial**: se ocultan observaciones que sí existen, se
reconstruyen con el filtro y se comparan con el valor real, calculando **MAE** y
**RMSE**. En nuestras series el error relativo (MAE) fue de aproximadamente
0.8%–1.5%, lo que sugiere que el filtro reconstruye bien bajo el modelo asumido.

### Limitaciones

- El filtro da una **estimación estadística** bajo el modelo de nivel local; no
  "demuestra" cuál era el valor real.
- Requiere una serie con suficientes observaciones para estimar el modelo.
- El suavizado asume que el nivel evoluciona como un camino aleatorio; si el
  precio tuviera saltos estructurales no capturados, la estimación podría
  alejarse del valor real.

### Reconstrucción histórica vs. predicción en tiempo real

- **Reconstrucción histórica** (lo que hacemos): se puede usar información
  posterior. Es válido para completar la serie antes de analizar.
- **Predicción en tiempo real**: solo se puede usar información disponible en ese
  momento. La imputación con suavizado **no** debe usarse directamente en
  backtesting o predicción sin adaptar el procedimiento (sería data leakage).

---

## 4. Análisis exploratorio

**Objetivo:** Comprender las características principales de los datos antes del modelamiento.

**Tareas:**
- Estadísticas descriptivas (media, varianza, skewness, curtosis).
- Distribuciones de rendimientos.
- Gráficos de series temporales.
- Análisis de tendencias y estacionalidad.
- Identificación deperiodos relevantes (crisis, recuperaciones).

---

## 5. Análisis estadístico

**Objetivo:** Realizar pruebas formales que sustenten las decisiones metodológicas.

**Pruebas:**
- Pruebas de normalidad (Shapiro-Wilk, Jarque-Bera).
- Pruebas de estacionariedad (ADF, KPSS).
- Análisis de correlaciones y correlaciones parciales.
- Pruebas de cointegración (si aplica).
- Análisis de heterocedasticidad.

---

## 6. Econometría

**Objetivo:** Construir modelos econométricos para modelar y predecir rendimientos.

**Modelos a considerar:**
- ARIMA / SARIMA para series individuales.
- GARCH y variantes para modelar volatilidad.
- VAR para relaciones multivariadas.
- Modelos de regresión con variables explicativas macroeconómicas.

**Evaluación:**
- Diagnósticos de residuos.
- Pruebas de bondad de ajuste.
- Comparación con modelos de referencia (naïve, random walk).

---

## 7. Machine Learning

**Objetivo:** Aplicar modelos de aprendizaje automático para predicción y clasificación.

**Modelos a considerar:**
- Random Forest para selección de variables.
- Gradient Boosting (XGBoost, LightGBM) para predicción.
- SVM para clasificación de señales.
- PCA para reducción de dimensionalidad.

**Consideraciones:**
- Respetar el orden temporal en la validación.
- Evitar data leakage.
- Usar validación cruzada temporal (TimeSeriesSplit).

---

## 8. Redes neuronales

**Objetivo:** Explorar arquitecturas de deep learning para pronóstico de rendimientos.

**Modelos a considerar:**
- MLP (Multi-Layer Perceptron) como modelo base simple.
- LSTM (Long Short-Term Memory) para dependencias temporales.
- Comparar contra modelos econométricos y de ML.

**Consideraciones:**
- No asumir que una red neuronal es superior.
- Documentar la arquitectura, hiperparámetros y proceso de entrenamiento.
- Validar con datos fuera de muestra.

---

## 9. Estimación del riesgo

**Objetivo:** Cuantificar el riesgo del portafolio y de los activos individuales.

**Métricas:**
- Volatilidad histórica y móvil.
- Value at Risk (VaR) — métodos paramétrico, histórico y de Monte Carlo.
- Conditional Value at Risk (CVaR).
- Drawdown máximo.
- Beta del portafolio.

**Modelos:**
- GARCH para volatilidad condicional.
- Simulación de Monte Carlo para distribuciones de rendimiento.

---

## 10. Optimización del portafolio

**Objetivo:** Encontrar la composición óptima del portafolio según diferentes criterios.

**Métodos a considerar:**
- Markowitz (media-varianza).
- Mínima varianza.
- Máximo Sharpe Ratio.
- Risk Parity.
- Black-Litterman (si se incorporan opiniones de mercado).

**Restricciones:**
- Peso mínimo y máximo por activo.
- Posición libre de corto plazo.
- Restricciones sectoriales (si aplica).

---

## 11. Backtesting

**Objetivo:** Evaluar el desempeño del portafolio fuera de muestra.

**Enfoque:**
- Simulación historica con ventana rolling.
- Separación estricta train/validation/test.
- Métricas de performance: Sharpe, Sortino, Calmar, drawdown.
- Comparación contra benchmarks (COLCAP, buy-and-hold).

**Consideraciones:**
- Respetar el orden temporal.
- No utilizar información futura.
- Documentar costos de transacción (si aplica).

---

## 12. Análisis de robustez

**Objetivo:** Verificar que los resultados no dependan de supuestos específicos.

**Pruebas:**
- Cambio en el periodo de análisis.
- Cambio en la selección de activos.
- Sensibilidad a parámetros de optimización.
- Validación cruzada temporal.
- Análisis de diferentes métricas de riesgo.

---

## 13. Agente de IA

**Objetivo:** Desarrollar un asistente de IA que ayude a coordinar y automatizar partes del proceso de investigación.

**Funcionalidades conceptuales:**
- Registrar decisiones metodológicas.
- Sugerir siguiente paso basado en el estado del proyecto.
- Ejecutar tareas repetitivas (carga de datos, generación de gráficos).
- Mantener un historial de experimentos.

**Nota:** Esta etapa se implementará progresivamente a medida que avance el proyecto.

---

## Nota final

> Las etapas 1 a 5 ya fueron ejecutadas (Fases 2 y 3) y sus resultados se
> encuentran en `resultados/`. Las etapas restantes siguen siendo un plan.
> Las decisiones específicas se registran en el `diario_decisiones.md`
> conforme avance el proyecto.
