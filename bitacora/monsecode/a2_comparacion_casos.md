# Etapa 2 (qa_casos) · v1 contra v2

Dueña de la etapa: Monsecode. Flujo medido: `analizar` (qa_analizar.v1) → `casos` (qa_casos.v1 o v2), con `validar=casos_cubren_qa08`.
Modelo: `gemini-3.1-flash-lite` (en `a2_trazas_casos.jsonl` está el prompt, la versión, el modelo y la fecha de cada llamada). Fecha: 2026-11-05.
Entradas: RF12, RF07, RF18 y RF12 dos veces más (consistencia). Sin contexto del Mini-RAG (`(sin contexto)`), por eso `fuente` queda vacía.
Datos crudos: `a2_casos_v1.json` y `a2_casos_v2.json`.

## Qué falló en la v1 y qué cambió en la v2
| Fallo medido en v1 | Cambio en v2 |
|---|---|
| `fuente` rellenada con "N/A" rompía el esquema (3 de 5 corridas) | `fuente` es opcional y se omite si no hay documento qa-xx |
| Nunca salía el tipo `limite`; la etapa 3 lo exige en dinero (5 de 5) | Lista cerrada de los 8 tipos con autoverificación de conteo; `limite` y `limite_exacto` son tipos distintos |
| Faltaban `monto_cero` y `monto_negativo` en dinero | Mismos 8 tipos obligatorios en dinero |
| Mi regla aceptaba `limite_exacto` en lugar de `limite` (no coincidía con qa_revisar) | `casos_cubren_qa08` exige los 8 tipos en dinero |

## Resultado (5 corridas, mismo modelo, mismas entradas)
| Medida | v1 | v2 |
|---|---|---|
| Corridas válidas | 0 de 5 | 4 de 5 |
| Válidas al primer intento | 0 de 5 | 4 de 5 |
| `fuente: "N/A"` que rompe el esquema | 3 de 5 | 0 de 5 |
| Corridas con el tipo `limite` | 0 de 5 | 5 de 5 |
| Corridas con tipos faltantes según la etapa 3 | 5 de 5 | 1 de 5 |

La corrida que falló en v2 (RF12 rep3) omitió `un_centavo_arriba`; la regla en código lo detectó y, después del reintento, siguió fallando.

## Limitaciones
- La v1 se midió con la regla de validación de v1 (aceptaba `limite_exacto` en lugar de `limite`). La fila "tipos faltantes según la etapa 3" se calculó aparte, con el criterio de qa_revisar, y por eso sí muestra ese fallo.
- Son 5 corridas con un modelo ligero y cuota gratuita. La matriz oficial del flujo completo (`bitacora/a2_matriz.md`, gemini-3.5-flash, RF12 × 3) muestra `qa_casos.v2` válida al primer intento las 3 veces.
- RF18 (bloqueo de tarjeta) la etapa 1 la marcó como operación de dinero, por eso se le exigieron los 8 tipos.
