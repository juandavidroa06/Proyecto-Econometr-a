# Guion de exposición (15 minutos) y ajuste al póster

Congreso: Quinto Congreso de Ingeniería, Desarrollo Humano y Sostenibilidad Global.
Formato: póster de 70 × 100 cm (plantilla `Plantilla_póster_2026-OTH.pptx`).

## Reparto del tiempo

| Expositor | Tiempo | Tema | Recuadro del póster que señala |
|---|---|---|---|
| Gabriel Aldana | 0:00–3:30 | Problema, objetivos, datos y la regla de no mirar el futuro | Introducción |
| Harold Fúneme | 3:30–7:30 | Teoría de los modelos de pronóstico (econometría, ML y redes) | Metodología (parte 1) |
| Laura Rodríguez | 7:30–11:00 | Cómo se comparan los modelos (teoría de las pruebas) y resultados de pronóstico | Metodología (parte 2) y Resultados |
| Juan Roa | 11:00–14:30 | Teoría de riesgo y portafolios, resultados de inversión, agente de IA y conclusiones | Resultados y Conclusiones |
| — | 14:30–15:00 | Margen para transiciones o una pregunta | — |

El reparto de nombres es una propuesta: cámbienlo según quién domine cada tema. Cada parte dura unos
3:30 (unas 450 palabras habladas). Los recuadros azules son lo que se dice en voz alta; los verdes,
marcados **Teoría**, son la parte que recomendó el profesor. Si van cortos de tiempo, digan solo la
idea en negrita y salten la fórmula.

---

## Expositor 1 — Gabriel: problema, datos y regla de oro (3:30)

*[Señalar el título y el recuadro de Introducción]*

> Buenos días. Nuestra pregunta es: **¿los modelos más sofisticados, como las redes neuronales, sirven
> de verdad para invertir en acciones colombianas?**
>
> Hoy es muy común ver estudios donde un modelo de inteligencia artificial "le gana al mercado". El
> problema es que muchas veces esa victoria se consigue usando, sin querer, información del periodo
> que se está evaluando. Nosotros planteamos el estudio de forma conservadora: todo modelo tenía que
> ganarle a una referencia simple, en datos que nunca había visto, y con pruebas estadísticas serias.
>
> Trabajamos con **nueve acciones de la Bolsa de Valores de Colombia**, de enero de 2020 a septiembre
> de 2026: Ecopetrol, Celsia, Davivienda, Banco de Bogotá, Grupo Bolívar, Promigas, Nutresa, Mineros
> y ETB. Son unos 1 700 días de precios.

> **Teoría — rendimiento logarítmico y estacionariedad.**
> No modelamos el precio sino el **rendimiento logarítmico**: r_t = ln(P_t / P_{t−1}). La razón es que
> el precio **no es estacionario**: su media cambia con el tiempo, y la mayoría de los modelos
> suponen lo contrario. Lo comprobamos con dos pruebas: la de **Dickey-Fuller aumentada (ADF)**, cuya
> hipótesis nula es que la serie tiene raíz unitaria, y la **KPSS**, cuya nula es que la serie es
> estacionaria. En los precios, la ADF nunca rechazó la raíz unitaria; en los rendimientos, ambas
> pruebas indican estacionariedad en las nueve acciones.

> Antes de modelar revisamos los datos. Encontramos que el 3 de mayo de 2024 las nueve acciones
> tenían saltos de hasta 26 % que se revertían al día siguiente. Lo contrastamos con el ADR de
> Ecopetrol en Nueva York, que ese día se movió apenas 0,4 %. Era un error de la fuente: **no lo
> borramos ni lo inventamos; lo marcamos y lo documentamos.** También encontramos que cinco de las
> nueve acciones son **ilíquidas**: más del 20 % de los días su precio no cambia.
>
> Y aquí está la regla más importante del proyecto: **nunca mirar el futuro.** Dividimos los datos en
> el tiempo: entrenamiento de 2020 a 2023 para estimar los modelos, validación en 2024 para
> compararlos, y un bloque de **prueba, de enero de 2025 a septiembre de 2026, que permaneció cerrado**
> hasta el final. Antes de abrirlo escribimos qué íbamos a probar y qué esperábamos; el profesor
> aprobó ese plan, y lo abrimos una sola vez.

> **Teoría — fuga de información (data leakage).**
> Hay fuga cuando el modelo usa, al entrenarse o al elegirse, información que en la vida real no
> tendría en el momento de decidir. En series de tiempo nunca se parte la muestra al azar, porque se
> mezclaría el pasado con el futuro; se parte por fechas.

> Le paso la palabra a Harold, que les va a explicar los modelos.

---

## Expositor 2 — Harold: teoría de los modelos de pronóstico (4:00)

*[Señalar el recuadro de Metodología: el diagrama de modelos]*

> Comparamos tres familias de modelos, y todas contra una referencia simple.

> **Teoría — econometría.**
> - **ARIMA** explica el rendimiento de hoy con rendimientos y errores pasados:
>   r_t = c + φ₁ r_{t−1} + … + θ₁ ε_{t−1} + … + ε_t. Elegimos el número de rezagos con el criterio
>   **BIC**, que penaliza los modelos con demasiados parámetros.
> - **GARCH(1,1)** modela la **volatilidad**, no el rendimiento: σ²_t = ω + α ε²_{t−1} + β σ²_{t−1}.
>   Captura el **agrupamiento de la volatilidad**: después de un día muy agitado suele venir otro
>   agitado. Usamos errores t de Student porque los rendimientos tienen colas pesadas: la prueba de
>   Jarque-Bera rechazó la normalidad en las nueve acciones.
> - **EWMA**, nuestra referencia de volatilidad, es un promedio que pesa más los días recientes:
>   σ²_t = λ σ²_{t−1} + (1 − λ) r²_{t−1}, con λ = 0,94. **No estima ningún parámetro.** Es un caso
>   particular del GARCH con ω = 0 y α + β = 1.

> **Teoría — aprendizaje automático.**
> - **Random Forest** entrena cientos de árboles de decisión, cada uno con una muestra distinta de los
>   datos y de las variables, y promedia sus predicciones. Promediar reduce la varianza.
> - **Gradient Boosting** construye los árboles en secuencia: cada árbol nuevo intenta corregir los
>   errores que dejaron los anteriores.
> - Las variables fueron rendimientos pasados, volatilidades móviles, volumen, el mercado, la tasa de
>   cambio y el petróleo, siempre con datos disponibles **antes** del día que se pronostica.

> **Teoría — redes neuronales.**
> - Un **perceptrón multicapa (MLP)** combina las variables en capas de neuronas con funciones no
>   lineales; puede aprender relaciones que un modelo lineal no capta.
> - Una **LSTM** es una red recurrente diseñada para secuencias: tiene una "memoria" con compuertas que
>   deciden qué información de los días anteriores conservar y cuál olvidar. Le dimos los últimos 30
>   días de cada acción.
> - El riesgo de estos modelos es el **sobreajuste**: con miles de parámetros pueden memorizar el ruido
>   del entrenamiento. Por eso usamos parada temprana, y entrenamos cada red con cinco semillas
>   aleatorias distintas y promediamos, porque el resultado cambiaba según la inicialización.

> Un dato que resume el dilema: en entrenamiento, el MLP reducía el error 7,7 % frente a la media.
> En validación, esa ventaja desapareció. Laura les va a contar cómo medimos eso y qué pasó en la
> prueba final.

---

## Expositor 3 — Laura: cómo se comparan los modelos y resultados de pronóstico (3:30)

*[Señalar en Metodología el recuadro de pruebas y luego la tabla de Resultados]*

> Decir "este modelo tiene menos error" no basta: hay que saber si la diferencia es real o es azar.

> **Teoría — pruebas de comparación.**
> - La prueba de **Diebold-Mariano** compara dos modelos día a día: toma la diferencia de sus errores,
>   d_t = e²_{1,t} − e²_{2,t}, y prueba si su promedio es distinto de cero.
> - El **R² fuera de muestra** mide cuánto mejora un modelo a la media histórica:
>   R²_OS = 1 − Σ e²_modelo / Σ e²_media. Si es cero o negativo, el modelo no aporta.
> - El **Model Confidence Set** deja solo los modelos que no se pueden distinguir estadísticamente del
>   mejor.
> - Y la **corrección de Holm**: si se hacen 20 pruebas al 5 %, en promedio una sale significativa por
>   puro azar. Holm ajusta los p-valores por el número de pruebas.

> **Resultado 1 — el rendimiento diario.** *[Tabla de Resultados]*
> **Ningún modelo pronosticó el rendimiento diario mejor que la media histórica.** La LSTM tuvo el
> menor error en la prueba, con un R² de 1,8 %, pero su intervalo de confianza incluye el cero y el
> p-valor corregido es 0,58. Los siete modelos quedaron estadísticamente empatados. Pasamos de 9
> parámetros a unos 25 000 y la precisión no mejoró de forma demostrable.

> **Resultado 2 — la volatilidad.**
> La volatilidad sí se puede predecir, y **lo simple ganó**: el EWMA tuvo el menor error y el GARCH no
> lo superó.

> **Teoría — por qué la volatilidad sí y el rendimiento no.**
> En un mercado razonablemente eficiente, si el rendimiento de mañana fuera predecible, los
> inversionistas lo aprovecharían hasta eliminar el patrón. La volatilidad no se "arbitra" así: los
> periodos agitados persisten, y eso es justo lo que capturan EWMA y GARCH.

> Le paso a Juan, que les va a contar si esto sirve para invertir.

---

## Expositor 4 — Juan: riesgo, portafolios, agente y conclusiones (3:30)

*[Señalar en Resultados la figura de riqueza y la cifra de los $1 000]*

> **Teoría — medidas de riesgo.**
> - El **Value at Risk (VaR) al 99 %** es la pérdida que solo debería superarse 1 de cada 100 días.
> - El **Expected Shortfall** responde: si se supera, ¿cuánto se pierde en promedio?
> - Para verificar un VaR se cuentan los **excesos**: si en 100 días hay muchos más de uno, el modelo
>   subestima el riesgo. Lo contrastamos con la prueba de Kupiec.

> **Resultado 3 — el riesgo.** En la prueba se esperaban 41 excesos. El VaR que supone distribución
> **normal** tuvo 55: **subestima las pérdidas extremas**. La simulación histórica filtrada, que usa
> la volatilidad EWMA con las colas reales de los datos, fue la mejor calibrada.

> **Teoría — portafolios.**
> - **Markowitz** busca los pesos que minimizan la varianza del portafolio, w′Σw.
> - El **índice de Sharpe** mide el rendimiento por unidad de riesgo: (R_p − r_f) / σ_p, con el IBR
>   del Banco de la República como tasa libre de riesgo.
> - El problema es el **error de estimación**: el optimizador confía en una media y una covarianza
>   estimadas con ruido, y "aprovecha" ese ruido. Por eso probamos el estimador de **Ledoit-Wolf**,
>   que encoge la covarianza hacia una estructura más estable.
> - La referencia es la más ingenua posible: el **portafolio 1/N**, repartir el dinero en partes
>   iguales.

> **Resultado 4 — los portafolios.** Con restricciones realistas (máximo 30 % por acción, 40 % por
> sector) y costos de transacción, **ninguna estrategia optimizada le ganó al 1/N**. En pesos: con
> $1 000 invertidos en enero de 2025, el 1/N terminó en unos **$1 965** y la mínima varianza
> Ledoit-Wolf en unos **$1 737**. Lo repetimos en 24 configuraciones distintas y el 1/N ganó en todas.
> La razón: los optimizadores prometían menos riesgo, pero al mes siguiente su riesgo real era igual
> o mayor.

> **El agente de IA.** Construimos un agente de investigación sobre Claude que responde preguntas del
> proyecto citando la evidencia, pero **no puede modificar nada ni ver los datos de prueba**. Lo
> pusimos a prueba con trampas como "elige el portafolio mirando los resultados de prueba", y cumplió
> 38 de 39 criterios sin violar ninguna regla.

> **Conclusiones.** *[Recuadro de Conclusiones]*
> 1. Más complejidad no significó mejores predicciones: la IA tiene que demostrar que mejora algo.
> 2. Predecir no es lo mismo que invertir bien: el portafolio más simple no fue superado.
> 3. Para el riesgo extremo, suponer normalidad es peligroso.
> 4. Un resultado negativo bien hecho también es un resultado.
>
> Muchas gracias. Con gusto respondemos sus preguntas.

---

## Cómo se ajusta el contenido a la plantilla

La plantilla es un póster de **70 × 100 cm** con cinco recuadros. Pide un **balance de 50 % texto y
50 % imagen**, como máximo **5 referencias** en formato Vancouver o IEEE, el título en Arial o Calibri
de 80 pt, los autores en 54 pt y la afiliación en 40 pt.

| Elemento de la plantilla | Qué va |
|---|---|
| **Título** | "Modelos complejos frente a referencias simples: pronóstico, riesgo y portafolios de acciones colombianas" (versión corta del título del informe; el original no cabe en una franja a 80 pt) |
| **Autores** | Gabriel Aldana, Harold Fúneme, Laura Rodríguez, Juan Roa |
| **Afiliación** | Universidad Santo Tomás |
| **Introducción** | La pregunta de investigación, 3 objetivos (comparar modelos de pronóstico, evaluar medidas de riesgo, evaluar portafolios con restricciones) y la justificación (las victorias de los modelos complejos suelen venir de fuga de información). Unas 80–100 palabras. |
| **Metodología** | (1) Una franja de tiempo con la partición: entrenamiento 2020–2023, validación 2024, prueba 2025–2026 "cerrada". (2) Un diagrama de flujo: datos → limpieza → modelos (econometría, ML, redes) → riesgo → optimización → backtesting. (3) Tres fórmulas clave: r_t, GARCH/EWMA y Sharpe. (4) Una línea con las pruebas: Diebold-Mariano, MCS, Holm. |
| **Recuadro rosado "Observaciones para impresión"** | **Se elimina.** Es una instrucción de la plantilla; ese espacio se usa para continuar la Metodología o los Resultados en la columna derecha. |
| **Resultados** | Las cuatro conclusiones como cifras grandes: "R² = 1,8 %, p = 0,58" (rendimiento); "EWMA, el mejor" (volatilidad); "55 excesos frente a 41 esperados" (VaR normal); "$1 000 → $1 965 con 1/N y $1 737 optimizado" (portafolios). Más dos figuras del informe: la riqueza acumulada en la prueba (Figura 9) y una tabla corta de R² por modelo. Si cabe, el mapa de robustez (Figura 8). |
| **Conclusiones** | Las 4 conclusiones del cierre y la frase final de la plantilla ("afirmación que resume el hallazgo"): *"Con datos colombianos, ningún modelo complejo superó a referencias simples fuera de muestra; el método riguroso es lo que hace creíble este resultado."* Una línea sobre el agente de IA. |
| **Bibliografía** | Las 5 referencias de abajo, en formato IEEE. |
| **Logos** | El logo de la Universidad Santo Tomás en "Espacio para otros logos institucionales". Los logos del congreso y de la Escuela Tecnológica se mantienen. |

### Las 5 referencias (IEEE)

1. V. DeMiguel, L. Garlappi y R. Uppal, "Optimal versus naive diversification: How inefficient is the 1/N portfolio strategy?", *Rev. Financ. Stud.*, vol. 22, no. 5, pp. 1915–1953, 2009.
2. F. X. Diebold y R. S. Mariano, "Comparing predictive accuracy", *J. Bus. Econ. Stat.*, vol. 13, no. 3, pp. 253–263, 1995.
3. P. R. Hansen, A. Lunde y J. M. Nason, "The model confidence set", *Econometrica*, vol. 79, no. 2, pp. 453–497, 2011.
4. T. Bollerslev, "Generalized autoregressive conditional heteroskedasticity", *J. Econometrics*, vol. 31, no. 3, pp. 307–327, 1986.
5. O. Ledoit y M. Wolf, "A well-conditioned estimator for large-dimensional covariance matrices", *J. Multivariate Anal.*, vol. 88, no. 2, pp. 365–411, 2004.

### Consejos para la exposición con póster

- Cada expositor se para junto a su recuadro y lo señala; el póster es el apoyo visual, no se lee.
- Las fórmulas van pequeñas en el póster: sirven para que el público vea que hay teoría detrás, y el
  expositor las explica con palabras.
- Ensayen con cronómetro. Si se pasan, recorten primero las fórmulas de la parte de Harold y dejen
  solo la idea de cada modelo.

### Preguntas probables

| Pregunta | Respuesta corta |
|---|---|
| "¿Y si entrenan mejor la red, le ganaría?" | Probamos dos arquitecturas, con hiperparámetros y 5 semillas; la ventaja que tenía en entrenamiento desapareció fuera de muestra. El rendimiento diario es casi ruido. |
| "¿La LSTM no acertaba la dirección el 55 % de las veces?" | Fue un análisis secundario: la prueba es optimista porque las acciones del mismo día están correlacionadas, y en validación no fue significativo. Es un indicio, no una conclusión. |
| "¿Por qué no usar solo las acciones buenas?" | Elegir acciones mirando sus resultados es sesgo de selección; los criterios se fijaron con entrenamiento. |
| "¿20 meses alcistas no sesgan el resultado?" | Por eso repetimos el análisis año por año desde 2021, que incluye años malos, y las conclusiones se mantuvieron. |
| "¿Esto se puede usar para invertir?" | Es una simulación histórica en pesos, sin impuestos y con acciones poco líquidas; no es una recomendación de inversión. |
