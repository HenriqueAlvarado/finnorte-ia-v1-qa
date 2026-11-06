# Matriz del flujo completo · v1-qa

Modelo: gemini/gemini-3.5-flash · entrada: `datos/v1-qa/requisitos/RF12-transferencia.md` · repeticiones: 3 · contexto (RAG): sí, k=4 · flujo: v1-qa

Cada etapa valida contra su esquema y su `validar=`. Si falla tras el reintento, el flujo se detiene ahí.

| Rep | Etapa | Prompt | Artefacto | Válida | Intentos | ms | USD | Errores |
|---|---|---|---|---|---|---|---|---|
| 1 | analizar | qa_analizar.v2 | RF12 · dinero=True · 8 reglas · 4 ambigüedades | ✓ | 1 | 25515 | 0.003215 | — |
| 1 | casos | qa_casos.v2 | 8 casos · tipos: 8 | ✓ | 1 | 18469 | 0.003767 | — |
| 1 | revisar | qa_revisar.v1 | cumple_qa08=True · 0 faltantes · 0 hallazgos | ✓ | 1 | 9337 | 0.001441 | — |
| 1 | pytest | qa_pytest.v3 | test_rf12.py · 8 tests · 194 lineas | ✓ | 2 | 40984 | 0.010768 | — |
| 1 | **total** | | | ✓ | | 94308 | 0.019191 | |
| 2 | analizar | qa_analizar.v2 | RF12 · dinero=True · 8 reglas · 5 ambigüedades | ✓ | 1 | 15588 | 0.003457 | — |
| 2 | casos | qa_casos.v2 | 8 casos · tipos: 8 | ✓ | 1 | 17992 | 0.003776 | — |
| 2 | revisar | qa_revisar.v1 | cumple_qa08=True · 0 faltantes · 0 hallazgos | ✓ | 1 | 14758 | 0.001468 | — |
| 2 | pytest | qa_pytest.v3 | test_rf12.py · 8 tests · 178 lineas | ✓ | 1 | 31688 | 0.005920 | — |
| 2 | **total** | | | ✓ | | 80031 | 0.014622 | |
| 3 | analizar | qa_analizar.v2 | RF12 · dinero=True · 8 reglas · 4 ambigüedades | ✓ | 1 | 22559 | 0.003152 | — |
| 3 | casos | qa_casos.v2 | 8 casos · tipos: 8 | ✓ | 1 | 41877 | 0.003952 | — |
| 3 | revisar | qa_revisar.v1 | cumple_qa08=True · 0 faltantes · 0 hallazgos | ✓ | 1 | 17672 | 0.001457 | — |
| 3 | pytest | qa_pytest.v3 | test_rf12.py · 8 tests · 195 lineas | ✓ | 1 | 32175 | 0.006338 | — |
| 3 | **total** | | | ✓ | | 114287 | 0.014899 | |

## Consistencia entre repeticiones

- **analizar**: rep 1: ✓ (RF12 · dinero=True · 8 reglas · 4 ambigüedades) · rep 2: ✓ (RF12 · dinero=True · 8 reglas · 5 ambigüedades) · rep 3: ✓ (RF12 · dinero=True · 8 reglas · 4 ambigüedades)
- **casos**: rep 1: ✓ (8 casos · tipos: 8) · rep 2: ✓ (8 casos · tipos: 8) · rep 3: ✓ (8 casos · tipos: 8)
- **revisar**: rep 1: ✓ (cumple_qa08=True · 0 faltantes · 0 hallazgos) · rep 2: ✓ (cumple_qa08=True · 0 faltantes · 0 hallazgos) · rep 3: ✓ (cumple_qa08=True · 0 faltantes · 0 hallazgos)
- **pytest**: rep 1: ✓ (test_rf12.py · 8 tests · 194 lineas) · rep 2: ✓ (test_rf12.py · 8 tests · 178 lineas) · rep 3: ✓ (test_rf12.py · 8 tests · 195 lineas)

Flujos completos: 3/3 intentadas · errores del proveedor: 0 · costo total: 0.048712 USD
