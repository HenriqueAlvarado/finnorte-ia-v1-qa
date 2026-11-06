# Etapa 3 · qa_revisar v1 contra v2 · gemini/gemini-3.1-flash-lite

8 pares congelados (`a2_revisar_entradas.json`), 1 llamada por par y versión, válida = esquema + `validar_revisar` al primer intento, sin reintentos.

| Par | Origen | v1 en el Avance 1 | v1 | v2 | Errores v1 | Errores v2 |
|---|---|---|---|---|---|---|
| 1 | av1_C.json · detalle[0] · q01 | falló | ✗ | ✗ | conteo o faltantes | conteo o faltantes, cumple_qa08 incoherente |
| 2 | av1_C.json · detalle[9] · q10 | falló | ✗ | ✗ | conteo o faltantes, cumple_qa08 incoherente, hallazgo no reportado | conteo o faltantes, cumple_qa08 incoherente, hallazgo no reportado |
| 3 | av1_C.json · detalle[11] · q12 | falló | ✗ | ✗ | conteo o faltantes | conteo o faltantes |
| 4 | av1_C.json · detalle[28] · q05 | falló | ✗ | ✓ | conteo o faltantes | — |
| 5 | av1_C.json · detalle[41] · q11 | falló | ✗ | ✓ | conteo o faltantes | — |
| 6 | av1_B.json · detalle[6] · q07 | falló | ✗ | ✓ | conteo o faltantes | — |
| 7 | av1_C.json · detalle[3] · q04 | válida al intento 2 | ✗ | ✗ | cumple_qa08 incoherente | conteo o faltantes |
| 8 | av1_D.json · detalle[23] · q02 | válida al intento 2 | ✓ | ✓ | — | — |

| Versión | Válidas al 1.er intento | Errores por categoría | Errores del proveedor |
|---|---|---|---|
| v1 | 1/8 | {'conteo o faltantes': 6, 'cumple_qa08 incoherente': 2, 'hallazgo no reportado': 1} | 0 |
| v2 | 4/8 | {'conteo o faltantes': 4, 'cumple_qa08 incoherente': 2, 'hallazgo no reportado': 1} | 0 |
