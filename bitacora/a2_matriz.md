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
| 2 | — | — | — | error del proveedor | — | — | — | LLMError: HTTP 429: {   "error": {     "code": 429,     "message": "You exceeded your current quota, please check your plan and billing details. For m |
| 3 | — | — | — | error del proveedor | — | — | — | LLMError: HTTP 429: {   "error": {     "code": 429,     "message": "You exceeded your current quota, please check your plan and billing details. For m |

## Consistencia entre repeticiones

- **analizar**: rep 1: ✓ (RF12 · dinero=True · 8 reglas · 4 ambigüedades)
- **casos**: rep 1: ✓ (8 casos · tipos: 8)
- **revisar**: rep 1: ✓ (cumple_qa08=True · 0 faltantes · 0 hallazgos)
- **pytest**: rep 1: ✓ (test_rf12.py · 8 tests · 194 lineas)

Flujos completos: 1/3 intentadas · errores del proveedor: 2 · costo total: 0.019191 USD

> Pendiente: las repeticiones 2 y 3 no se hicieron porque se agotó la cuota de Gemini (HTTP 429,
> límite de la capa gratuita). Se completan en cuanto se reinicie la cuota, corriendo de nuevo
> `python guia/a2_flujo_variante.py --rep 3`. Con una sola repetición todavía no hay medida de
> consistencia entre corridas.
