# Bitácora de uso de IA

> Obligatoria en todas las entregas. Una fila por uso relevante de una herramienta de IA (chat, asistente de código, generador).
> La IA es una herramienta permitida; ocultarla no lo es. Se califica la honestidad y la calidad de la validación, no si la usaste.

| Fecha | Entrega | Herramienta y modelo | Para qué la usé | Prompt (resumen o enlace) | Qué acepté | Qué cambié o rechacé y por qué | Cómo lo validé |
|---|---|---|---|---|---|---|---|
| 2026-10-16 | A1 | Ejemplo: asistente de código | Ejemplo: generar el esqueleto de la función de normalización | "Escribe una función en numpy que…" | La estructura del ciclo | Usaba `/` sin cuidar la norma cero; lo corregí | Prueba `test_normalizar_vector_cero` |
| 2026-11-05 | A2 · etapa 2 (qa_casos) | Claude Code (Sonnet 5.5) | Redactar el borrador del prompt qa_casos v1, su esquema JSON, la regla de validación `casos_cubren_qa08` y sus pruebas | "Escribe mi etapa 2 (qa_casos) siguiendo el contrato de campos del equipo y la guía qa-08" | La estructura del prompt, el esquema con enum de tipos y la regla en código | Mantuve los nombres de campo del contrato del equipo sin renombrar; acepté un campo opcional `fuente` que la IA propuso. Los commits, el push y el PR los hice yo | `pytest` (7 pruebas propias), una corrida real con Gemini sobre RF12 y el PR #2, que unió Henrique |
| 2026-11-05 | A2 · etapa 2 (qa_casos) | Claude Code (Sonnet 5.5) | Medir el v1 con el flujo analizar → casos y proponer la mejora v2 | "Mide mi etapa con la salida real de Gera y propón qué mejorar" | El prompt `qa_casos.v2.md` y la regla que exige los 8 tipos en operaciones de dinero | La medición reveló que `fuente` salía como "N/A" y rompía el esquema, y que nunca salía el tipo `limite` (qa_revisar sí lo exige). Se midió con gemini-3.1-flash-lite porque gemini-3.5-flash agotó la cuota | 5 corridas con las mismas entradas y el mismo modelo: 0 de 5 válidas en v1 y 4 de 5 en v2; `pytest` 63 passed; PR #7 |
