# Buenas prácticas para agentes de IA en este proyecto

> **Documento explicativo.** El archivo operativo principal es [`AGENTS.md`](../AGENTS.md),
> que contiene la versión obligatoria y condensada. Este documento amplía las
> reglas, da contexto y ejemplos, y distingue lo obligatorio de lo recomendado.

El objetivo es que cualquier agente de IA (o persona) que trabaje en el proyecto
produzca código **claro, modular, reproducible y metodológicamente sólido**,
respetando en todo momento la integridad de los datos y el rigor estadístico.

---

## 1. Reglas obligatorias (aplican siempre)

Estas reglas **no son negociables**. Si una tarea entra en conflicto con ellas,
el agente debe detenerse y pedir instrucciones.

| # | Regla |
|---|---|
| 1 | No guardar secretos, API keys, contraseñas ni tokens en el código. |
| 2 | `datos/crudos/` es inmutable: nunca modificarlo automáticamente. |
| 3 | Toda transformación genera archivos nuevos; nunca sobrescribe los crudos. |
| 4 | Nunca inventar, ocultar ni rellenar valores sin documentarlo. |
| 5 | Nunca eliminar una observación sin documentar la decisión. |
| 6 | Respetar el orden cronológico de las series temporales. |
| 7 | Evitar data leakage (no usar información futura). |
| 8 | Ningún agente declara una tarea terminada sin ejecutar código y pruebas. |
| 9 | Toda decisión metodológica se registra en `informes/diario_decisiones.md`. |
| 10 | No usar `assert` como sustituto de validación de producción. |

### 1.1 Entornos y reproducibilidad

- Entornos virtuales siempre que sea posible (`venv`, `conda`, etc.).
- Versiones **exactas** en `requirements.txt` (por ejemplo `pandas==3.0.5`).
- `.gitignore` debe cubrir: `.env`, `.venv/`, `venv/`, `__pycache__/`,
  `.pytest_cache/`, checkpoints de notebooks y artefactos temporales.
- Si se crean variables de entorno, documentarlas en `.env.example` (sin secretos).

### 1.2 Manejo de excepciones

- No ocultar excepciones con `except: pass` silencioso.
- Diferenciar **errores de datos** (no se pudieron descargar, valores inválidos)
  de **errores de programación** (bug en el código).
- Un error inesperado debe ser **visible** (logging, no `print` suelto) y con
  información suficiente para diagnosticarlo.
- Si se crea un decorador propio, usar `@wraps`:
  ```python
  from functools import wraps

  def mi_decorador(fn):
      @wraps(fn)
      def wrapper(*args, **kwargs):
          return fn(*args, **kwargs)
      return wrapper
  ```

---

## 2. Recomendaciones (calidad de código)

- **Responsabilidad única:** un módulo hace una sola cosa. En este proyecto:
  `data/` adquiere y valida; `preprocessing/` transforma e imputa;
  `exploratory_analysis/` analiza. Evitar módulos monolíticos.
- Preferir **composición** sobre herencia compleja.
- No usar estado mutable global innecesario.
- Los módulos tienen `__init__.py` y docstrings en español que explican *qué*
  hace el módulo y *por qué*.
- Parámetros y rutas se centralizan en `config/` (fuente única), no se repiten
  en varios módulos.

### 2.1 Validación

- Validar entradas y salidas de funciones críticas: tipos, dimensiones, fechas,
  columnas, valores faltantes e inválidos.
- `assert` sirve para tests, no para validar datos en producción.

---

## 3. Reglas específicas de datos

Esta es la parte más delicada del proyecto.

### 3.1 Datos crudos vs. procesados

```
datos/crudos/      -> datos originales descargados (Yahoo Finance). Inmutables.
datos/procesados/  -> datos limpios, imputados y transformados. Archivos nuevos.
datos/metadata/    -> metadatos de la descarga (JSON): fuente, fechas, estado, etc.
```

### 3.2 Trazabilidad

Toda transformación debe poder rastrearse en la cadena:

```
dato crudo → validación → transformación → dato procesado → resultado
```

En la práctica:

- Cada paso se registra (metadatos, reportes CSV/JSON en `resultados/`).
- Toda imputación queda **marcada con una bandera** (p. ej. `es_imputado_kalman`)
  y registrada en un reporte que indica valor original, valor imputado y método.
- Nunca se elimina una observación sin documentar el motivo y la evidencia.

### 3.3 Valores extremos y faltantes

- Los outliers se **identifican** (z-score, percentiles) y se documentan; **no**
  se eliminan automáticamente.
- Los valores faltantes se **documentan**; su imputación queda trazada.

---

## 4. Reglas específicas de series temporales

- **Orden cronológico:** los datos deben estar ordenados por fecha.
- **Sin `train_test_split` aleatorio:** en series de tiempo la división es temporal
  (por ejemplo, los primeros 70% para entrenar, etc.).
- **Data leakage:** está prohibido usar información del futuro para construir una
  variable histórica o evaluar un modelo "prediciendo" el pasado.
- **Documentar toda transformación** que involucre fechas (rezagos, diferencias,
  medias móviles, imputación).
- Distinguir explícitamente:
  - **Análisis retrospectivo:** se puede usar información posterior (p. ej. el
    suavizado de Kalman para reconstruir un faltante histórico).
  - **Predicción en tiempo real:** solo se puede usar información disponible en
    ese momento.
- **Correlación no es causalidad.**

### 4.1 Caso concreto: imputación retrospectiva con Kalman

El suavizado de Kalman reconstruye valores faltantes usando información **antes y
después** del faltante. Por eso:

> La imputación mediante suavizado de Kalman utiliza información posterior al
> valor faltante y, por tanto, **no** puede usarse directamente como procedimiento
> de información disponible en tiempo real para backtesting o predicción sin
> adaptar el procedimiento.

---

## 5. Reglas futuras: Machine Learning

Cuando se implementen modelos en fases posteriores:

- `train / validation / test` deben respetar el orden temporal.
- No ajustar transformaciones (escaladores, imputadores, PCA) con datos futuros.
- Documentar hiperparámetros y **registrar semillas** para reproducibilidad.
- Comparar cualquier modelo complejo contra **benchmarks simples** (naïve,
  random walk, mean) antes de afirmar que es mejor.
- No afirmar superioridad sin evidencia estandarizada.

---

## 6. Reglas futuras: API y agente

Cuando se construya una API (todavía **no**):

- Contratos explícitos, códigos HTTP correctos y respuestas en JSON.
- Validación explícita de entradas.
- Endpoint `/health`.
- Separar desarrollo de producción.
- Recursos costosos (modelos cargados, conexiones) inicializados una sola vez.
- Clasificar operaciones IO-bound vs CPU-bound.
- **No** usar `pickle` como formato de intercambio externo.

---

## 7. Flujo de trabajo recomendado para un agente

1. **Leer** `README.md`, `docs/metodos.md`, `informes/diario_decisiones.md` y la
   documentación de la fase actual.
2. **Inspeccionar** la estructura y los módulos existentes antes de escribir código.
3. **Implementar** respetando la responsabilidad única y la configuración central.
4. **Ejecutar** el código y los tests (`python -m pytest tests -v`).
5. **Inspeccionar** los archivos y resultados generados.
6. **Verificar** métricas y evidencias.
7. **Reportar** evidencia reproducible, no afirmaciones sin respaldo.
8. **Registrar** las decisiones en `informes/diario_decisiones.md`.

---

*Este documento es una guía explicativa. Ante cualquier conflicto, prevalece
[`AGENTS.md`](../AGENTS.md).*