# Glosario del Proyecto

> **Propósito:** Definir de manera clara los conceptos técnicos que aparecen
> a lo largo del proyecto. Las definiciones están pensadas para estudiantes
> de Estadística que están aprendiendo algunos de estos conceptos por primera vez.

---

## Conceptos de finanzas

### Rendimiento
Cambios en el valor de un activo financiero a lo largo del tiempo. Se calcula como la diferencia entre el precio actual y el precio anterior, generalmente expresado como porcentaje.

### Rendimiento logarítmico
Rendimiento calculado usando el logaritmo natural de la razón entre precios consecutivos. Es preferido en análisis financiero porque:
- Es simétrico (subidas y bajadas se tratan de forma equivalente).
- Los rendimientos logarítmicos aditivos se approximan mejor a distribuciones normales.
- Facilita el trabajo con series de tiempo.

**Fórmula:** r_t = ln(P_t / P_{t-1})

### Precio ajustado (Adj Close)
Precio de cierre corregido por eventos corporativos como dividendos y desdoblamientos (splits) de acciones. Es la serie que se usa para calcular rendimientos, porque refleja el valor real que recibe el inversionista a lo largo del tiempo. En nuestro proyecto los rendimientos se calculan sobre este precio.

### Volatilidad
Mide la dispersión de los rendimientos de un activo. Es el desviación estándar de los rendimientos y se utiliza como proxy del riesgo. Mayor volatilidad implica mayor incertidumbre sobre el rendimiento futuro.

### Volatilidad anualizada
Volatilidad expresada a escala anual. A partir de la diaria se calcula como σ_anual = σ_diaria · √252, donde 252 es una aproximación convencional (no universal) al número de días bursátiles por año. El factor √252 proviene del supuesto de que los rendimientos diarios son independientes.

### Covarianza
Mide cómo se mueven dos activos respecto a su media. Si la covarianza es positiva, tienden a moverse en la misma dirección. Si es negativa, se mueven en direcciones opuestas. Es la base de la diversificación de portafolios.

### Correlación
Versión normalizada de la covarianza (entre -1 y 1). Indica la fuerza y dirección de la relación lineal entre dos activos. Una correlación de 0 indica que no hay relación lineal.

---

## Conceptos de econometría

### Estacionariedad
Una serie temporal es estacionaria cuando sus propiedades estadísticas (media, varianza, covarianza) no cambian con el tiempo. Es un requisito fundamental para muchos modelos econométricos. Si una serie no es estacionaria, se puede diferenciar para lograr estacionariedad.

### ARIMA (Autoregressive Integrated Moving Average)
Modelo para series temporales que combina:
- **AR (Autoregresivo):** El valor actual depende de valores pasados.
- **I (Integrado):** Número de diferencias necesarias para lograr estacionariedad.
- **MA (Media Móvil):** El valor actual depende de errores pasados.

El formato ARIMA(p, d, q) indica el orden de cada componente.

### GARCH (Generalized Autoregressive Conditional Heteroskedasticity)
Modelo que captura la volatilidad variable en el tiempo. Es útil en finanzas porque la volatilidad de los mercados tiende a agruparse (períodos de alta volatilidad seguidos de períodos de baja volatilidad, y viceversa).

### VAR (Vector Autoregression)
Extensión del modelo AR para múltiples series temporales. Permite modelar las relaciones dinámicas entre varias variables simultáneamente.

---

## Machine Learning

### Machine Learning (Aprendizaje automático)
Conjunto de técnicas que permiten a las computadoras aprender patrones a partir de datos sin ser programadas explícitamente. En nuestro proyecto, se usa para predecir rendimientos o clasificar señales de compra/venta.

### Red neuronal artificial
Modelo computacional inspirado en la estructura del cerebro humano. Consiste en capas de neuronas artificiales que procesan información. No asumimos que sea superior a otros métodos; su inclusión es exploratoria.

### LSTM (Long Short-Term Memory)
Tipo especial de red neuronal diseñada para trabajar con secuencias de datos, como series de tiempo. A diferencia de las redes tradicionales, LSTM puede "recordar" información de pasos anteriores, lo cual es útil para capturar dependencias temporales de largo plazo.

---

## Riesgo y métricas

### VaR (Value at Risk)
Estimación de la pérdida máxima esperada en un período determinado, con un nivel de confianza dado. Por ejemplo, un VaR del 5% de $10 millones significa que hay un 5% de probabilidad de perder más de $10 millones.

### CVaR (Conditional Value at Risk)
También conocido como Expected Shortfall. Es el promedio de las pérdidas que exceden el VaR. Proporciona una medida del riesgo en el peor de los escenarios, siendo más conservador que el VaR.

### Sharpe Ratio
Mide el exceso de rendimiento por unidad de riesgo tomado. Un Sharpe Ratio más alto indica mejor relación riesgo-rentabilidad.

**Fórmula:** Sharpe = (Rendimiento del portafolio - Tasa libre de riesgo) / Volatilidad del portafolio

---

## Metodología

### Backtesting
Proceso de evaluar una estrategia de inversión utilizando datos históricos. Simula qué habría pasado si se hubiera aplicado la estrategia en el pasado. Es fundamental para validar modelos antes de aplicarlos con dinero real.

### Data leakage (Fuga de datos)
Error que ocurre cuando el modelo utiliza información que no estaría disponible en el momento de la predicción. Por ejemplo, usar el precio de cierre de mañana para predecir el precio de hoy. Evitar el data leakage es uno de los principios más importantes del proyecto.

### Train / Validation / Test (Entrenamiento / Validación / Prueba)
Separación de los datos en tres conjuntos:
- **Train (Entrenamiento):** Para ajustar el modelo.
- **Validation (Validación):** Para seleccionar hiperparámetros y comparar modelos.
- **Test (Prueba):** Para evaluar el desempeño final, solo se usa una vez.

En series de tiempo, esta separación respeta el orden temporal (no se mezclan datos pasados con futuros).

---

*Este glosario se actualizará a medida que aparezcan nuevos conceptos en el proyecto.*
