# A2 · Mi etapa — Etapa 4 · qa_pytest (borrador)

**Integrante:** Luis (GitHub: oft24) · **Equipo:** 1 · **Variante:** v1-qa (Requisitos → pruebas)
**Rama:** `Luis-H` · **Repositorio:** https://github.com/HenriqueAlvarado/finnorte-ia-v1-qa

> Borrador. Lo marcado **[PENDIENTE]** se llena con la salida de `python guia/a2_etapa4_pytest.py` corrido con Gemini.

## 1. Mi etapa
| Campo | Valor |
|---|---|
| Nombre en `FLUJO` | `pytest` |
| Prompt | `prompts/qa_pytest.v1.md` y `prompts/qa_pytest.v2.md` |
| Recibe (`usa=`) | `["casos"]`: la lista de casos de la etapa 2 (`id_caso`, `titulo`, `tipo`, `dado`, `cuando`, `entonces`, `regla_citada`) |
| Entrega (esquema) | `nombre_archivo` (patrón `^test_[a-z0-9_]+\.py$`) y `codigo_pytest`, con `additionalProperties: false` |
| Conexión | `Etapa("pytest", "qa_pytest", usa=["casos"], validar=pytest_compila_y_cubre)` |

**Cómo ayuda:** convierte los casos Dado/Cuando/Entonces en un archivo pytest que compila y que QA puede ejecutar. Cada test se rastrea a su caso (`id_caso`), a su requisito (`@RFxx`) y a la regla de la que sale (`regla_citada`).

## 2. Mi prompt v1 y técnicas
- **v1** (línea base): rol ("Eres QA de FinNorte…"), formato JSON con un ejemplo y una función por caso.
- **v2** (versión mejorada): agrega las técnicas que la rúbrica busca:
  - **rol:** "Eres QA de FinNorte. Conviertes casos de prueba en Gherkin…"
  - **restricciones técnicas:** montos con `decimal.Decimal`, nunca `float`; solo pytest y la biblioteca estándar.
  - **reglas explícitas:** el nombre `test_cp_rf12_03`, un docstring con `id_caso`, `@RFxx`, tipo y `regla_citada`, y al menos un assert.
  - **qué hacer si falta información:** "Si el «entonces» contiene SUPUESTO, conserva la palabra SUPUESTO… no inventes el valor" y "Usa solo los datos de los casos".
  - **formato JSON:** el objeto exacto que debe devolver.

## 3. Mi validación en código (`pytest_compila_y_cubre`)
Revisa 7 reglas en `src/finnorte/etapa_pytest.py`:
1. El código compila (`ast.parse`). Es el control obligatorio de la variante.
2. Hay un `test_cp_rfxx_nn` por cada `id_caso` de la etapa 2.
3. Cada test tiene un `assert` o un `pytest.raises`.
4. Cada test cita su `regla_citada`.
5. No aparecen los datos de qa-10, tampoco con otro formato (por ejemplo `55-5550-7788`).
6. Solo importa pytest y la biblioteca estándar.
7. `nombre_archivo` corresponde al requisito (`CP-RF12-nn` → `test_rf12.py`).

**Por qué es código y no prompt:** el modelo no puede comprobar que su propio código compila ni contar sus funciones con certeza. `ast` sí, de forma determinista y sin costo. Los errores se le devuelven al modelo en el reintento.

**Caso real en que se disparó:** [PENDIENTE: copiar de `a2_matriz_pytest_v1.md`, columna «Errores (1.er intento)»]
- Prueba de plomería (no cuenta como evidencia): un `nombre_archivo` igual a `test_rf07.py` con casos `CP-RF12-*` dispara la regla 7, y el reintento lo corrige.

## 4. Evidencia de ejecución
- **Extracto de `bitacora/trazas.jsonl`:** [PENDIENTE] las filas con `etiqueta = v1-qa/pytest/qa_pytest.v1` y `.v2`, con su `modelo` y su `ts`.
- **Fila de mi etapa en la matriz:** [PENDIENTE] de `bitacora/luis/a2_matriz_pytest_v2.md`.

## 5. Consistencia (RF12 × 3)
[PENDIENTE] la línea «Consistencia» de cada matriz y su explicación (temperatura 0.2, número de tests, nombre del archivo).

## 6. Mi mejora v2 medida
- **Qué falló en v1:** [PENDIENTE]
- **`cambios:` de la v2:** "v2 fija el nombre de cada test, exige @RFxx y regla citada por test, Decimal para montos y un fixture que omite (skip) mientras no haya sistema real".
- **Antes y después:** [PENDIENTE] válidas al primer intento v1 = _/5 frente a v2 = _/5, y reglas disparadas v1 = _ frente a v2 = _.
- **Método:** las dos versiones reciben **los mismos casos** (congelados en `bitacora/luis/a2_casos_entrada.json`) y la misma validación. La diferencia se atribuye solo al prompt.

## 7. Mis commits
- Rama `Luis-H`: https://github.com/HenriqueAlvarado/finnorte-ia-v1-qa/commits/Luis-H
- `git log --author="oft24" --oneline`

**Uso de IA:** Claude Code me ayudó a redactar y revisar la etapa. El detalle está en `ai_log.md`.
