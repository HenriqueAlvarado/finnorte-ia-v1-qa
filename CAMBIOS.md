# Cambios del andamio

## 29 de octubre de 2026 · Laboratorios 2 y 3, Avance 1 y A2 fusionada
- **`controles.opcional(funcion, *args, por_defecto=...)`:** te deja usar los controles del Avance 2 (`filtrar_clasificacion` y `sanear_salida`) sin que el motor truene mientras no los implementas. `asistente.py` y los comentarios de `variante.py` ya lo usan.
- **`evaluacion.evaluar`:** cuenta las ejecuciones en que tu sistema falló (`errores_sistema`) y guarda los primeros errores. `guia/av1_configuraciones.py` te avisa si tu `sistema()` truena y se detiene si falla en todos los casos. También revisa que tus casos usen los tipos `normal`, `fuera`, `limite` y `adversarial`.
- **Tipos de los casos de evaluación:** `evals/*.jsonl` usa solo esos 4 tipos. El detalle va en el campo opcional `subtipo` (vigencia, supuesto, estilo…).
- **`guia/s2_flujo_cambios.py`:**
  - modo de demostración sin red (`LLM_PROVIDER=fake`);
  - `--plan-version N` para medir la v1 contra la v2;
  - la matriz se guarda por versión (`s2_trazabilidad_plan_vN.json`) con la versión de cada prompt y los errores.
- **Scripts de `guia/`:** si falta implementar una función, muestran un aviso claro en lugar del error largo.
- **Encabezado de los prompts:** un comentario es « # » con espacios. Un `#` pegado (por ejemplo «caso #3») ya no corta el texto de `cambios:`.
- **`tests/test_a2_pipeline.py`:** nueva prueba de una regla de negocio en código (`validar=`).
- **`avance1/`:**
  - fecha de entrega: viernes 6 de noviembre;
  - plan actualizado con la A2 fusionada;
  - tabla de dueños de etapa en `equipo.md`.
- **`VARIANTES.md`:** aclara que las etapas de código (`ast`, regex, linter) van como preprocesamiento o dentro de `validar=`.
