# Diario de Decisiones Metodológicas

> **Propósito:** Registrar cada decisión importante del proyecto, su justificación
> y las alternativas que se consideraron. Esto garantiza trazabilidad y permite
> revisar decisiones anteriores si es necesario.

---

## Cómo usar este diario

Cada decisión se registra con el siguiente formato:

```
### DEC-[Número]: [Título de la decisión]

- **Fecha:** YYYY-MM-DD
- **Fase:** [Fase del proyecto]
- **Decisión:** [Qué se decidió]
- **Motivo:** [Por qué se tomó esta decisión]
- **Alternativas consideradas:** [Qué otras opciones se evaluaron]
- **Evidencia utilizada:** [Qué información respaldó la decisión]
- **Impacto:** [Cómo afecta al proyecto]
- **Estado:** [Pendiente / Aprobada / Revisada]
```

---

## Registro de decisiones

### DEC-001: Definición de arquitectura del proyecto

- **Fecha:** 2026-08-19
- **Fase:** Fase 1 — Cimientos
- **Decisión:** Se adopta la estructura de carpetas propuesta (datos/, notebooks/, src/, modelos/, resultados/, informes/, tests/, config/, docs/). Los módulos internos de src/ se crearán incrementalmente.
- **Motivo:** Se busca un diseño modular, escalable y fácil de mantener. Crear toda la estructura de una vez generaría carpetas vacías y código innecesario.
- **Alternativas consideradas:**
  - Crear toda la estructura completa de una vez (rechazada: demasiado código sin uso aún).
  - Estructura plana sin subcarpetas (rechazada: falta de organización).
  - Solo notebooks/ y datos/ (rechazada: insuficiente para un proyecto serio).
- **Evidencia utilizada:** Buenas prácticas de proyectos de ciencia de datos y la necesidad de integrar múltiples disciplinas (estadística, econometría, ML, deep learning).
- **Impacto:** Establece la base sobre la que se construirá todo el proyecto. Facilita la incorporación progresiva de código.
- **Estado:** Aprobada

---

### DEC-002: Dependencias iniciales

- **Fecha:** 2026-08-19
- **Fase:** Fase 1 — Cimientos
- **Decisión:** Se definen únicamente dependencias para manejo de datos, estadística, visualización y econometría. Se excluyen librerías de ML, deep learning y agentes de IA.
- **Motivo:** Evitar instalar herramientas que todavía no se han definido. Mantener el entorno ligero y enfocado en las primeras fases.
- **Alternativas consideradas:**
  - Instalar todo el ecosistema completo (rechazado: innecesario y puede generar conflictos de versiones).
  - No definir requirements.txt todavía (rechazado: dificulta la reproducibilidad).
- **Evidencia utilizada:** Principio de reproducibilidad y desarrollo incremental del proyecto.
- **Impacto:** Permite trabajar en las primeras fases sin sobrecarga de dependencias. Las librerías de ML se agregarán cuando se defina exactamente cuáles se utilizarán.
- **Estado:** Aprobada

---

### DEC-003: Fuente principal de datos

- **Fecha:** 2026-08-19
- **Fase:** Fase 2 — Adquisición de datos
- **Decisión:** Se utiliza **Yahoo Finance** mediante la librería `yfinance` como fuente principal de descarga de datos.
- **Motivo:** Acceso programático, reproducible y gratuito a series históricas OHLCV. Investing.com NO se utiliza en esta fase (podrá documentarse después como fuente secundaria de contraste).
- **Alternativas consideradas:**
  - Descarga manual desde la BVC (rechazada: tediosa y poco reproducible).
  - Investing.com (rechazada por ahora: se pospone como posible contraste).
- **Evidencia utilizada:** Disponibilidad de datos para los 9 tickers verificada con una descarga de prueba.
- **Impacto:** Define el mecanismo de adquisición de todas las series del proyecto.
- **Estado:** Aprobada

---

### DEC-004: Frecuencia de los datos

- **Fecha:** 2026-08-19
- **Fase:** Fase 2 — Adquisición de datos
- **Decisión:** Se utilizan datos **diarios** (intervalo `1d` en Yahoo Finance).
- **Motivo:** La frecuencia diaria ofrece el mayor número de observaciones y es estándar para volatilidad, riesgo y optimización de portafolios.
- **Alternativas consideradas:** Semanal y mensual (rechazadas: menor número de observaciones).
- **Evidencia utilizada:** ~1 715 observaciones por activo con frecuencia diaria en el período elegido.
- **Impacto:** Determina la granularidad de todos los análisis posteriores.
- **Estado:** Aprobada

---

### DEC-005: Período de análisis

- **Fecha:** 2026-08-19
- **Fase:** Fase 2 — Adquisición de datos
- **Decisión:** Se analizan datos desde **2020-01-01** hasta la **fecha actual de ejecución** (no fija, configurable en `config/settings.py`).
- **Motivo:** El período incluye eventos de mercado relevantes (pandemia COVID-19 en 2020 y la recuperación posterior) y maximiza el número de observaciones. Usar "la fecha actual" evita codificar una fecha que quedaría obsoleta.
- **Alternativas consideradas:** Períodos más cortos (rechazados: menos evidencia); fecha final fija (rechazada: se vuelve obsoleta).
- **Evidencia utilizada:** Necesidad de reproducibilidad y relevancia temporal.
- **Impacto:** Define el horizonte de todos los análisis.
- **Estado:** Aprobada

---

### DEC-006: Selección de empresas

- **Fecha:** 2026-08-19
- **Fase:** Fase 2 — Adquisición de datos
- **Decisión:** Se analizan exactamente estas 9 empresas (tickers de Yahoo Finance indicados):
  - Celsia (`CELSIA.CL`), Banco de Bogotá (`BOGOTA.CL`), Ecopetrol (`ECOPETROL.CL`), ETB (`ETB.CL`), Nutresa (`NUTRESA.CL`), Banco Davivienda PF (`PFDAVVNDA.CL`), Promigas (`PROMIGAS.CL`), Mineros SA (`MINEROS.CL`), Grupo Bolívar (`GRUBOLIVAR.CL`).
- **Motivo:** Conjunto definido por el equipo; cubre distintos sectores (energía, financiero, telecomunicaciones, alimentos, servicios públicos, minería).
- **Alternativas consideradas:** Incluir más/otras empresas (rechazado por alcance de esta fase).
- **Evidencia utilizada:** Los 9 tickers devolvieron datos correctamente.
- **Impacto:** Define el universo de activos del portafolio.
- **Nota:** Los tickers usan el sufijo `.CL`. Se confirma que Yahoo Finance devuelve datos para estos símbolos; se recomienda verificar en fases posteriores que corresponden al activo esperado (ver advertencias en el resumen).
- **Estado:** Aprobada

---

### DEC-007: Conservación de datos crudos

- **Fecha:** 2026-08-19
- **Fase:** Fase 2 — Adquisición de datos
- **Decisión:** Los datos descargados de Yahoo Finance se conservan **sin modificar** en `datos/crudos/` (un CSV por empresa). Toda transformación se guarda aparte en `datos/procesados/`.
- **Motivo:** Garantizar trazabilidad y reproducibilidad: siempre se puede volver a la fuente original.
- **Alternativas consideradas:** Almacenar solo datos procesados (rechazado: se pierde trazabilidad).
- **Evidencia utilizada:** Principio de reproducibilidad (principio metodológico #8).
- **Impacto:** Permite auditar cualquier transformación posterior.
- **Estado:** Aprobada

---

### DEC-008: Cálculo de rendimientos

- **Fecha:** 2026-08-19
- **Fase:** Fase 3 — Preparación de datos
- **Decisión:** Se calculan **rendimientos simples** y **logarítmicos** sobre el **precio ajustado (`Adj Close`)**, que corrige dividendos y splits.
- **Motivo:** El precio ajustado es metodológicamente el más adecuado para calcular rendimientos de un activo. Se mantienen ambos tipos de rendimiento porque se usan en contextos distintos (el logarítmico es conveniente por su aditividad temporal).
- **Alternativas consideradas:** Usar precio de cierre (`Close`) sin ajustar (rechazado: ignora dividendos/splits); usar solo rendimiento simple (rechazado: menos útil para modelos).
- **Evidencia utilizada:** Literatura estándar de finanzas cuantitativas.
- **Impacto:** Todas las métricas posteriores (volatilidad, correlaciones, riesgo) se basan en estos rendimientos.
- **Estado:** Aprobada

---

### DEC-009: Tratamiento de valores extremos

- **Fecha:** 2026-08-19
- **Fase:** Fase 3 — Análisis exploratorio
- **Decisión:** Los valores extremos (outliers) se **identifican** (z-score y percentiles) y se documentan en `resultados/posibles_outliers.csv`, pero **NO se eliminan automáticamente**.
- **Motivo:** Muchos "outliers" corresponden a eventos reales de mercado (p. ej., marzo de 2020, OPA de Nutresa). Eliminarlos sin justificación sesgaría el análisis (principio metodológico #4).
- **Alternativas consideradas:** Eliminar outliers de forma automática (rechazado: viola el principio de no modificar datos sin justificar).
- **Evidencia utilizada:** El reporte muestra que los extremos coinciden con eventos conocidos del mercado.
- **Impacto:** El conjunto de datos se conserva íntegro; cualquier exclusión futura deberá justificarse explícitamente.
- **Estado:** Aprobada

---

### DEC-010: Auditoría de tickers

- **Fecha:** 2026-09-15
- **Fase:** Fase 3.5 — Auditoría
- **Decisión:** Se auditaron los 9 tickers consultando los metadatos de Yahoo Finance (`yf.Ticker(tk).info`). Resultado: los 9 corresponden a la BVC (Bolsa de Valores de Colombia), moneda COP, país Colombia, `market=co_market`, tipo EQUITY.
- **Motivo:** Verificar de forma independiente que los tickers corresponden a las empresas colombianas esperadas y no a otro mercado (p. ej., Chile).
- **Alternativas consideradas:** Confiar en el reporte previo sin verificar (rechazado); usar otra fuente (no disponible).
- **Evidencia utilizada:** Metadatos de Yahoo Finance registrados en `resultados/auditoria_tickers.csv`.
- **Impacto:** Confirma la validez del universo de activos. Corrige la advertencia previa: el sufijo `.CL` en Yahoo Finance mapea al mercado colombiano (co_market), NO a Chile.
- **Estado:** Aprobada

---

### DEC-011: Auditoría de observaciones repetidas / liquidez

- **Fecha:** 2026-09-15
- **Fase:** Fase 3.5 — Auditoría
- **Decisión:** Se analizaron las filas con OHLCV repetido y volumen cero. Resultado: 0 fechas duplicadas en las 9 empresas; entre 38 y 125 filas consecutivas con OHLCV idéntico al día anterior; entre 115 y 206 días con volumen cero. Se concluye que corresponden a **días sin negociación** (iliquidez) y NO a errores ni fechas duplicadas.
- **Motivo:** No asumir que los "duplicados" reportados eran días sin negociación sin evidencia.
- **Alternativas consideradas:** Eliminar o corregir estas filas (rechazado: son datos reales de iliquidez).
- **Evidencia utilizada:** `resultados/auditoria_liquidez.csv` (conteos por caso A/B/C/D).
- **Impacto:** Estas observaciones se conservan. Se documenta que la ausencia de negociación es una característica del mercado colombiano.
- **Estado:** Aprobada

---

### DEC-012: Tratamiento del valor faltante de Grupo Bolívar

- **Fecha:** 2026-09-15
- **Fase:** Fase 3.5 — Auditoría
- **Decisión:** Se verificó el único valor faltante de precios: Grupo Bolívar, `2026-03-10` (martes), con `Open/High/Low/Close/Adj Close = NaN` y `Volume=0`. Es una única observación; el día anterior (lunes) y el siguiente (miércoles) tienen datos normales. Se decidió **no eliminar la fila y no modificar el CSV crudo**, y tratarla mediante imputación (ver DEC-013).
- **Motivo:** Es un día sin negociación en el que Yahoo no devolvió precios (a diferencia de otros días de volumen cero donde sí los devuelve replicando el cierre anterior).
- **Alternativas consideradas:** Eliminar la fila (rechazado); replicar el precio anterior (rechazado: sesgado); interpolación lineal simple (rechazada: no usa el modelo estadístico).
- **Evidencia utilizada:** Inspección directa del CSV crudo (`GRUBOLIVAR_CL.csv`) en la ventana 2026-03-06 a 2026-03-13.
- **Impacto:** Establece el alcance de la imputación: exactamente 1 valor (1 fecha, 1 activo).
- **Estado:** Aprobada

---

### DEC-013: Uso del Filtro de Kalman para imputación

- **Fecha:** 2026-09-15
- **Fase:** Fase 3.5 — Imputación
- **Decisión:** Se implementa la imputación del valor faltante mediante un **modelo de nivel local** (local level) estimado con el **Filtro de Kalman** y suavizado, usando `statsmodels.tsa.statespace.UnobservedComponents(level="local level")`. Se imputa únicamente la variable `Adj Close` (la usada para rendimientos). Los datos crudos permanecen intactos; el valor imputado se guarda con bandera.
- **Motivo:** Es un método estadístico estándar para reconstruir faltantes en series de tiempo que combina información pasada y futura de forma óptima (bajo el modelo). No requiere instalar librerías nuevas (statsmodels ya está en el proyecto).
- **Alternativas consideradas:** Interpolación lineal (rechazada: no es un modelo estadístico); last observation carried forward (rechazada: sesgada); usar una librería nueva como `pykalman` (rechazada: innecesaria).
- **Evidencia utilizada:** Prueba artificial: se ocultaron observaciones reales y se reconstruyeron; error relativo MAE ≈ 0.8%–1.5% (ver `resultados/validacion_kalman.csv`).
- **Impacto:** Define la metodología de imputación para las fases posteriores.
- **Estado:** Aprobada

---

### DEC-014: Uso de Kalman smoothing (reconstrucción retrospectiva)

- **Fecha:** 2026-09-15
- **Fase:** Fase 3.5 — Imputación
- **Decisión:** Se utiliza **suavizado de Kalman** (smoothing), es decir, se emplea información **posterior** al valor faltante para estimarlo.
- **Motivo:** Para la reconstrucción histórica de un valor faltante es metodológicamente válido usar toda la información disponible (antes y después).
- **Alternativas consideradas:** Usar solo filtrado (solo información pasada), que produce una estimación secuencial pero no aprovecha la información posterior (menos precisa para este caso).
- **Evidencia utilizada:** Teoría de espacios de estado; se documenta explícitamente la distinción con la predicción en tiempo real.
- **Impacto:** El valor imputado es una reconstrucción retrospectiva, no una predicción.
- **Estado:** Aprobada

---

### DEC-015: Prohibición de usar la imputación retrospectiva en backtesting

- **Fecha:** 2026-09-15
- **Fase:** Fase 3.5 — Imputación
- **Decisión:** Se establece explícitamente que la imputación mediante suavizado de Kalman **NO puede usarse directamente** como información disponible en tiempo real para backtesting o predicción sin adaptar el procedimiento (evitar data leakage).
- **Motivo:** El suavizado usa información futura; usarlo en predicción/backtesting constituiría fuga de datos.
- **Alternativas consideradas:** Ignorar esta advertencia (rechazado).
- **Evidencia utilizada:** Principio metodológico #2 (evitar data leakage) y #6 (orden temporal).
- **Impacto:** Protege la validez de los modelos y del backtesting en fases posteriores.
- **Estado:** Aprobada

---

### DEC-016: Inmutabilidad de los datos crudos

- **Fecha:** 2026-09-15
- **Fase:** Fase 3.5 — Imputación
- **Decisión:** Se reafirma que `datos/crudos/` permanece **inmutable**. La imputación genera columnas/archivos nuevos en `datos/procesados/` con banderas `es_imputado_kalman` y `retorno_depende_imputacion`, sin tocar los CSV crudos.
- **Motivo:** Garantizar trazabilidad: el valor original (NaN) se preserva y el valor imputado se identifica explícitamente.
- **Alternativas consideradas:** Sobrescribir el crudo con el valor imputado (rechazado: viola la regla #2).
- **Evidencia utilizada:** Verificación directa: el crudo conserva `NaN` y el procesado contiene el valor imputado con bandera `True`.
- **Impacto:** Establece el patrón de trazabilidad para toda imputación futura.
- **Estado:** Aprobada

---

### DEC-017: Partición temporal por fechas de corte

- **Fecha:** 2026-09-27
- **Fase:** Fase 4 — Análisis exploratorio
- **Decisión:** Se reemplaza la partición por proporciones (70/15/15) por **fechas de corte** en `config/settings.py`: entrenamiento hasta 2023-12-31 (1 043 obs.), validación 2024 (255 obs.) y prueba desde 2025-01-01 hasta el final de la muestra (426 obs.). El bloque de prueba permanece intocable hasta la evaluación final. Las pruebas formales de la Fase 4 se calculan **solo sobre entrenamiento**.
- **Motivo:** Evitar data leakage: las decisiones del EDA (modelos, transformaciones, exclusiones) no deben depender de la información de validación/prueba. Las fechas son explícitas y reproducibles; las proporciones dependen de cuándo se ejecute el pipeline (FECHA_FIN = hoy).
- **Alternativas consideradas:** Mantener 70/15/15 (rechazada: el corte se mueve con la fecha de ejecución); partición aleatoria (rechazada: mezcla pasado y futuro).
- **Evidencia utilizada:** `resultados/particion_temporal.csv`; `src/preprocessing/split.py` con tests.
- **Impacto:** El evento del 2024-05-03 (ver DEC-018) cae en **validación**, por lo que su tratamiento afecta las métricas de validación.
- **Estado:** Pendiente de aprobación del equipo (las fechas son una propuesta).

---

### DEC-018 (HALLAZGO Fase 4): Iliquidez y saltos reversibles de precio

- **Fecha:** 2026-09-27
- **Fase:** Fase 4 — Análisis exploratorio
- **Observación:** Al analizar la volatilidad móvil de 30 días se detectó un comportamiento anómalo en Promigas (rendimientos de -25,8 % el 2024-05-03 y +26,5 % el 2024-05-06). Se investigó como posible error de dato o iliquidez.
- **Evidencia:**
  - El volumen del día del salto (15 031) está en línea con la mediana histórica de la acción (13 283): **no** parece una consecuencia de baja negociación.
  - Ese día la vela de Promigas es plana (Open = High = Low = Close = 5 100, frente a 6 600 el día anterior y 6 650 el siguiente) y el precio se recupera por completo al día siguiente.
  - **El mismo patrón aparece el mismo día en otras acciones:** Nutresa (+24,6 %, vela plana 46 700 frente a 36 500) y Mineros (-23,0 %), ambas revertidas el 2024-05-06. Ver `resultados/saltos_reversibles.csv` y `resultados/contexto_saltos.csv`. Otras fechas con reversión simultánea en varias acciones: 2025-02-19 (Ecopetrol y Nutresa) y 2025-09-30 (Nutresa y Mineros).
  - Sin ese par de días, la volatilidad móvil anualizada máxima de Promigas baja de 112 % a 62 %.
  - Auditoría de iliquidez (`resultados/auditoria_iliquidez_umbral.csv`, precio de cierre crudo, umbral de referencia 20 % de precio repetido / racha máxima de 15 días): superan el umbral 5 de 9 empresas: ETB (60,9 %, racha 67), Promigas (32,7 %), Nutresa (30,9 %, racha 22), Grupo Bolívar (27,2 %) y Mineros (20,4 %, racha 20).
- **Interpretación provisional:** Que el volumen sea normal descarta la iliquidez como causa, pero **no** descarta un precio anómalo. La combinación de vela plana, reversión inmediata y coincidencia entre varias acciones apunta más a un problema de la fuente (Yahoo Finance, sufijo `.CL`) o a un evento de mercado común que a un problema propio de Promigas. Es una hipótesis, no una conclusión.
- **Acción pendiente:** Contrastar estas fechas con una segunda fuente (BVC u otra) antes de decidir.
- **Estado:** **Resuelto para 2024-05-03 por DEC-022** (error de la fuente en las 9 empresas, contrastado con el ADR de Ecopetrol). Los saltos de ETB de 2023-09 se conservan (iliquidez). Las fechas de 2025 están en el bloque de prueba y no se tratan (ver DEC-022).

---

### DEC-019: Fase 5 — Congelación y blindaje de la partición temporal

- **Fecha:** 2026-09-30
- **Fase:** Fase 5 — Separación entrenamiento / validación / prueba
- **Decisión:** La partición cronológica propuesta en DEC-017 se formaliza y se guarda en archivos separados dentro de `datos/particiones/` (rendimientos log y precios, cada uno en `_train`, `_validacion` y `_test`). Cortes: entrenamiento hasta 2023-12-31 (1 043 obs.), validación 2024 (255 obs.) y prueba desde 2025-01-01 (426 obs. con los datos al 2026-09-14). Se agregan: (1) `verificar_sin_leakage` (orden, sin solape, sin pérdida de filas); (2) `cargar_particion`, que exige `confirmar_evaluacion_final=True` para leer el bloque de prueba; (3) huellas SHA-256 por bloque en `datos/particiones/huellas.json` para detectar alteraciones; (4) tests anti-leakage en `tests/test_particion_fase5.py`.
- **Motivo:** Evitar data leakage. Nunca se usa partición aleatoria en series de tiempo: mezclaría pasado y futuro. La prueba (2025 en adelante) debe permanecer intocable hasta la evaluación final; ninguna transformación, imputación, selección de empresas ni ajuste de hiperparámetros puede usar sus datos.
- **Regla operativa:** Todo estimador (media, covarianza, escalado, modelos) se ajusta solo con entrenamiento; la validación sirve para elegir modelos e hiperparámetros; la prueba se lee una sola vez, al final.
- **Alternativas consideradas:** Partición aleatoria 80/20 (rechazada: leakage); proporciones 70/15/15 (rechazada en DEC-017: el corte se mueve con la fecha de ejecución).
- **Evidencia utilizada:** `resultados/particion_temporal.csv`; `datos/particiones/huellas.json`; 10 tests nuevos (56 en total).
- **Puntos abiertos:** (a) `FECHA_FIN = None` hace que el bloque de prueba crezca cada vez que se vuelven a descargar los datos; conviene fijar una fecha final de muestra antes de la evaluación final. (b) El evento del 2024-05-03 (DEC-018) cae en validación. (c) Con un solo bloque de prueba (2025 en adelante) la evaluación final tiene un único escenario; el backtesting walk-forward de fases posteriores lo complementará.
- **Auditoría de cierre (2026-09-30):** (1) Train, validación y prueba identificadas: ≤ 2023-12-29, 2024 y ≥ 2025-01-02; sin solapamiento y reconstruyen exactamente `rendimientos_log.csv` y `precios.csv` (verificado por tests sobre los archivos reales). (2) Las únicas imputaciones de Kalman son 1 valor de Grupo Bolívar (2026-03-10), dentro del bloque de prueba; en train y validación los precios procesados coinciden con los crudos (0 diferencias) y no hay imputaciones. (3) No existe aún ningún escalador ni estimador ajustado en `src/`; cuando aparezca, se ajusta solo con train. (4) Los resultados exploratorios de la Fase 3 se calcularon con toda la muestra y no deben usarse para decidir. (5) La auditoría de iliquidez recalculada solo con train confirma las mismas 5 empresas sobre el umbral (ETB 45,3 %, Grupo Bolívar 35,3 %, Promigas 33,3 %, Nutresa 21,4 %, Mineros 20,4 %); Banco de Bogotá queda cerca (19,2 %). (6) Advertencia: el análisis de saltos de DEC-018 miró fechas de 2025 (2025-02-19, 2025-09-30); fue un control de calidad del dato, no una selección de modelos, pero el tratamiento que se decida debe justificarse con train/validación.
- **Estado:** Pendiente de aprobación del equipo (depende de la aprobación de las fechas de DEC-017).

---

### DEC-020: Fase 6 — Benchmark de Markowitz

- **Fecha:** 2026-10-01
- **Fase:** Fase 6 — Modelo de referencia
- **Decisión:** Se construye el benchmark con `src/portfolio/` (`markowitz.py`, `metricas.py`, `fase6.py`). Media y covarianza se estiman **solo con entrenamiento** (rendimientos simples, R = exp(r) − 1, anualizados con 252 días); los pesos quedan fijos y se evalúan en entrenamiento (dentro de muestra) y validación (fuera de muestra). Portafolios: igual ponderación (1/N), mínima varianza y máximo Sharpe. Restricciones: suma 1, sin cortos, peso máximo 30 % por activo. Dos universos: las 9 empresas y las 4 líquidas según entrenamiento (Celsia, Banco de Bogotá, Ecopetrol, Davivienda PF).
- **Motivo:** Tener un punto de comparación antes de ARIMA/GARCH/ML/LSTM, sin tocar la prueba.
- **Criterio de liquidez:** proporción de rendimientos exactamente cero en entrenamiento, umbral 20 % (el mismo de DEC-018). Quedan como ilíquidas ETB, Grupo Bolívar, Promigas, Nutresa y Mineros. Nutresa (20,7 %) y Mineros (20,1 %) están al borde del umbral: la clasificación es frágil.
- **Faltantes:** se descartan filas completas con algún NaN (4 en entrenamiento y 8 en validación para las 9 empresas); no se imputa. Los NaN de 2023-06-09 y 2023-06-12 y otras fechas son días sin precio en Yahoo para 8 de 9 acciones (Nutresa trae el precio repetido).
- **Supuesto provisional:** tasa libre de riesgo = 0 (`TASA_LIBRE_RIESGO_ANUAL`, [PLACEHOLDER]); no hay serie de tasas en el proyecto. El Sharpe absoluto no es comparable con el mercado real hasta sustituirla.
- **Hallazgos (no son conclusiones):** (1) En entrenamiento el retorno medio de casi todas las acciones es cercano a cero o negativo; con las 4 líquidas ningún portafolio factible supera la tasa libre de riesgo (Sharpe máximo −0,04), así que el "máximo Sharpe" es degenerado. (2) En validación (2024, año alcista) el orden se invierte respecto a entrenamiento: el máximo Sharpe fue el mejor dentro de muestra y el peor de los tres fuera de muestra en el universo de 9, lo que es consistente con error de estimación de la media. (3) El máximo Sharpe con 9 empresas pone 30 % en Nutresa y 30 % en Ecopetrol; Nutresa es una de las acciones con saltos reversibles (DEC-018). (4) Validación incluía el evento del 2024-05-03; desde DEC-022 ese precio es inválido y las métricas de validación se recalcularon (el orden de los portafolios no cambia).
- **Alternativas consideradas:** usar rendimientos logarítmicos directamente (rechazada: no agregan linealmente en el portafolio); imputar faltantes (rechazada: AGENTS.md); elegir el portafolio de referencia mirando validación (rechazada: sesgo de selección).
- **Evidencia utilizada:** `resultados/fase6_pesos.csv`, `fase6_metricas.csv`, `fase6_parametros_train.csv`, `fase6_universo_liquidez_train.csv`, `resultados/graficos/fase6_frontera_eficiente.png`; `tests/test_markowitz_fase6.py`.
- **Puntos abiertos:** (a) El equipo debe fijar, **antes** de mirar más resultados, cuál portafolio es "el benchmark" (la propuesta: mínima varianza por ser más estable que máximo Sharpe, con 1/N como referencia). (b) Sustituir la tasa libre de riesgo. (c) Sin clasificación sectorial en el repo no se aplicaron límites por sector. (d) ~~Resolver DEC-018 antes de congelar resultados~~ (resuelto por DEC-022).
- **Estado:** Pendiente de aprobación del equipo.

---

### DEC-021: Fecha final fija, crudos protegidos y regeneración exacta de la partición

- **Fecha:** 2026-10-03
- **Fase:** Mantenimiento (antes de la Fase 7)
- **Problema detectado:** (1) `python -m src.pipeline` (paso 2 del README) volvía a descargar con `FECHA_FIN = None`, **sobrescribía `datos/crudos/`** (viola la inmutabilidad, DEC-016) y alargaba el bloque de prueba; como también regeneraba `huellas.json`, las huellas no habrían detectado el cambio. (2) Los archivos de `datos/particiones/` no eran copia exacta de `datos/procesados/`: diferían en el último dígito (máx. 2,3e-13 en precios del orden de miles; 1,0e-16 en rendimientos log), probablemente porque la Fase 5 leyó los crudos con el lector de floats por defecto de pandas, que no es exacto.
- **Decisión:**
  - `FECHA_FIN = "2026-09-15"` en `config/settings.py`. Yahoo trata `end` como exclusivo: última observación 2026-09-14, idéntica a la descarga original (`fecha_fin_solicitada` en los metadatos). Resuelve el punto abierto (a) de DEC-019.
  - `guardar_datos_crudos` lanza `FileExistsError` si algún archivo crudo ya existe, antes de escribir nada.
  - El pipeline, por defecto, **lee los crudos guardados** (`cargar_resultados_crudos`, con `float_precision="round_trip"`) y no descarga. La descarga exige `--descargar` y solo funciona con `datos/crudos/` vacío.
  - La Fase 5 compara las huellas nuevas con `huellas.json` antes de guardar (`comparar_con_huellas_guardadas`); si difieren lanza `ValueError` y no reescribe la partición.
  - Con aprobación del usuario, se regeneraron `datos/particiones/` y `huellas.json` desde los crudos leídos de forma exacta.
- **Evidencia:** Reprocesar los crudos con lectura exacta reproduce `datos/procesados/` bit a bit. Train y validación regenerados: mismas fechas y columnas, iguales a `datos/procesados/`, cambio máximo 2,3e-13 (precios) y 1,0e-16 (rendimientos). El bloque de prueba se regeneró con el mismo código, **sin abrirlo ni inspeccionarlo**. Una segunda ejecución del pipeline pasa la verificación de huellas (reproducible). Resultados de Fase 4 regenerados (`pruebas_*`, `saltos_reversibles.csv`): cambio ≤ 2,7e-15 y ninguna columna categórica (decisiones de las pruebas, fechas de saltos) cambia. Fase 6 reejecutada: parámetros ±5e-16, pesos y métricas ±1,4e-8 (tolerancia del optimizador SLSQP, igual que reejecutar sin cambios); se conservan los resultados versionados de DEC-020. 12 tests nuevos en `tests/test_proteccion_crudos.py` (90 en total).
- **Alternativas consideradas:** Mantener la partición antigua (rechazada: el pipeline no podría reejecutarse completo); comparar huellas con tolerancia numérica (rechazada: obligaría a abrir el bloque de prueba desde `src/`); permitir sobrescribir crudos con una bandera (rechazada: una nueva descarga es una decisión metodológica que debe hacerse a mano y registrarse aquí).
- **Impacto:** El pipeline es reproducible sin red y no puede alterar los crudos ni la partición congelada en silencio. Ninguna conclusión de las Fases 4 a 6 cambia.
- **Estado:** Aplicada (pendiente de revisión del equipo).

---

### DEC-022: Precio inválido de la fuente el 2024-05-03 (resuelve DEC-018)

- **Fecha:** 2026-10-04
- **Fase:** Fase 3 — Limpieza (retoma el hallazgo DEC-018 antes de la Fase 7)
- **Evidencia (solo entrenamiento y validación; el bloque de prueba no se inspeccionó):**
  - El 2024-05-03 **las 9 empresas**, no solo 3, tienen un precio fuera de línea que se revierte el 2024-05-06: Banco de Bogotá +12,8 %, Nutresa +24,6 %, Promigas −25,8 %, Mineros −23,0 %, Grupo Bolívar −12,2 %, Davivienda PF −8,2 %, Celsia −8,5 %, Ecopetrol −6,2 %, ETB −5,1 % (log), y al día siguiente lo contrario.
  - Barrido de 1 298 días de entrenamiento y validación: es el **único día** en que dos o más acciones tienen un salto ≥ 5 % revertido al día siguiente. Los otros 54 saltos revertidos son aislados (17 de ETB) y coherentes con iliquidez.
  - **Segunda fuente:** el ADR de Ecopetrol en NYSE (EC, 1 ADR = 20 acciones), convertido con USD/COP, varió −0,42 % el 2024-05-03 (+0,36 % el 05-06), mientras el dato local de Yahoo da −6,0 % y +6,1 %. Precio implícito del ADR ≈ 2 248 COP frente a 2 120 COP en Yahoo. Rendimiento local de 2 días (2 → 6 may) tras el tratamiento: −0,22 %, coherente con el ADR.
  - No se pudo obtener precio diario de la BVC ni de Investing.com (no accesibles); los tickers locales de Bancolombia y el COLCAP ya no están en Yahoo.
  - Nota lateral: en el feed `.CL` de Yahoo la apertura (`Open`) suele ser el cierre anterior y hay 586 filas con OHLC incoherente en entrenamiento y validación; el proyecto solo usa `Adj Close`, así que no lo afecta, pero `Open/High/Low` no deben usarse sin revisarlos.
- **Decisión:** En la capa procesada (los crudos no se tocan) el precio del 2024-05-03 queda **NaN para las 9 empresas** con bandera (`datos/procesados/banderas_dato_invalido.csv`, columnas `es_dato_invalido_fuente` y `retorno_abarca_dato_invalido` en `dataset_analisis.csv`). El rendimiento del 2024-05-06 es el de 2 días (2 → 6 de mayo). No se imputa ni se usa información posterior. Configuración: `FECHAS_DATO_INVALIDO_FUENTE` en `config/settings.py`; código en `src/preprocessing/invalid_data.py`. La anulación se aplica **después** de la imputación de Kalman para que esta no la rellene y para no alterar la imputación de Grupo Bolívar (bloque de prueba).
- **Alternativas consideradas:** Imputar con Kalman (rechazada: el suavizado usa el precio del 6 de mayo, información futura dentro de validación, DEC-015); solo documentar (rechazada: infla la volatilidad de validación); eliminar la fila (rechazada: se perdería la trazabilidad).
- **Impacto verificado:** Solo cambian las filas 2024-05-03 y 2024-05-06 de los procesados. Huellas: cambian únicamente `precios_validacion` y `rendimientos_log_validacion`; **entrenamiento y prueba quedan idénticos** (la protección de DEC-021 lo detectó y se regeneró la partición de forma deliberada; una segunda ejecución reproduce las huellas). Fase 6: pesos y métricas de entrenamiento sin cambios (±1,4e-8, tolerancia del optimizador); en validación con 9 empresas la volatilidad de mínima varianza baja de 19,3 % a 13,1 % y su Sharpe sube de 2,03 a 2,76; el orden de los tres portafolios en validación no cambia (mínima varianza > 1/N > máximo Sharpe). Se regeneran los resultados exploratorios de la Fase 3 (muestra completa) y `saltos_reversibles.csv`. 7 tests nuevos (97 en total).
- **Pendiente:** Las fechas de 2025 con el mismo patrón señaladas en DEC-018 (2025-02-19, 2025-09-30) están en el bloque de prueba: no se tratan ahora. Antes de la evaluación final el equipo debe fijar una regla general (p. ej. "día en que ≥ 2 acciones tienen un salto ≥ 5 % revertido al día siguiente y una segunda fuente lo contradice"), definida con entrenamiento y validación, y aplicarla mecánicamente a la prueba.
- **Estado:** Aplicada (pendiente de revisión del equipo).

---

### DEC-023: Fase 7 — ARIMA (media) y GARCH(1,1) (volatilidad)

- **Fecha:** 2026-10-04
- **Fase:** Fase 7 — Econometría
- **Decisión (diseño):**
  - Rendimiento logarítmico diario por empresa; cada serie usa sus propios días con dato (se descartan explícitamente los NaN de esa empresa, sin imputar). Parámetros estimados **solo con entrenamiento**; evaluación en validación con pronósticos **a un paso y parámetros fijos** (el valor de t usa datos hasta t−1). Sin reestimación dentro de validación (eso es el backtesting walk-forward, Fase 14). Prueba no utilizada.
  - **ARIMA(p,0,q)** con constante, d = 0 (ADF/KPSS de la Fase 4 en entrenamiento: las 9 series son estacionarias). Rejilla p, q ≤ 3, selección por **BIC** entre los modelos que convergen. Referencias: pronóstico cero y media de entrenamiento. Métricas MAE, RMSE y Diebold-Mariano (pérdida cuadrática, corrección HLN).
  - **GARCH(1,1)** con media constante e innovaciones **t de Student** (Jarque-Bera rechaza normalidad en las 9). Referencias: varianza constante de entrenamiento y EWMA RiskMetrics (λ = 0,94, sin estimación). Proxy de la varianza: r_t². Métricas QLIKE robusto (admite r_t = 0) y MSE; Diebold-Mariano sobre QLIKE.
  - Ajustes en rendimientos ×100: con rendimientos en proporción el optimizador de `statsmodels` declaraba "no convergencia" en modelos simples (AR(1) de Promigas y Grupo Bolívar, MA(1) de Davivienda) con los mismos parámetros y BIC; en % convergen. Tras el cambio solo 10 de 144 modelos de la rejilla no convergen, todos con p + q ≥ 5; quedan registrados en `fase7_arima_seleccion.csv`.
  - Dependencia nueva: `arch==8.0.0` (no cambió ninguna otra versión).
- **Resultados (validación 2024; son hallazgos, no conclusiones definitivas):**
  - **Media (ARIMA):** órdenes elegidos (0,0) en 4 empresas, AR(1) en Ecopetrol y Mineros, AR(2) en Celsia, MA(1) en Promigas, MA(3) en ETB. **Ningún ARIMA pronostica mejor que la media de entrenamiento ni que el cero** (Diebold-Mariano p > 0,14 en las 9). La autocorrelación detectada en entrenamiento (Fase 4) no se traduce en capacidad predictiva fuera de muestra.
  - **Volatilidad (GARCH), 4 líquidas:** GARCH supera a la varianza constante con significancia en Banco de Bogotá y Ecopetrol (p < 0,001), no en Celsia (p = 0,24) ni Davivienda (p = 0,08). **No supera a EWMA en ninguna**; EWMA tiene menor QLIKE en las 4 y es significativamente mejor en Celsia (p = 0,050). La persistencia α + β es ≈ 1 (0,92–1,00), cercana a un IGARCH, que es justamente lo que impone EWMA.
  - **Volatilidad, 5 ilíquidas:** resultados poco fiables. ETB (91 % de rendimientos cero en validación): ω ≈ 0, la varianza pronosticada colapsa a ~5e-7 tras cada racha sin negociación y un movimiento de −10,5 % dispara la pérdida (QLIKE ≈ 1,25 millones): **GARCH no es adecuado para ETB**. Promigas: GARCH significativamente peor que la varianza constante (sobreestima el nivel). Grupo Bolívar: mejor que la constante (p = 0,008), igual a EWMA. Grados de libertad ν entre 2,1 y 2,5 en las ilíquidas (colas extremas, efecto de los días sin negociación).
  - **Diagnósticos:** sin autocorrelación remanente en z_t² salvo Davivienda (p = 0,026) y Ecopetrol al borde (p = 0,053). En 6 empresas la persistencia toca el límite α + β = 1 (`estacionario = False` cuando es exactamente 1).
- **Implicaciones para fases siguientes:** (1) Para la media no hay evidencia de que ARIMA aporte sobre una media constante: en la optimización (Fase 12) usar ARIMA como estimador de rendimientos esperados no está justificado con esta evidencia. (2) Para la volatilidad de las líquidas, EWMA es una referencia exigente que GARCH no supera; la Fase 11 (riesgo) debería comparar ambos. (3) Las 5 ilíquidas requieren otro tratamiento (o exclusión) para modelos de volatilidad; refuerza el universo de 4 líquidas de DEC-020.
- **Alternativas consideradas:** selección por AIC (rechazada: con ~1 000 observaciones tiende a sobreajustar); GARCH con errores normales (rechazada: colas pesadas); EGARCH/GJR (aplazadas: primero establecer si el GARCH básico supera referencias simples, y no lo hace frente a EWMA); reestimar en cada paso (aplazada a la Fase 14); un único criterio en validación para elegir el modelo final (no se elige aún; validación solo compara).
- **Evidencia utilizada:** `resultados/fase7_arima.csv`, `fase7_arima_seleccion.csv`, `fase7_garch.csv`, `fase7_pronosticos_validacion.csv`, `resultados/graficos/fase7_volatilidad_validacion.png`; código en `src/econometrics/` (`arima.py`, `garch.py`, `evaluacion.py`, `fase7.py`); 12 tests en `tests/test_econometria_fase7.py` (incluyen que los pronósticos no cambian al alterar datos futuros).
- **Estado:** Pendiente de aprobación del equipo.

---

### DEC-024: Variables externas (TRM y Brent) y ampliación de la partición congelada

- **Fecha:** 2026-10-04
- **Fase:** Fase 2 (base de datos) y Fase 5 (partición), como preparación de la Fase 8
- **Decisión:**
  - Se descargan **una vez** de Yahoo Finance la TRM (`COP=X`) y el petróleo Brent (`BZ=F`), con el mismo horizonte de las acciones (2020-01-01 a 2026-09-14, `FECHA_FIN` fija). Se guardan como crudos inmutables en `datos/crudos/externos/` (misma protección que DEC-021) con metadatos en `datos/metadata/externos/`. Código: `src/data/externos.py`; `python -m src.pipeline --descargar` también las descarga. El índice COLCAP no está disponible en Yahoo; tasa de interés e inflación quedan pendientes (requieren otras fuentes).
  - El **volumen** de las acciones (con el 2024-05-03 en NaN por DEC-022) y las **externas** (en su propio calendario) se agregan a la partición de la Fase 5 (`volumen_*` y `externos_*` en `datos/particiones/`, con huellas). Así la Fase 8 no necesita leer crudos completos, que incluyen el periodo de prueba.
  - `comparar_con_huellas_guardadas` ahora permite **agregar** series nuevas; las huellas ya registradas deben seguir coincidiendo exactamente y no pueden desaparecer.
- **Evidencia:** Las 6 huellas existentes no cambiaron al regenerar; se agregaron 6 nuevas. Una segunda ejecución del pipeline reproduce todas. Faltantes en los crudos externos (todo el periodo): 1 día en TRM y 59 en Brent (calendarios distintos); no se rellenan.
- **Alternativas consideradas:** leer los crudos externos en la Fase 8 y recortarlos por fecha (rechazada: cargaría en memoria el periodo de prueba); sincronizar las externas con el calendario de la BVC al guardarlas (rechazada: la regla de sincronización es una decisión de modelado y va en la Fase 8).
- **Estado:** Aplicada (pendiente de revisión del equipo).

---

### DEC-025: Fase 8 — Random Forest y Gradient Boosting para el rendimiento del día siguiente

- **Fecha:** 2026-10-04
- **Fase:** Fase 8 — Machine Learning
- **Decisión (diseño):**
  - **Objetivo:** rendimiento logarítmico de t+1 con información disponible al cierre de t (regresión), comparable con ARIMA y las referencias de la Fase 7.
  - **Variables** (`src/machine_learning/variables.py`): rendimientos de t a t−4; media y volatilidad móviles de 5 y 21 días; proporción de rendimientos cero en 21 días (iliquidez); volumen relativo (log del volumen menos su mediana de 21 días); rendimiento promedio del mercado (las 9) en t y su media de 5 días; rendimientos de 1 y 5 días de TRM y Brent con fecha **estrictamente anterior** a t (su cierre en Yahoo es posterior al de la BVC; tolerancia de 7 días); indicador de empresa.
  - **Modelo agrupado** de las 9 empresas (≈ 9 000 filas de entrenamiento) en vez de uno por empresa (≈ 1 000).
  - **Anti-leakage:** cada fila se asigna a entrenamiento o validación por la **fecha del objetivo**; filas con faltantes se descartan y se cuentan (train: 208 de 9 378; validación: 176 de 2 295, incluye el 2024-05-03 y sus rezagos).
  - **Hiperparámetros:** validación cruzada temporal expansiva de 5 pliegues **dentro de entrenamiento**, por fechas (un mismo día nunca queda en dos pliegues); rejilla de 8 combinaciones por modelo; semilla 42. La validación solo se usa para comparar. Elegidos: Random Forest `max_depth=6, min_samples_leaf=50, max_features=0.3` (300 árboles); Gradient Boosting (`HistGradientBoostingRegressor`, el mismo método que XGBoost dentro de scikit-learn) `learning_rate=0.02, max_depth=2, min_samples_leaf=50` (300 iteraciones).
  - **Comparación** en validación sobre las mismas filas: pronóstico cero, media de entrenamiento y ARIMA de la Fase 7; RMSE, MAE y Diebold-Mariano frente a la media. Dependencia nueva: `scikit-learn==1.9.1`.
- **Resultados (validación 2024; hallazgos, no conclusiones definitivas):**
  - En la validación cruzada (train) el mejor Random Forest reduce el MSE solo 0,7 % frente a la media; **ningún Gradient Boosting supera a la media** en la validación cruzada.
  - En validación, agrupando las 9 empresas: RMSE Random Forest 0,02018, Gradient Boosting 0,02018, media de train 0,02024, cero 0,02023, ARIMA 0,02028. La mejora de los modelos de ML (≈ 0,3 % del RMSE) **no es significativa** (Diebold-Mariano p = 0,41 y 0,57). Por empresa, ningún p-valor es < 0,05; el más bajo es Promigas (p ≈ 0,07), donde además el ARIMA MA(1) tiene el menor RMSE.
  - **Importancia por permutación** (validación): domina el rendimiento del día (`r_lag0`, coherente con reversión de corto plazo y rebote por iliquidez) y el volumen relativo. TRM y Brent aportan prácticamente nada.
- **Implicación:** Con estas variables, ni ARIMA (DEC-023) ni Random Forest / Gradient Boosting predicen el rendimiento diario mejor que una media constante de forma estadísticamente distinguible. Para la Fase 9 (redes neuronales) la referencia exigente es la media; para la optimización (Fase 12) no hay, por ahora, evidencia para sustituir la media histórica por pronósticos de modelos.
- **Alternativas consideradas:** modelos por empresa (rechazada: pocas observaciones); ajustar hiperparámetros con validación (rechazada: sesgaría la comparación con ARIMA); clasificación de la dirección (aplazada); XGBoost como librería aparte (descartada: `HistGradientBoosting` cubre el mismo método sin otra dependencia).
- **Evidencia utilizada:** `resultados/fase8_*.csv` (filas, validación cruzada, hiperparámetros, métricas, pronósticos, importancia) y `resultados/graficos/fase8_importancia.png`; código en `src/machine_learning/`; 8 tests en `tests/test_machine_learning_fase8.py` (variables sin información futura, externas con fecha anterior, separación por fecha objetivo, pliegues sin solape, reproducibilidad).
- **Estado:** Pendiente de aprobación del equipo.

---

### DEC-026: Fase 9 — Redes neuronales MLP y LSTM

- **Fecha:** 2026-10-04
- **Fase:** Fase 9 — Red neuronal
- **Decisión (diseño):**
  - **Librería:** PyTorch 2.14.1 (CPU). TensorFlow no tiene versión para Python 3.14.
  - **Mismo problema y filas que la Fase 8:** objetivo r_{t+1}, panel agrupado de las 9 empresas, filas asignadas por fecha del objetivo (`src/machine_learning/variables.py`).
  - **MLP:** las mismas variables de la Fase 8, estandarizadas con media y desviación **solo de entrenamiento**; rejilla: capas ocultas (32) o (64, 32) y decaimiento de pesos 1e-4 o 1e-2; abandono 0,2.
  - **LSTM:** secuencias de los **últimos 30 días** de la empresa (rendimiento, volumen relativo, mercado, TRM y Brent, como en el borrador) + indicador de empresa en la capa de salida; rejilla: 16 o 32 unidades y decaimiento 1e-4 o 1e-2. Ventanas con algún faltante se descartan (no se imputa).
  - **Selección y parada temprana:** el último 20 % de fechas objetivo de **entrenamiento** es el conjunto de parada (nunca validación). Escaladores ajustados con la parte de ajuste durante la selección y con todo entrenamiento en el modelo final.
  - **Modelo final:** por cada una de 5 semillas fijas (42–46) se busca la época óptima con el conjunto de parada y se reentrena con todo entrenamiento durante esas épocas; la predicción es el promedio de las 5 (conjunto). Adam, MSE, lotes de 256, objetivo en % para estabilidad numérica, algoritmos deterministas.
  - **Comparación** en validación sobre las **mismas filas** para todos los modelos (MLP, LSTM, Random Forest, Gradient Boosting, ARIMA, media, cero): 1 631 filas. Se excluyen 488 de las 2 119 de la Fase 8 porque la LSTM necesita 30 días completos: 216 son ventanas que incluyen el 2024-05-03 (precio inválido, DEC-022) y el resto, otros días sin precio (más en ETB, Nutresa y Promigas).
- **Resultados (validación 2024; hallazgos, no conclusiones definitivas):**
  - Elegidos: MLP (64, 32) con decaimiento 1e-4; LSTM de 32 unidades con decaimiento 1e-4. Épocas óptimas entre 18 y 70.
  - En el conjunto de parada (final de entrenamiento) el MLP reducía el MSE 7,7 % frente a la media y la LSTM 2,9 %; **en validación esa ventaja desaparece**.
  - Validación, las 9 empresas juntas: RMSE MLP 0,01917, LSTM 0,01913, Random Forest 0,01905, Gradient Boosting 0,01903, media de entrenamiento 0,01915, ARIMA 0,01924. **Ni el MLP ni la LSTM superan a la media** (Diebold-Mariano p = 0,84 y 0,80).
  - Por empresa: MLP y LSTM son significativamente mejores que la media solo en Promigas (p ≈ 0,02), donde también ARIMA mejora a la media (la media de entrenamiento de Promigas se alejó de su comportamiento en 2024); el MLP es significativamente **peor** que la media en ETB (p = 0,037). Con 18 pruebas al 5 % se esperaría cerca de 1 resultado significativo por azar.
  - **Variabilidad entre semillas:** el RMSE de la LSTM varía entre semillas con desviación 0,00015 (máximo 0,01945), mayor que las diferencias entre modelos. Sin promediar semillas, el resultado de una red dependería de la inicialización.
- **Implicación:** Con estos datos y variables, ninguna familia de modelos (ARIMA, Random Forest, Gradient Boosting, MLP, LSTM) predice el rendimiento diario mejor que una media constante de forma estadísticamente distinguible. Coincide con la advertencia del borrador ("una red neuronal no es automáticamente mejor") y es un resultado válido para la Fase 10 (comparación de modelos).
- **Alternativas consideradas:** TensorFlow (no disponible para Python 3.14); `MLPRegressor` de scikit-learn (rechazada: no ofrece LSTM y conviene una sola librería para ambas redes); elegir hiperparámetros o la época con validación (rechazada: sesgaría la comparación); una sola semilla (rechazada: la variabilidad entre semillas es del mismo orden que las diferencias entre modelos); LSTM por empresa (rechazada: pocas secuencias por empresa).
- **Evidencia utilizada:** `resultados/fase9_*.csv` (selección, hiperparámetros, épocas, métricas, dispersión entre semillas, pronósticos); código en `src/neural_networks/` (`datos.py`, `redes.py`, `fase9.py`); 7 tests en `tests/test_redes_fase9.py` (escalado solo con ajuste, secuencias sin futuro, ventanas con faltantes descartadas, conjunto de parada al final, entrenamiento reproducible). Dependencia nueva: `torch==2.14.1`.
- **Estado:** Pendiente de aprobación del equipo.

---

### DEC-027: Fase 10 — Comparación de modelos con control de comparaciones múltiples

- **Fecha:** 2026-10-04
- **Fase:** Fase 10 — Comparación de modelos
- **Decisión (diseño):**
  - Se consolidan los pronósticos de **validación** de las Fases 7 a 9 (no se reentrena nada; se leen sus CSV). Media condicional: cero, media de entrenamiento, ARIMA, Random Forest, Gradient Boosting, MLP y LSTM sobre las mismas 1 631 filas (224 fechas). Varianza condicional: GARCH(1,1), EWMA y varianza constante.
  - **Dependencia entre empresas:** las pérdidas se promedian por fecha antes de las pruebas agregadas (las 9 acciones de un mismo día no son observaciones independientes).
  - **Pruebas:** Model Confidence Set de Hansen, Lunde y Nason (2011) con estadístico T_max al 10 %; R² fuera de muestra de Campbell y Thompson (2008) frente a la media, con IC 95 % por bootstrap de bloques móviles (bloques de 10 días, 2 000 réplicas, semilla 42); Diebold-Mariano frente a la media; acierto direccional con la prueba de Pesaran-Timmermann (1992). **Corrección de Holm** en cada familia de pruebas (DM agregadas, PT agregadas, 54 pruebas DM por empresa en media y 18 en varianza).
  - **Complejidad:** número de parámetros donde está definido (media 9, ARIMA 26 en total, MLP 3 841 y LSTM 5 034 por red, ×5 semillas) y método de selección de hiperparámetros.
- **Resultados (validación 2024; hallazgos, no conclusiones definitivas):**
  - **Rendimiento esperado:** los **7 modelos están en el MCS** (p_MCS ≥ 0,38): ninguno se distingue estadísticamente del mejor, incluidos el cero y la media. R²_OS frente a la media: Gradient Boosting 1,26 % [IC 0,00 %; 2,54 %], Random Forest 1,02 % [0,04 %; 2,08 %], cero 0,31 %, LSTM 0,07 % [−3,8 %; 3,2 %], MLP −0,17 %, ARIMA −1,12 %. Los intervalos de Random Forest y Gradient Boosting rozan el cero por arriba, pero Diebold-Mariano no rechaza (p = 0,16 y 0,20; 0,81 tras Holm) y el MCS no los separa: **evidencia débil, no concluyente**, de una mejora del orden de 1 % en el error cuadrático.
  - **Por empresa:** 5 de 54 pruebas con p < 0,05 sin corregir (cerca de 2,7 esperadas por azar); **ninguna significativa tras Holm**.
  - **Dirección:** acierto entre 47,9 % y 52,7 %. ARIMA, MLP y LSTM tienen p de Pesaran-Timmermann ≈ 0,02–0,03 sin corregir, pero **≈ 0,11 tras Holm**; además la prueba supone independencia entre filas y aquí hay correlación entre empresas del mismo día, así que esos p-valores son, si acaso, optimistas.
  - **Volatilidad (4 líquidas):** **solo EWMA queda en el MCS** al 10 % (GARCH p_MCS = 0,087; varianza constante 0,000). Por empresa, tras Holm, GARCH supera a la varianza constante en Banco de Bogotá y Ecopetrol y es peor que ella en Promigas; frente a EWMA ninguna diferencia es significativa.
- **Conclusión de la fase:** para el **rendimiento diario**, más complejidad (de 9 a ~25 000 parámetros contando las 5 semillas) no produce una mejora estadísticamente distinguible frente a la media o al cero. Para la **volatilidad**, el modelo más simple que se adapta (EWMA, sin parámetros estimados) es el mejor. Ambos resultados coinciden con la advertencia del borrador ("predicción ≠ inversión"; "la IA tiene que demostrar que mejora algo").
- **Implicaciones:** (1) Fase 11 (riesgo): usar EWMA como estimador principal de volatilidad para VaR/CVaR y GARCH como alternativa. (2) Fase 12 (optimización): la media histórica (o el cero) sigue siendo el estimador de rendimiento esperado justificado; Random Forest / Gradient Boosting pueden evaluarse como alternativa en el backtesting (Fase 14), donde lo que importa es el valor económico con costos, no el RMSE.
- **Alternativas consideradas:** comparar por filas sin promediar por fecha (rechazada: trata como independientes observaciones correlacionadas); no corregir por pruebas múltiples (rechazada: con 54 pruebas, ~3 falsos positivos esperados); MCS con estadístico de rango (se eligió T_max, más usado); evaluar valor económico aquí (aplazado a la Fase 14).
- **Evidencia utilizada:** `resultados/fase10_media.csv`, `fase10_media_por_empresa.csv`, `fase10_varianza_mcs.csv`, `fase10_varianza_por_empresa.csv`, `fase10_complejidad.csv`, `resultados/graficos/fase10_comparacion.png`; código en `src/comparacion/` (`estadistica.py`, `fase10.py`); 9 tests en `tests/test_comparacion_fase10.py` (Holm con valores conocidos, bootstrap reproducible, MCS excluye un modelo claramente peor e incluye equivalentes, R²_OS, Pesaran-Timmermann). Segunda ejecución: resultados idénticos.
- **Estado:** Pendiente de aprobación del equipo.

---

### DEC-028: Fase 11 — VaR y Expected Shortfall a un día con backtesting

- **Fecha:** 2026-10-04
- **Fase:** Fase 11 — Estimación del riesgo
- **Decisión (diseño):**
  - **Series:** las 4 acciones líquidas según entrenamiento y los 6 portafolios de la Fase 6 (1/N, mínima varianza y máximo Sharpe en los universos de 9 y de 4 empresas) con sus pesos fijos estimados en entrenamiento. Las 5 ilíquidas no se evalúan por separado (la Fase 7 mostró que sus modelos de volatilidad no son fiables); sí entran en los portafolios de 9 empresas.
  - **Medidas:** VaR y ES (CVaR) al 95 % y al 99 %, a un día, sobre rendimientos **simples** (pérdida = −R). Media condicional cero (la Fase 10 no encuentra un pronóstico de la media mejor que el cero).
  - **Métodos** (cada día con datos hasta el anterior): (1) simulación histórica con ventana móvil de 250 días; (2) normal con volatilidad EWMA, λ = 0,94; (3) GARCH(1,1)-t con parámetros estimados en entrenamiento; (4) simulación histórica filtrada (FHS): cuantiles de los residuos R/σ_EWMA de entrenamiento escalados por la σ_EWMA del día.
  - **Backtesting en validación (2024, ≈ 250 días):** Kupiec (cobertura incondicional), Christoffersen (independencia y cobertura condicional), semáforo de Basilea para el 99 %, prueba del ES (pérdida/ES en los días con exceso, unilateral, con al menos 3 excesos), pérdida cuantílica y MCS entre métodos (promediando las 10 series por fecha). Holm sobre las 80 pruebas de cobertura condicional y sobre las 53 pruebas de ES.
- **Resultados (hallazgos, no conclusiones definitivas):**
  - **Ninguna** de las 80 combinaciones serie × método × nivel se rechaza tras Holm (5 con p < 0,05 sin corregir, cerca de las 4 esperadas por azar). Ninguna prueba de ES es significativa tras Holm (3 de 53 sin corregir).
  - **Patrón por método al 99 %** (sumando las 10 series, 24,9 excesos esperados; la suma es descriptiva porque las series están correlacionadas):
    - Normal-EWMA: **39 excesos** y pérdida/ES media 1,25 → **subestima la cola** (colas normales demasiado delgadas). Es el único método con zonas amarillas de Basilea (Banco de Bogotá 6 y Ecopetrol 8 excesos).
    - GARCH-t: 12 excesos y pérdida/ES 0,88 → **conservador**: sobreestima el riesgo.
    - FHS: 21 excesos y pérdida/ES 0,93; histórica: 22 excesos y 1,17 → los más cercanos a la calibración nominal.
  - Al 95 % todos los métodos tienen menos excesos de los esperados (83–103 frente a 124): 2024 fue un año de baja volatilidad frente al entrenamiento (que incluye 2020).
  - **MCS de la pérdida cuantílica:** los 4 métodos quedan en el conjunto a ambos niveles (la simulación histórica tiene la menor pérdida media); con un año de datos la prueba no los distingue.
  - Portafolio de mínima varianza (4 líquidas), propuesto como benchmark: 2–3 excesos al 99 % con los 4 métodos (zona verde).
- **Recomendación para las Fases 12–14:** usar **FHS** (filtrado EWMA + residuos empíricos) como medida principal de VaR/ES: combina la adaptación de EWMA, que la Fase 10 identificó como el mejor pronóstico de volatilidad, con colas empíricas, y es el método mejor calibrado aquí. Mantener la simulación histórica como alternativa simple. No usar el VaR normal para el riesgo extremo.
- **Limitación de potencia:** con ≈ 250 días, al 99 % se esperan 2,5 excesos; las pruebas tienen poca potencia para distinguir métodos. La evaluación en la prueba (2025–2026, Fase 15) y el backtesting walk-forward (Fase 14) ampliarán la muestra.
- **Alternativas consideradas:** VaR con media del modelo (rechazada por la Fase 10); GARCH con errores normales (rechazada: colas pesadas); prueba de ES de Acerbi-Székely (aplazada: requiere simulación y la muestra de excesos es pequeña); horizonte de 10 días (aplazado: con 250 días hay muy pocas ventanas independientes).
- **Evidencia utilizada:** `resultados/fase11_backtesting.csv`, `fase11_mcs_metodos.csv`, `fase11_var_es_validacion.csv`, `resultados/graficos/fase11_var_validacion.png`; código en `src/riesgo/` (`medidas.py`, `backtesting.py`, `fase11.py`); 21 tests en `tests/test_riesgo_fase11.py` (VaR/ES sin información futura para los 4 métodos, ES ≥ VaR, cuantil y ES de la t contra simulación, Kupiec, Christoffersen, zonas de Basilea 0/4/5/9/10 excesos). Segunda ejecución: resultados idénticos.
- **Corrección posterior (DEC-031):** el CVaR empírico pasó a la definición robusta a empates (k peores observaciones); se reejecutó esta fase: cambian 8 de 80 combinaciones (histórica al 99 %: 19 excesos en lugar de 22) y ninguna conclusión.
- **Estado:** Pendiente de aprobación del equipo.

---

### DEC-029: Plan registrado ANTES de ejecutar — volatilidad semanal (y rendimiento semanal como robustez)

- **Fecha:** 2026-10-05 (registrado y commiteado antes de calcular cualquier resultado de este análisis)
- **Fase:** Extensión de las Fases 7–10 (pronóstico), previa a la Fase 12
- **Motivo:** Las Fases 7–10 muestran que el rendimiento diario no es predecible mejor que la media (DEC-027), pero que la volatilidad sí lo es (EWMA, DEC-023/DEC-027). El riesgo es lo que usa la optimización (Fase 12). Como el cambio de objetivo ocurre después de ver resultados, el plan se fija aquí antes de ejecutar, para evitar elegir el análisis según el resultado; el resultado nulo diario se mantiene y se reporta.
- **Datos y universo:** las 4 acciones líquidas según entrenamiento (Celsia, Banco de Bogotá, Ecopetrol, Davivienda PF), con las particiones congeladas (solo entrenamiento y validación). Semanas de calendario que terminan en viernes; una semana es válida si tiene al menos 3 días con rendimiento. Unas 208 semanas por acción en entrenamiento y 52 en validación.
- **Objetivo principal:** varianza realizada de la semana siguiente, RV_{w+1} = suma de los rendimientos log diarios al cuadrado (en %²) de la semana w+1, pronosticada al cierre de la semana w. Asignación a entrenamiento o validación por la fecha de la semana objetivo.
- **Modelos:**
  - Referencias: (a) EWMA diaria (λ = 0,94) × número de días de la semana objetivo; (b) GARCH(1,1)-t de la Fase 7, suma de los pronósticos a 1…n días; (c) **HAR** (Corsi, 2009) sobre log RV con componentes semanal (RV_w), mensual (media de 4 semanas) y diario (último r²), por MCO en entrenamiento. **HAR es la referencia principal.**
  - Retadores: Random Forest, Gradient Boosting (scikit-learn) y MLP (PyTorch) sobre log RV, con los componentes HAR más: rendimiento y |rendimiento| de la semana, proporción de días sin cambio, volumen relativo, RV promedio de las 4 acciones, |rendimiento| semanal de TRM y Brent (con fecha estrictamente anterior al cierre de la semana) e indicador de empresa. Modelo agrupado de las 4 acciones. **No se incluye LSTM** (≈ 830 observaciones semanales: muestra insuficiente).
  - Los modelos en log se devuelven a nivel con la corrección de *smearing* de Duan estimada con los residuos de entrenamiento.
  - Hiperparámetros: validación cruzada temporal por fechas dentro de entrenamiento (RF, GB, mismas rejillas de la Fase 8); MLP con el último 20 % de entrenamiento para parada temprana y 5 semillas (igual que la Fase 9).
- **Evaluación (validación 2024):** pérdida **QLIKE** (principal; robusta a un proxy ruidoso) y MSE sobre RV_{w+1}; pérdidas promediadas por semana entre las 4 acciones.
  - **Hipótesis principal H1:** al menos un retador (RF, GB, MLP) tiene menor QLIKE que HAR. Prueba: Diebold-Mariano de cada retador frente a HAR, **Holm sobre las 3 pruebas**, nivel 5 %. Se confirma H1 solo si algún p ajustado < 0,05 con estadístico negativo.
  - Secundarias: MCS al 10 % sobre los 6 modelos (QLIKE); HAR frente a EWMA y GARCH (Diebold-Mariano con Holm).
- **Análisis de robustez del resultado diario:** rendimiento semanal de la semana siguiente con RF y GB frente a la media de entrenamiento y el cero (RMSE, Diebold-Mariano, Holm). Expectativa declarada: poca potencia (≈ 52 semanas por acción); se reporta sea cual sea el resultado.
- **Lo que no se hará:** cambiar objetivo, universo, variables, pérdida o prueba después de ver los resultados de validación; abrir el bloque de prueba (eso es la Fase 15).
- **Estado:** Plan registrado; ejecutado sin cambios. Resultados en DEC-030.

---

### DEC-030: Resultados del plan DEC-029 — volatilidad y rendimiento semanales

- **Fecha:** 2026-10-05
- **Fase:** Extensión de las Fases 7–10, previa a la Fase 12
- **Ejecución:** se siguió el plan DEC-029 sin cambios de objetivo, universo, variables, pérdida ni prueba (commit del plan anterior al del código y los resultados). Detalles de implementación no especificados en el plan: HAR estimado **por empresa**; piso de 1e-4 %² antes de tomar logaritmos (una semana objetivo con RV = 0 en todo el periodo); smearing de RF/GB con residuos fuera de pliegue de la validación cruzada temporal y del MLP con el conjunto de parada; misma rejilla y lote del MLP que la Fase 9. Filas: 812 semanas-empresa en entrenamiento (16 descartadas por ventanas incompletas al inicio) y 208 en validación (52 semanas × 4).
- **Resultados (validación 2024):**
  - QLIKE medio (menor es mejor): MLP 3,531; EWMA 3,543; Gradient Boosting 3,556; Random Forest 3,566; GARCH 3,610; HAR 3,637.
  - **H1 (retador mejor que HAR): NO se confirma.** Los tres retadores tienen menor QLIKE que HAR, pero Diebold-Mariano da p = 0,19 (RF), 0,13 (GB) y 0,15 (MLP); **0,40 tras Holm**.
  - **MCS al 10 %: los 6 modelos quedan en el conjunto** (p_MCS ≥ 0,21). Con 52 semanas no se distinguen.
  - Secundarias: HAR peor que EWMA (DM = 2,14, p = 0,037 sin corregir; **0,074 tras Holm**, no significativa); HAR frente a GARCH, p = 0,56.
  - HAR: el componente mensual domina (β entre 0,27 y 0,55) y el diario no aporta (β ≈ 0 o negativo); factores de smearing 1,6–2,6, reflejo de lo ruidosa que es la RV semanal construida con 5 rendimientos diarios.
  - **Rendimiento semanal (robustez):** RF y GB no superan a la media ni al cero (p ≥ 0,17 sin corregir; ≥ 0,68 tras Holm). **El resultado nulo del rendimiento diario se mantiene a horizonte semanal.**
  - Reproducibilidad: segunda ejecución con pronósticos idénticos hasta 4e-14 (paralelismo del Random Forest).
- **Interpretación:** A horizonte semanal, los modelos de aprendizaje automático (en especial el MLP) quedan **numéricamente** por delante de las referencias econométricas, pero la diferencia no es estadísticamente significativa con un año de validación. EWMA, sin parámetros estimados, sigue entre los mejores, como en la Fase 10. El rendimiento sigue sin ser predecible.
- **Implicaciones:** (1) Para la optimización y el backtesting (Fases 12 y 14) se mantiene EWMA/FHS como estimador principal de riesgo; el MLP de volatilidad semanal puede incluirse como alternativa en el backtesting, donde se medirá su valor económico. (2) La evaluación en el bloque de prueba (Fase 15) duplicará la muestra (≈ 90 semanas); el plan de esa evaluación debe registrarse igual que DEC-029.
- **Evidencia utilizada:** `resultados/semanal_*.csv` (filas, volatilidad, pruebas, volatilidad por empresa, rendimiento, coeficientes HAR, validación cruzada, selección del MLP, hiperparámetros, pronósticos) y `resultados/graficos/semanal_volatilidad_validacion.png`; código en `src/volatilidad_semanal/` (`panel.py`, `ejecutar.py`); 6 tests en `tests/test_volatilidad_semanal.py` (RV semanal, objetivo = semana siguiente, semanas con < 3 días, variables sin información futura, separación por semana objetivo, HAR y smearing).
- **Estado:** Pendiente de aprobación del equipo.

---

### DEC-031: Fases 12–13 — Optimización con restricciones, tasa libre de riesgo (IBR) y corrección del CVaR empírico

- **Fecha:** 2026-10-05
- **Fase:** Fase 12 (optimización) y Fase 13 (restricciones realistas)
- **Tasa libre de riesgo (resuelve DEC-020 b):** IBR overnight **nominal** del Banco de la República (Portal de Estadísticas Económicas), descargado manualmente por el equipo el 2026-10-05 y guardado sin modificar (`datos/crudos/externos/Tasas de interés.csv`; metadatos y SHA-256 en `datos/metadata/externos/IBR.json`). Se recorta a la muestra, se agrega a la partición congelada (`tasas_*`, con huellas; las existentes no cambian) y se convierte a efectiva anual con (1 + r/360)^365 − 1. Media efectiva: **6,23 % en entrenamiento** y **11,39 % en validación**.
- **Restricciones (Fase 13):** suma 1, sin cortos, máximo 30 % por acción y, en la variante con sectores, **máximo 40 % por sector**. Sectores: financiero (Banco de Bogotá, Davivienda PF, Grupo Bolívar), petróleo y gas (Ecopetrol), servicios públicos (Celsia, Promigas), telecomunicaciones (ETB), consumo (Nutresa), minería (Mineros).
- **Insumos (solo entrenamiento, rendimientos simples, filas completas):** media histórica (la Fase 10 no encontró pronóstico mejor); covarianza muestral y **Ledoit-Wolf** (encogimiento 0,26 con 9 empresas y 0,10 con 4); escenarios diarios para el CVaR.
- **Portafolios:** 1/N; mínima varianza (muestral y Ledoit-Wolf); **mínimo CVaR 95 %** (programa lineal de Rockafellar-Uryasev con HiGHS); **paridad de riesgo** (Ledoit-Wolf); máximo Sharpe (Ledoit-Wolf, IBR de entrenamiento); **máximo retorno con volatilidad ≤ la del 1/N**. Universos de 9 y de 4 empresas; variantes sin y con límite sectorial. Pesos fijos evaluados en entrenamiento y validación (el rebalanceo es la Fase 14).
- **Resultados (validación 2024; hallazgos, no conclusiones):**
  - **9 empresas:** el límite sectorial **no es activo** (el financiero queda entre 19 % y 35 %). Los portafolios basados en riesgo superan al 1/N en Sharpe: mínima varianza muestral 1,89, máximo retorno con volatilidad acotada 1,89, mínimo CVaR 1,85, mínima varianza Ledoit-Wolf 1,69, paridad de riesgo 1,37, 1/N 1,21. **El máximo Sharpe es el peor (0,85)**, consistente con el error de estimación de la media (DEC-020).
  - **4 líquidas:** **ningún portafolio supera al IBR en 2024** (Sharpe entre −0,44 y −0,22): el rendimiento de las líquidas (≈ 5–8 %) quedó por debajo de la tasa libre de riesgo (11,4 %). Con el límite sectorial, el conjunto factible casi se reduce a una recta (Celsia y Ecopetrol forzadas al 30 %, financiero al 40 %) y todos los portafolios son prácticamente iguales.
  - **Máximo Sharpe degenerado** en el universo líquido: en entrenamiento ningún portafolio supera al IBR (mejor Sharpe −0,30); se reporta con aviso (`fase12_avisos.csv`) y no debe usarse como benchmark.
  - Validaciones internas: el mínimo CVaR tiene el menor CVaR de entrenamiento de su universo; el 1/N infactible con el límite sectorial (4 líquidas) se sustituye por el factible más cercano, con aviso.
- **Corrección metodológica (afecta a DEC-028):** el CVaR empírico se calculaba con "rendimientos ≤ cuantil". Como los precios de la BVC se mueven en saltos discretos, hay **empates** en el cuantil y el tamaño de la cola cambiaba con perturbaciones de 1e-15 (53 frente a 56 observaciones, CVaR 0,0263 frente a 0,0257 con pesos idénticos). Se adopta la definición robusta: **VaR = −x_(k) y ES = −media de las k = ⌈α·n⌉ peores observaciones** (`src/riesgo/medidas.py: cola_empirica`), usada ahora en la simulación histórica, FHS y la Fase 12. Al reejecutar la Fase 11 cambian 8 de 80 combinaciones (sobre todo el método histórico: 22 → 19 excesos al 99 %); **ninguna conclusión de DEC-028 cambia** (sin rechazos tras Holm; FHS sigue siendo el mejor calibrado con 21 excesos y pérdida/ES 0,93; los 4 métodos siguen en el MCS).
- **Otra corrección durante la implementación:** la paridad de riesgo no convergía en el universo líquido con sectores por un factor de escala (×10⁴) en la función objetivo; sin él converge y coincide con una búsqueda exhaustiva del único grado de libertad (Banco de Bogotá = 21,24 %).
- **Implicaciones para la Fase 14 (backtesting):** comparar con rebalanceo periódico y costos de transacción al menos 1/N, mínima varianza (muestral y Ledoit-Wolf), mínimo CVaR y paridad de riesgo; excluir el máximo Sharpe como candidato principal. Evaluar también el universo líquido, donde el benchmark relevante es el IBR.
- **Alternativas consideradas:** tasa libre de riesgo 0 (rechazada para el congreso); TES (aplazada: el IBR overnight es el estándar de corto plazo y está completo en la muestra); límite sectorial en el universo líquido como restricción principal (se reporta, pero casi fija la solución); Black-Litterman (aplazado: requiere vistas y la Fase 10 no da pronósticos de rendimiento con señal).
- **Evidencia utilizada:** `resultados/fase12_pesos.csv`, `fase12_metricas.csv`, `fase12_insumos.csv`, `fase12_avisos.csv`, `resultados/graficos/fase12_pesos.png`; código en `src/optimizacion/` (`optimizadores.py`, `fase12.py`) y `src/data/externos.py` (`cargar_ibr`, `ibr_efectiva_anual`); 9 tests nuevos en `tests/test_optimizacion_fase12.py` (fórmula cerrada de mínima varianza, límite sectorial activo, infactibilidad, paridad de riesgo = inversa de la volatilidad con covarianza diagonal, mínimo CVaR frente a búsqueda exhaustiva, volatilidad acotada, máximo Sharpe, IBR) y 1 en `tests/test_riesgo_fase11.py` (CVaR robusto a empates). Ejecución determinista: dos corridas idénticas.
- **Estado:** Pendiente de aprobación del equipo.

---

*Las decisiones siguientes se registrarán conforme avance el proyecto.*
