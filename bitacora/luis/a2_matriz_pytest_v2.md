# Matriz de la etapa 4 · qa_pytest v2

Modelo: gemini / gemini-3.1-flash-lite · casos de entrada: `a2_casos_entrada.json` (los mismos para v1 y v2)

Artefacto y Válida son del intento final; la última columna son los errores que la validación devolvió en el 1.er intento.

| Entrada | Rep | Prompt | Artefacto (final) | Válida | Intentos | 1.er intento | Errores (1.er intento) |
|---|---|---|---|---|---|---|---|
| RF07 | 1 | qa_pytest.v2 | test_rf07.py · 5/5 casos con su test | ✓ | 1 | ✓ | — |
| RF12 | 1 | qa_pytest.v2 | test_rf12.py · 8/8 casos con su test | ✓ | 1 | ✓ | — |
| RF12 | 2 | qa_pytest.v2 | test_rf12.py · 8/8 casos con su test | ✓ | 1 | ✓ | — |
| RF12 | 3 | qa_pytest.v2 | test_rf12.py · 8/8 casos con su test | ✓ | 1 | ✓ | — |
| RF15 | 1 | qa_pytest.v2 | test_rf15.py · 9/9 casos con su test | ✓ | 1 | ✓ | — |

Consistencia (RF12 × 3): [(True, 8, 'test_rf12.py'), (True, 8, 'test_rf12.py'), (True, 8, 'test_rf12.py')]  ← (válida al 1.er intento, casos con test, nombre_archivo)
