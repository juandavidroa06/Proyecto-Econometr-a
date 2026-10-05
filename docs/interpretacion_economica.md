# Interpretación económica de los resultados (Fase 17)

> Plan registrado en DEC-039 y resultados en DEC-040 (`informes/diario_decisiones.md`).
> Cálculos en `src/interpretacion/fase17.py` → `resultados/fase17/*.csv` y
> `resultados/graficos/fase17_interpretacion.png`. Los análisis A–E usan solo
> 2020–2024 (entrenamiento y validación). Son **explicativos, no causales**.
> Las afirmaciones de contexto marcadas como *hipótesis* deben respaldarse con
> fuentes antes del informe final.

## 1. ¿Por qué ciertas empresas reciben más peso?

**Lo que muestran los datos (análisis A).** En los 48 rebalanceos de la Fase 14,
los pesos de las estrategias de riesgo dependen sobre todo de la **volatilidad**:
la correlación de rangos entre peso y volatilidad es −0,72 (mínima varianza
muestral), −0,77 (Ledoit-Wolf), −0,76 (paridad de riesgo) y −0,50 (mínimo CVaR),
negativa en el 96–100 % de las fechas. La correlación con las demás acciones
pesa mucho menos (−0,11 a −0,18), y la iliquidez apenas influye (+0,07 a +0,18,
con signo cambiante entre fechas).

**Interpretación.** Los optimizadores se comportan, en la práctica, como
"inviertan menos en lo que se movió mucho el último año". Con 9 acciones y una
ventana de un año, las correlaciones estimadas son ruidosas y aportan poca
información estable; la volatilidad es la señal más fuerte. Por eso la paridad
de riesgo y la mínima varianza terminan cerca de un "1/N ponderado por la
inversa de la volatilidad".

**Las acciones ilíquidas.** Reciben en promedio un 57–59 % del peso en las
estrategias de mínima varianza y mínimo CVaR, frente al 55,6 % del 1/N: hay una
ligera sobreponderación, con meses en que llega al 78–90 %. Grupo Bolívar,
Mineros y Promigas son las más favorecidas por la mínima varianza.

## 2. ¿Las acciones ilíquidas parecen menos riesgosas de lo que son?

**Lo que muestran los datos (análisis B).** La beta de Dimson, que suma la
reacción al mercado del día anterior, del mismo día y del siguiente, es mayor
que la beta simple en 8 de las 9 acciones. La subestimación es grande en Grupo
Bolívar (34 %), Mineros (29 %), Ecopetrol (22 %), ETB (20 %) y Davivienda (16 %).

**Pero la hipótesis del plan no se confirma.** No hay una relación clara entre
iliquidez y subestimación (correlación de rangos 0,18, p = 0,64, con 9 acciones).
Dos casos rompen el patrón:
- **Ecopetrol, la más líquida, muestra una beta adelantada grande** (0,32 con el
  mercado del día siguiente): Ecopetrol se mueve **antes** que el resto. Es
  coherente con que las demás acciones incorporen la información con retraso,
  no con que Ecopetrol sea ilíquida.
- **Nutresa** tiene una beta de Dimson menor que la simple. *Hipótesis:* su
  precio estuvo dominado por las ofertas públicas de adquisición del periodo
  2021–2023 y no por el mercado.

**Implicación.** El riesgo medido día a día subestima la exposición real de
varias acciones al mercado. Las covarianzas que usa el optimizador están
sesgadas a la baja para esas acciones, lo que da una diversificación aparente
mayor que la real.

## 3. ¿Por qué el 1/N gana fuera de muestra?

**Lo que muestran los datos (análisis C).** Las estrategias optimizadas
**prometen** menos riesgo que el 1/N: su volatilidad estimada en la ventana es
del 13,9–15,3 % anual, frente al 16,0 % del 1/N. **Esa reducción no se
materializa**: el mes siguiente, la volatilidad realizada del 1/N (14,1 %) es
igual o menor que la de las optimizadas (14,1–15,2 %). El 1/N incluso
sobreestima su riesgo (razón realizada/estimada 0,84), mientras que las
optimizadas aciertan o lo subestiman levemente (0,95–0,99).

**La hipótesis del plan se confirma solo en parte.** Las optimizadas no
subestiman su riesgo mucho más que el 1/N. Lo que pasa es que **la ventaja de
riesgo que el optimizador cree haber encontrado desaparece fuera de muestra**,
mientras que la optimización sí cambia la exposición a cada acción (más peso en
lo que estuvo tranquilo el último año) y paga costos por rotación. Sin
reducción real de riesgo y con un rendimiento esperado que no se puede estimar
mejor que la media (Fases 7–10), no hay nada que compense: el 1/N, que no
estima nada, no comete error de estimación.

## 4. ¿Por qué el rendimiento no es predecible, pero el último rendimiento parecía importante?

**Lo que muestran los datos (análisis D).** La autocorrelación de primer orden
es negativa y significativa en las acciones menos líquidas: ETB −0,28 (45 % de
días sin cambio), Promigas −0,19 (32 %), Celsia −0,13. Ecopetrol, la más
líquida, tiene autocorrelación positiva (+0,10). La relación entre iliquidez y
autocorrelación es negativa (correlación de rangos −0,62, p = 0,08, con solo 9
acciones).

**Interpretación.** Es el patrón esperado del rebote entre precios de compra y
venta en acciones poco negociadas: si una operación se hace al precio de compra
y la siguiente al de venta, aparece una reversión que no es una oportunidad de
inversión, porque capturarla exige pagar justamente ese diferencial. Explica
por qué el rendimiento del día (`r_lag0`) fue la variable más importante en los
modelos de las Fases 8 y 9 sin que eso se tradujera en mejores pronósticos con
significancia.

## 5. Ecopetrol y el petróleo

**Lo que muestran los datos (análisis E).** Ecopetrol tiene una correlación de
0,51 (entrenamiento) y 0,32 (validación) con el rendimiento del Brent **del
mismo día**, muy por encima de las otras 8 acciones (≤ 0,19). Con el Brent del
**día anterior** la correlación cae a 0,07–0,08.

**Interpretación.** El mercado colombiano incorpora el precio del petróleo en
Ecopetrol el mismo día. Por eso el Brent rezagado no ayudó a predecir
(Fase 8): la información ya estaba en el precio. Es una forma concreta de
eficiencia informativa.

## 6. Contexto: tasas de interés y renta variable

**Lo que muestran los datos (análisis F).** El IBR overnight pasó de un mínimo
de **1,61 %** (marzo de 2021) a un máximo de **12,35 %** (mayo de 2023), y bajó
a 8,96 % al cierre de 2024. El 1/N de 9 empresas rindió −4,0 % anual en
2021–2023, cuando el IBR medio fue 7,3 %; luego +29,6 % en 2024, +55,8 % en
2025 y +39,9 % anualizado en 2026, por encima del IBR (9–11 %).

**Interpretación (hipótesis).** El periodo de pérdidas coincide con el ciclo
de alzas de tasas del Banco de la República, y la recuperación con el inicio de
las bajadas. Es coherente con que tasas más altas reduzcan el valor presente de
los flujos de las empresas y hagan más atractiva la renta fija, pero **estos
datos no permiten afirmar causalidad**: en el mismo periodo hubo otros factores
(por ejemplo, el ciclo político y fiscal, el precio del petróleo y operaciones
corporativas como las de Nutresa), que el equipo debe documentar con fuentes.

## 7. Síntesis para el informe

1. El riesgo es más predecible que el rendimiento, y la volatilidad reciente es
   la señal que dominan todos los optimizadores.
2. Las covarianzas diarias subestiman la exposición de varias acciones al
   mercado (negociación no sincrónica y reacción rezagada al líder del
   mercado, Ecopetrol).
3. El optimizador promete reducciones de riesgo que no se cumplen fuera de
   muestra; el 1/N, sin error de estimación, no es superado.
4. Las regularidades de corto plazo (reversión diaria) son efectos de
   microestructura propios de acciones poco líquidas, no oportunidades
   rentables tras costos.
5. El contexto de tasas ayuda a entender por qué la renta variable perdió
   frente al IBR en 2021–2023 y lo superó en 2024–2026, sin implicar causalidad.
