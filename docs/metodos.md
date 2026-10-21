# Metodología del proyecto

> **Estado:** ejecutada (Fases 0 a 21). Este documento describe **qué se hizo y cómo**, con
> las fórmulas principales. Las razones de cada elección, las alternativas descartadas y los
> resultados están en `informes/diario_decisiones.md` (citado como DEC-xxx); el resumen de
> resultados está en `informes/informe_final.md`.
> **Última actualización:** octubre de 2026

---

## 0. Principios de evaluación (aplican a todo)

- **Partición temporal congelada** (DEC-017, DEC-019, DEC-021): entrenamiento 2020-01-02 a
  2023-12-29, validación 2024, prueba 2025-01-02 a 2026-09-14. Los estimadores se ajustan con
  entrenamiento; la validación sirve para comparar y elegir; la prueba se abrió **una sola vez**
  (Fase 15, plan DEC-034). Lo calculado después sobre la prueba es exploratorio.
- **Planes registrados antes de ejecutar** para cada análisis confirmatorio (DEC-029, 032, 034,
  037, 039, 042, 046, 048, 049): qué se calcula, con qué prueba y con qué criterio.
- **Pronósticos a un paso** con información hasta t−1; **referencias simples** siempre presentes
  (media, cero, varianza constante, EWMA, 1/N, IBR).
- **Dependencia entre acciones:** las pérdidas se promedian por fecha antes de las pruebas
  agregadas. **Comparaciones múltiples:** corrección de Holm en cada familia.

## 1. Datos y calidad (Fases 1–3, DEC-003 a DEC-016, DEC-022, DEC-024)

- Nueve acciones de la BVC en Yahoo Finance (`Adj Close`), TRM y Brent (Yahoo) e IBR overnight
  del Banco de la República (descarga manual). Crudos inmutables; toda transformación crea
  archivos nuevos con banderas.
- Rendimientos: simple R_t = P_t/P_{t−1} − 1 y logarítmico r_t = ln(P_t/P_{t−1}).
- Valores extremos: se identifican (z-score, percentiles) y no se eliminan (DEC-009).
- Iliquidez: proporción de rendimientos exactamente cero en entrenamiento; umbral 20 %
  (5 ilíquidas: ETB, Grupo Bolívar, Promigas, Nutresa, Mineros).
- Precio inválido de la fuente (2024-05-03): NaN en la capa procesada y rendimiento de dos días
  el día siguiente, sin imputar (DEC-022). Para la prueba se fijó antes una regla mecánica: días
  con 2 o más acciones con |r_t| ≥ 5 % revertido al día siguiente (DEC-034).

### 1.1 Imputación del único valor faltante (Filtro de Kalman, DEC-012 a DEC-016)

Grupo Bolívar, `Adj Close` del 2026-03-10. Modelo de nivel local:

```
y_t  = mu_t + eps_t         (observación)
mu_t = mu_{t-1} + eta_t     (transición: camino aleatorio)
```

estimado con `statsmodels` y **suavizado** (usa información anterior y posterior). El valor
queda marcado (`es_imputado_kalman`, `retorno_depende_imputacion`). Validación: al ocultar
valores reales, el error relativo fue de 0,8 % a 1,5 %. Al usar información posterior, la
imputación es una reconstrucción histórica y **no** puede usarse como información en tiempo real
(DEC-015).

## 2. Análisis exploratorio (Fase 4)

Con entrenamiento: Jarque-Bera (normalidad), ADF y KPSS (estacionariedad de precios y
rendimientos), Ljung-Box sobre r y r² (autocorrelación y efectos ARCH) y ARCH-LM.

## 3. Pronóstico del rendimiento (Fases 7–10)

- **ARIMA(p,0,q)** por acción, p, q ≤ 3, selección por BIC; se ajusta en % por estabilidad
  numérica (DEC-023).
- **Random Forest y Gradient Boosting** agrupados (DEC-025): rezagos, medias y volatilidades
  móviles, días sin cambio, volumen relativo, mercado, TRM y Brent con fecha estrictamente
  anterior, indicador de empresa; filas asignadas por la fecha del objetivo; hiperparámetros por
  validación cruzada temporal expansiva de 5 pliegues dentro de entrenamiento.
- **MLP y LSTM** (PyTorch, DEC-026): escalado con entrenamiento; parada temprana con el último
  20 % de entrenamiento; 5 semillas promediadas; la LSTM recibe los últimos 30 días.
- **Comparación** (DEC-027): Diebold-Mariano con corrección de Harvey-Leybourne-Newbold sobre
  d_t = L_modelo,t − L_ref,t; Model Confidence Set (Hansen, Lunde y Nason, 2011, estadístico
  T_max, 10 %); R² fuera de muestra R²_OS = 1 − Σ e²_modelo / Σ e²_media con intervalo por
  bootstrap de bloques; Pesaran-Timmermann para la dirección.

## 4. Pronóstico de la volatilidad (Fase 7, DEC-029/030)

- **GARCH(1,1)-t:** σ²_t = ω + α ε²_{t−1} + β σ²_{t−1}.
- **EWMA (RiskMetrics):** σ²_t = λ σ²_{t−1} + (1 − λ) r²_{t−1}, λ = 0,94, sin parámetros
  estimados.
- **HAR** (Corsi, 2009) para la varianza realizada semanal, con componentes diario, semanal y
  mensual; RF, GB y MLP como retadores sobre log RV con corrección de Duan.
- **Pérdida QLIKE:** L = log h + proxy / h (Patton, 2011), robusta a un proxy ruidoso (r²).

## 5. Riesgo: VaR y Expected Shortfall (Fase 11, DEC-028, DEC-031)

- Métodos (a un día, 95 % y 99 %): simulación histórica (250 días), normal con σ EWMA,
  GARCH-t y simulación histórica filtrada (FHS: residuos de entrenamiento × σ EWMA del día).
- ES empírico robusto a empates: media de las k = ⌈α·n⌉ peores observaciones (DEC-031).
- Backtesting: Kupiec, Christoffersen, semáforo de Basilea, prueba del ES, pérdida cuantílica y
  MCS; Holm sobre las combinaciones.

## 6. Optimización y backtesting (Fases 12–14, DEC-031 a DEC-033)

- Portafolios: 1/N; mínima varianza (muestral y Ledoit-Wolf); mínimo CVaR 95 %
  (Rockafellar-Uryasev, programa lineal); paridad de riesgo; máximo Sharpe.
- Restricciones: pesos ≥ 0 que suman 1, máximo 30 % por acción y 40 % por sector.
- Sharpe = (R_p − r_f) / σ_p con el IBR diario efectivo como r_f.
- **Walk-forward:** rebalanceo mensual, ventana móvil de 252 días, pesos que derivan entre
  rebalanceos, costo = c × Σ|w_objetivo − w_derivado| con c = 20 pb (0 y 50 pb como
  sensibilidad). Diferencia de Sharpe frente al 1/N con bootstrap por bloques (21 días) y Holm.

## 7. Evaluación final, robustez e interpretación (Fases 15–17)

- **Fase 15** (DEC-034 a DEC-036): las mismas familias en la prueba, con los modelos reestimados
  con 2020–2024 y los procedimientos ya congelados; ensayo previo obligatorio que reprodujo las
  Fases 7–14.
- **Fase 16** (DEC-037/038, exploratoria): 24 configuraciones de portafolio, volatilidad y VaR
  año por año, rendimiento año por año, con criterios fijados antes.
- **Fase 17** (DEC-039/040, descriptiva): determinantes de los pesos, beta de Dimson, riesgo
  prometido frente al realizado, autocorrelación e iliquidez, petróleo.

## 8. Extensiones (Fase 21, DEC-046/047)

- **SPA de Hansen (2005)** y Reality Check de White (2000): ¿algún modelo supera a la
  referencia? Bootstrap estacionario de Politis-Romano (bloque medio de 10).
- **Acierto direccional robusto:** u_it = (1{y>0} − p_y)(1{f>0} − p_f), sumado por fecha, con
  varianza de Newey-West (rezago ⌊4(T/100)^{2/9}⌋).
- **Prueba del ES de Acerbi y Székely (2014):** Z2 = Σ X_t I_t / (T α ES_t) + 1, con p-valor por
  simulación de la distribución predictiva de cada método.
- **Sharpe probabilístico y deflactado** (Bailey y López de Prado) y prueba de diferencia de
  Sharpe de Ledoit y Wolf (2008) con HAC.
- **Portafolios con pronósticos:** covarianza EWMA (λ = 0,97), CCC-GARCH, volatility targeting
  del 1/N (x = min(1, σ_obj/σ̂), resto al IBR) y carteras diarias con las k acciones de mayor
  pronóstico de cada modelo.

## 9. Prueba prospectiva (DEC-048)

Datos posteriores al 2026-09-14, descargados una sola vez por el equipo. Evaluación
confirmatoria con los primeros 252 días bursátiles y seis hipótesis fijadas de antemano
(P1–P6), con los mismos procedimientos de la Fase 15 y modelos reestimados con toda la muestra
2020–2026. Código: `src/data/prospectiva.py` y `src/prospectiva.py` (probado con un simulacro).

## 10. Agente de IA (Fases 18, 19 y 21; DEC-041 a DEC-044, DEC-049/050)

Agente sobre Claude Code (skill `/investigador`) con 11 herramientas de contrato estricto (leer y
buscar en el diario, leer y consultar resultados, pruebas de estacionariedad, ARIMA con
entrenamiento, verificación de reproducibilidad, tests, proponer cambios), disponibles por línea
de comandos y como servidor MCP. La regla de oro (no abrir la prueba, no descargar datos, no
modificar datos, código ni metodología) se impone por diseño de las herramientas y con un hook
que bloquea esas operaciones. Se evaluó dos veces con escenarios y criterios fijados antes (la
segunda, con 12 escenarios y 3 repeticiones).

## Reproducibilidad

Versiones exactas en `requirements.txt`; semillas fijas; 246 tests automáticos;
`python -m src.reproducir` reejecuta las fases y compara cada tabla con la versión publicada.
