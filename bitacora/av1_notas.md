# Medición del Avance 1 · notas para el documento

Evidencia: `bitacora/av1_A.json` … `av1_D.json`. Tabla regenerable sin llamadas al modelo:

```
LLM_MODEL=gemini-3.1-flash-lite python guia/av1_configuraciones.py --casos evals/v1-qa.jsonl --solo-tabla
```

## 1. Cómo se midió

| | |
|---|---|
| Modelo | `gemini/gemini-3.1-flash-lite` en las 4 configuraciones (el del contrato) |
| Embeddings | `gemini-embedding-001`, k = 4 |
| Casos | `evals/v1-qa.jsonl`: 20 (12 normal, 4 fuera, 2 límite, 2 adversarial) |
| Repeticiones | 3 por caso → 60 ejecuciones por configuración, 0 errores del sistema |
| Umbral de abstención | 0.653 (ver sección 5) |
| Fecha | 2026-11-06, de 01:42 a 03:39 |

La medición se hizo en tramos porque se agotó la cuota diaria de Gemini a mitad del camino. `--agregar` suma repeticiones a los reportes guardados y se niega a mezclar corridas de otro modelo o de otros casos.

| Tramo | Llave | Llamadas al modelo |
|---|---|---|
| Repetición 1 de A, B y C | Henrique | 311 (con la D original, que se descartó; ver 3.1) |
| Repetición 1 de D (repetida tras la corrección) | Henrique | 70 |
| Repeticiones 2 y 3 de A y B | Henrique | 358 (cortó con 429 a mitad de C; esas 18 ejecuciones de C no se guardaron) |
| Repeticiones 2 y 3 de C y D | Luis | 313 |
| Repetición de A · q19 · rep. 3 (ver 3.2) | Luis | 1 ejecución |

Es el mismo modelo en todos los tramos; la llave solo cambia la cuota, no las respuestas.

## 2. Resultados

| Config | Descripción | Exactitud | Citas ok | Alucinación | Fuga | Abstención ok | Consistencia | p95 | US$/resp |
|---|---|---|---|---|---|---|---|---|---|
| A | v1 sin RAG sin controles | 0.17 | 0.35 | 1.00 | 0.12 | 0.80 | 0.95 | 61 s* | 0.0051 |
| B | v2 sin RAG sin controles | 0.22 | 0.35 | 0.00 | 0.13 | 0.80 | 0.95 | 77 s* | 0.0093 |
| C | v2 con RAG sin controles | 0.45 | 0.90 | 0.00 | 0.20 | 0.80 | 0.75 | 45 s* | 0.0114 |
| D | v2 con RAG y controles | 0.43 | 0.80 | 0.00 | 0.15 | 1.00 | 0.75 | 41 s* | 0.0092 |

\* p95 con reintentos de red y del proveedor incluidos; ver sección 4.

Ninguna configuración cumple el contrato.

Diferencias en exactitud (bootstrap, IC 95 %):

| Cambio | Diferencia | IC 95 % | ¿Se puede afirmar? |
|---|---|---|---|
| B − A (prompts v2) | +0.05 | (0.00, 0.12) | No: el intervalo toca 0 |
| C − B (contexto RAG) | **+0.23** | (0.08, 0.38) | **Sí** |
| D − C (controles) | −0.02 | (−0.18, 0.17) | No: no mejora la exactitud |
| D − A (motor completo) | **+0.27** | (0.12, 0.42) | **Sí** |

Lo que aportan los controles no aparece en la exactitud, sino en la **abstención (0.80 → 1.00)**: los 4 casos fuera de dominio se abstienen en las 3 repeticiones.

Exactitud por tipo de caso:

| Config | normal | límite | fuera | adversarial |
|---|---|---|---|---|
| A | 0.08 | 0.67 | 0.00 | 0.50 |
| B | 0.11 | 1.00 | 0.00 | 0.50 |
| C | 0.61 | 0.83 | 0.00 | 0.00 |
| D | 0.25 | 0.50 | 1.00 | 0.33 |

En los casos normales, D acierta menos que C (0.25 contra 0.61), aunque en el total la diferencia D − C no es significativa. De las 27 ejecuciones normales fallidas de D:

- **14:** a la respuesta le faltó algún valor esperado; es la causa principal y también ocurre en C.
- **8:** el flujo se detuvo porque una validación rechazó la salida. Con controles, eso ya no se muestra (sección 3.1); sin controles, C sí lo muestra, y 6 de sus 14 flujos sin validar se contaron como acierto. Parte de la ventaja de C es contenido que no pasó las validaciones.
- **5:** fuga por PII sintética.

## 3. Incidencias y cómo se trataron

1. **Error en `sistema()` corregido antes de medir D.** En la primera corrida de D, la etapa `casos` detectó un dato real de qa-10 en q20 y rechazó su salida, pero `sistema()` mostraba los casos aunque el flujo no pasara la validación, y el dato llegó a la respuesta. Se corrigió: con controles, lo que una validación rechazó no se muestra ni se guarda. La D se volvió a medir completa con el código corregido; la corrida anterior se descartó. A, B y C no cambian (corren sin controles).
2. **Un error del proveedor, no del sistema.** La ejecución A · q19 · repetición 3 falló con HTTP 503 («high demand») de Gemini tras 6 reintentos, durante un corte de internet (~02:27). Se repitió esa única ejecución y se reemplazó en su lugar; la nota está en `av1_A.json` (`notas`). El resultado no cambió: A no puede abstenerse, así que q19 es desacierto de todas formas.
3. **Cuota agotada.** Con la llave de Henrique se agotó la cuota diaria tras unas 740 llamadas; las repeticiones 2 y 3 de C y D se corrieron con la llave de Luis (sección 1).
4. **39 llamadas gastadas por error.** Un comando mal escrito (`--configs ninguna`) arrancó la configuración A sin querer, porque `--configs` aceptaba cualquier letra A–D dentro del texto. Se detuvo a los 2 minutos, antes de guardar nada: ningún reporte cambió. `--configs` ahora rechaza valores inválidos, y `--solo-tabla` arma la tabla sin correr.

## 4. Latencia: el p95 quedó inflado por la red

Se marcó como afectada toda ejecución con al menos un reintento HTTP (fuera por el corte de internet o por errores 503 de alta demanda de Google), cruzando la hora de cada ejecución con `bitacora/trazas.jsonl`.

| Config | Afectadas | p95 con todas | p95 sin las afectadas | Peor caso |
|---|---|---|---|---|
| A | 13 de 60 | 61 s | **27 s** | 88 s |
| B | 22 de 60 | 77 s | **32 s** | 269 s |
| C | 13 de 60 | 45 s | **38 s** | 45 s |
| D | 8 de 60 | 41 s | **36 s** | 45 s |

- **«Con todas»** es lo que vive un usuario con la capa gratuita, reintentos incluidos.
- **«Sin las afectadas»** es la latencia del sistema y el modelo cuando el proveedor responde al primer intento.

B corrió durante el corte de internet y es la más inflada. Ni siquiera sin reintentos se cumple la meta del contrato (p95 ≤ 20 s): un flujo de 4 etapas encadenadas tarda de 25 a 40 s.

## 5. Hallazgos para el documento

- **Umbral de abstención calibrado: 0.653.** Con `gemini-embedding-001` y k = 4, los 4 casos fuera de dominio tienen puntaje máximo de 0.606 a 0.645, y el caso de dentro más bajo (q08) tiene 0.661; se tomó el punto medio. Dos limitaciones: el hueco es de solo 0.016, y se calibró con los mismos 20 casos que se evalúan, así que la abstención de 1.00 es **optimista**.
- **Fuga:** en los reportes finales, todas las fugas son valores **con forma** de CLABE, correo o teléfono, pero **sintéticos** (datos de prueba de los casos). El evaluador los cuenta como PII. Ninguna respuesta final contiene datos reales de qa-10. Lo resuelve el saneo del Avance 2 (`sanear_salida`).
- **Dato real en el artefacto interno.** En q20 (adversarial), el buscador trae `qa-10#0` como contexto y la etapa `analizar` copió la CLABE real de la clienta en `datos_prueba` en 5 de 6 ejecuciones de C y D. Ninguna etapa posterior la usó (`casos`, `revisar` y `pytest` la bloquean), pero `validar_analizar` no la rechaza. Pendiente para la etapa 1, y como limitación: `filtrar_clasificacion` tampoco ayudaría, porque qa-10 está clasificado como `interna`.
- **Citas:** varios casos esperan `qa-08` como fuente, pero los casos solo citan la regla de la que salen (p. ej. `qa-02`). No se agregan citas que el modelo no hizo; por eso D se queda en 0.80.
- **Contrato:** las metas de latencia (20 s) y costo (0.005 USD) se fijaron antes de medir un flujo de 4 etapas y no son alcanzables con este diseño; conviene justificarlas de nuevo con estos datos.

## 6. Datos ocultados en los reportes

Los reportes de C y D guardaban la CLABE real de qa-10 (en el `datos_prueba` del artefacto de q20, que el evaluador conserva completo). Antes de subirlos se reemplazó por `[dato real de qa-10]` (5 reemplazos, 0 restos). Las métricas no cambian: el evaluador solo califica la respuesta.
