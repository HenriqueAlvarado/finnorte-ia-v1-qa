# Etapa 3 · qa_revisar v1 contra v2

Evidencia: `a2_revisar_entradas.json` (entradas congeladas), `a2_revisar_v1_v2_gemini-3.1-flash-lite.json/.md` y `a2_revisar_v1_v2_gemini-3.5-flash.json/.md`. Script: `guia/a2_etapa3_revisar.py`.

## Qué cambia la v2 y por qué

Se analizaron las 186 ejecuciones reales de `qa_revisar.v1` en `bitacora/trazas.jsonl` (A2 y Avance 1): 74 % válidas al primer intento, 14 % tras reintento y **12 % fallidas aun con reintento**. Causas de esas 22 fallas, según `validar_revisar`:

| Causa | Veces |
|---|---|
| Conteo equivocado en `cobertura_tipos` (14 de 18 **de más**: `negativo` 7, `positivo` 4) | 18 |
| `cumple_qa08: true` aunque el propio modelo reportó un hallazgo que lo bloquea | 4 |
| Llave mal escrita (`un_centavo_arridos`) | 3 |

Las dos mejoras de la v2:

1. **Orden de dependencia de la salida:** `hallazgos` → `cobertura_tipos` → `casos_faltantes` → `cumple_qa08`. La v1 pedía `cumple_qa08` antes que `hallazgos`, así que el modelo decidía si cumplía antes de escribir sus hallazgos, y contaba antes de saber qué casos excluir.
2. **Conteo mecánico por el campo `tipo`:** se cuenta el valor tal como viene, sin reclasificar por lo que el caso prueba (un `limite` que espera un rechazo sigue siendo `limite`), y las 8 llaves van como una lista cerrada que se copia exacta.

`validar_revisar` y el esquema no cambian: el esquema no exige un orden de llaves.

## Cómo se midió

- **8 pares congelados** (análisis y casos) de la medición del Avance 1. En todos, la etapa `casos` pasó su validación y `revisar` v1 **falló (6) o necesitó reintento (2)** con `gemini-3.1-flash-lite`. Hay 5 requisitos de dinero y 3 que no lo son. La muestra está sesgada a casos difíciles, pero igual para las dos versiones, porque reciben exactamente las mismas entradas.
- **1 llamada por par y versión.** Válida = esquema + `validar_revisar` **al primer intento**, sin reintentos. El orden v1/v2 se alterna por par.
- **Por qué dos modelos:** casi todas las fallas de la v1 ocurrieron con `gemini-3.1-flash-lite`, que es el modelo del contrato y de la medición del Avance 1, y es donde la v2 puede mostrar diferencia. `gemini-3.5-flash` es el modelo de la `a2_matriz` y es más fuerte; ahí se mide si la v2 empeora algo.

## Resultados

### `gemini-3.1-flash-lite` (llave de Luis, los 8 pares)

| Par | Caso | v1 | v2 |
|---|---|---|---|
| 1 | q01 | ✗ | ✗ |
| 2 | q10 | ✗ | ✗ |
| 3 | q12 | ✗ | ✗ |
| 4 | q05 | ✗ | **✓** |
| 5 | q11 | ✗ | **✓** |
| 6 | q07 | ✗ | **✓** |
| 7 | q04 | ✗ | ✗ |
| 8 | q02 | ✓ | ✓ |
| **Válidas** | | **1/8** | **4/8** |

- **La v2 corrige** los tres conteos de más (pares 4, 5 y 6: `negativo` y `monto_cero`), que es la mejora 2.
- **Ya no se contradice en `cumple_qa08`**, que es la mejora 1. La v1 dijo `true` en el par 7 aunque ella misma había reportado un `entonces_no_verificable`. Los dos errores de `cumple_qa08` que quedan en la v2 (pares 1 y 2) son en cadena: el valor es coherente con sus propios faltantes y hallazgos, que estaban mal. Esta corrida no guardó la salida del modelo; la conclusión sale de los mensajes de error.
- **La v2 no corrige:**
  - creer que falta `limite` (pares 1 y 3, en las dos versiones);
  - un error de conteo en `idempotencia` (par 7);
  - el correo del par 2 (ver hallazgos).
- **Ningún par empeora.** Con 8 pares no hay significancia estadística.

### `gemini-3.5-flash` (incompleta: 6 de 8 pares)

| Par | Caso | Llave | v1 | v2 |
|---|---|---|---|---|
| 1 | q01 | Henrique | ✓ | ✓ |
| 2 | q10 | Henrique | ✗ | ✗ |
| 3 | q12 | Luis | ✓ | error 503 |
| 4 | q05 | Luis | ✓ | ✓ |
| 5 | q11 | Luis | error 503 | ✓ |
| 6 | q07 | Luis | ✓ | error 503 |
| 7 | q04 | — | sin medir | sin medir |
| 8 | q02 | — | sin medir | sin medir |

- En los 3 pares con las dos versiones medidas (1, 2 y 4), **el resultado es idéntico**. En total: v1 4 de 5 y v2 3 de 4 medidas.
- Con el modelo fuerte, la v1 ya acierta en casos donde con `flash-lite` fallaba (pares 1, 3, 4 y 6), así que **no hay diferencia observable**, y tampoco una señal de que la v2 empeore. La salida de la v2 respetó el orden nuevo en todas las medidas.
- **Por qué está incompleta:** las dos llaves llegaron al límite diario de la capa gratuita para este modelo, que Google reporta como `GenerateRequestsPerDayPerProjectPerModel-FreeTier` con límite de 20. Los 3 errores 503 («alta demanda») se reintentaron y, por el conteo, todo indica que esos reintentos también gastaron cuota. Los pares 7 y 8 y los tres resultados con 503 se pueden completar otro día con `--continuar`.

## Limitación conocida (no se corrige en esta entrega)

En el par 2 (q10), las dos versiones fallan con los dos modelos por lo mismo. Un caso trae un correo con dominio `fintech.example1`, claramente inventado, pero la regla (en el prompt y en `validar_revisar`) solo acepta como de prueba `ejemplo.com`, `test.com` y los dominios que **terminan** en `.example`. El modelo no lo marca como `datos_reales` y el código sí; de ahí sale además el error de conteo, porque ese caso no debe contar.

**Decisión:** queda documentado como limitación y no se cambia ni la regla ni la v2 en esta entrega. Se le avisó a Caro (etapa 2, que genera los casos), sin pedirle un cambio para esta entrega. Hay dos opciones para después:

- que la etapa 2 use solo los dominios de prueba de la lista;
- aceptar variantes de un dominio `.example` en una v3 de `qa_revisar` y en `validar_revisar`, siempre juntas, para que el prompt y el código sigan aplicando la misma regla.

## Efecto en el flujo

`FLUJO` usa ahora `qa_revisar.v2` (la versión más reciente) y `FLUJO_V1` sigue usando la v1. La medición del Avance 1 (`bitacora/av1_*.json`) se hizo con la v1.
