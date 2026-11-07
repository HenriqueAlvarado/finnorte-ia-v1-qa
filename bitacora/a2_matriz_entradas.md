# Matriz del flujo completo con 3 entradas · v1-qa

Modelo: gemini/gemini-3.1-flash-lite · entradas: RF07, RF12, RF15 (datos/v1-qa/requisitos/) · contexto (RAG): sí, k=4 · flujo: v1-qa

Checkpoint 5 del Lab 2: cada entrada recorre las 4 etapas con su esquema y su `validar=`. La consistencia (RF12 × 3) está en `bitacora/a2_matriz.md`.

| Entrada | Etapa | Prompt | Artefacto | Válida | Intentos | ms | USD | Errores |
|---|---|---|---|---|---|---|---|---|
| RF07 | analizar | qa_analizar.v2 | RF07 · dinero=False · 9 reglas · 3 ambigüedades | ✗ | 2 | 5723 | 0.004438 | datos_prueba[1]: contiene datos personales o datos reales de qa-10; utiliza datos sinteticos o marcadores simbolicos; datos_prueba[2]: contiene datos  |
| RF12 | analizar | qa_analizar.v2 | RF12 · dinero=True · 8 reglas · 4 ambigüedades | ✓ | 1 | 10693 | 0.002547 | — |
| RF12 | casos | qa_casos.v2 | 10 casos · tipos: 8 | ✓ | 1 | 3698 | 0.004115 | — |
| RF12 | revisar | qa_revisar.v2 | cumple_qa08=False · 1 faltantes · 1 hallazgos | ✗ | 2 | 3724 | 0.005216 | cobertura_tipos.positivo reportado como 0 pero el conteo real en casos es 1; casos_faltantes no debe incluir positivo para RF12 |
| RF15 | analizar | qa_analizar.v2 | RF15 · dinero=True · 5 reglas · 3 ambigüedades | ✓ | 1 | 2359 | 0.002032 | — |
| RF15 | casos | qa_casos.v2 | 9 casos · tipos: 8 | ✓ | 1 | 3721 | 0.003988 | — |
| RF15 | revisar | qa_revisar.v2 | cumple_qa08=True · 0 faltantes · 0 hallazgos | ✗ | 2 | 2083 | 0.002839 | cobertura_tipos.limite_exacto reportado como 2 pero el conteo real en casos es 1 |

Flujos completos: 0/3 · etapas válidas al primer intento: 4/7 · errores del proveedor: 0 · costo total: 0.025175 USD
