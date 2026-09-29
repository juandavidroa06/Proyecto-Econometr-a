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
- **Estado:** **Pendiente de decisión.** No se elimina ni modifica ningún dato. Se retoma antes de iniciar la Fase 7 (Econometría), al cerrar el criterio final de inclusión de empresas. Requiere revisión del equipo.

---

*Las decisiones siguientes se registrarán conforme avance el proyecto.*
