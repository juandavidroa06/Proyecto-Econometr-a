# AGENTS.md — Estándar de desarrollo para agentes de IA

> Archivo operativo principal. Todo agente de IA (o colaborador) que trabaje en
> este proyecto **debe** cumplir estas reglas. La versión explicativa y más
> detallada está en [`docs/buenas_practicas_agente.md`](docs/buenas_practicas_agente.md).

## 1. Entornos y reproducibilidad

- **Nunca** guardar secretos, API keys, contraseñas ni tokens en el código.
- Usar variables de entorno cuando sean necesarias.
- Mantener `.env` fuera del control de versiones (`.gitignore`).
- Crear `.env.example` solo si realmente se requieren variables de entorno.
- Fijar **versiones exactas** de dependencias en `requirements.txt`.
- Mantener `.gitignore` correctamente configurado.
- Preferir entornos virtuales.
- Registrar cambios importantes de dependencias en `informes/diario_decisiones.md`.
- El código debe ser **reproducible**.

## 2. Manejo de excepciones

- No ocultar excepciones inesperadamente.
- No devolver falsos estados de éxito.
- Diferenciar errores de **datos** de errores de **programación**.
- Los errores inesperados deben ser visibles (logging).
- Registrar información suficiente para diagnosticar un problema.
- **Nunca inventar datos** para que una ejecución "funcione".
- Si se usa un decorador propio, usar `from functools import wraps` y aplicar `@wraps`.

## 3. Principio de responsabilidad única

Cada módulo tiene una sola responsabilidad clara:

```
data/                  -> adquisición y validación
preprocessing/         -> transformación e imputación
exploratory_analysis/  -> análisis exploratorio
econometrics/          -> modelos econométricos (futuro)
```

- Evitar clases o módulos monolíticos.
- Preferir composición.
- No usar estado mutable global innecesario.

## 4. Validación

- Nunca confiar únicamente en que una función terminó sin error.
- Validar: entradas, salidas, tipos, dimensiones, fechas, columnas, faltantes e inválidos.
- `assert` **no** sustituye a la validación de producción.

## 5. Datos (reglas obligatorias)

### Datos crudos
- `datos/crudos/` es **inmutable**. Nunca modificarlo automáticamente.

### Datos procesados
- Toda transformación produce **archivos nuevos**, nunca sobrescribe los crudos.

### Trazabilidad
```
dato crudo -> validación -> transformación -> dato procesado -> resultado
```

- Nunca eliminar una observación sin documentarlo.
- Nunca inventar valores.
- Nunca ocultar valores faltantes.
- Toda imputación debe quedar marcada (bandera) y registrada.

## 6. Series temporales (reglas obligatorias)

- Respetar el **orden cronológico**.
- No usar `train_test_split` aleatorio.
- Evitar **data leakage**.
- No usar información futura para construir una variable histórica cuando el objetivo es predicción.
- Documentar toda transformación.
- Distinguir **análisis retrospectivo** de **predicción en tiempo real**.
- No interpretar correlación como causalidad.

## 7. Machine Learning (fases futuras)

- `train/validation/test` respetan el tiempo.
- No ajustar transformaciones con datos futuros.
- Documentar hiperparámetros; registrar semillas.
- Comparar modelos complejos contra benchmarks simples.
- No afirmar que un modelo es superior sin evidencia.

## 8. Verificación independiente

> Ningún agente puede afirmar que una tarea está completada solo porque escribió código.

Obligatorio:

1. ejecutar el código;
2. ejecutar los tests;
3. inspeccionar los resultados;
4. comprobar los archivos;
5. verificar métricas;
6. informar evidencia reproducible.

Preferir **5 resultados verificados** sobre **15 afirmaciones no verificadas**.

## 9. Decisiones metodológicas

Toda decisión importante se registra en `informes/diario_decisiones.md` con:
decisión, motivo, fecha, impacto, alternativas consideradas, si fue aceptada o rechazada.

## 10. API y agente futuro (no construir ahora)

Cuando llegue ese momento:
- contratos explícitos; códigos HTTP correctos; JSON; validación explícita;
- endpoint `/health`; separar desarrollo/producción;
- recursos costosos inicializados una sola vez; clasificar IO-bound / CPU-bound;
- no usar `pickle` como formato de intercambio externo.