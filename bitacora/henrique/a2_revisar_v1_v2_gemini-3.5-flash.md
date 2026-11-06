# Etapa 3 · qa_revisar v1 contra v2 · gemini/gemini-3.5-flash

**INCOMPLETA:** solo 6 pares medidos.

6 pares congelados (`a2_revisar_entradas.json`), 1 llamada por par y versión, válida = esquema + `validar_revisar` al primer intento, sin reintentos.

| Par | Origen | v1 en el Avance 1 | v1 | v2 | Errores v1 | Errores v2 |
|---|---|---|---|---|---|---|
| 1 | av1_C.json · detalle[0] · q01 | falló | ✓ | ✓ | — | — |
| 2 | av1_C.json · detalle[9] · q10 | falló | ✗ | ✗ | conteo o faltantes, cumple_qa08 incoherente, hallazgo no reportado | conteo o faltantes, cumple_qa08 incoherente, hallazgo no reportado |
| 3 | av1_C.json · detalle[11] · q12 | falló | ✓ | error del proveedor | — | — |
| 4 | av1_C.json · detalle[28] · q05 | falló | ✓ | ✓ | — | — |
| 5 | av1_C.json · detalle[41] · q11 | falló | error del proveedor | ✓ | — | — |
| 6 | av1_B.json · detalle[6] · q07 | falló | ✓ | error del proveedor | — | — |

| Versión | Válidas al 1.er intento | Errores por categoría | Errores del proveedor |
|---|---|---|---|
| v1 | 4/5 | {'conteo o faltantes': 1, 'cumple_qa08 incoherente': 1, 'hallazgo no reportado': 1} | 1 |
| v2 | 3/4 | {'conteo o faltantes': 1, 'cumple_qa08 incoherente': 1, 'hallazgo no reportado': 1} | 2 |
