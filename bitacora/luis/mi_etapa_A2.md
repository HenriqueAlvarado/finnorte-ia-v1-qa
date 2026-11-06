# A2 · Mi etapa — Etapa 4 · qa_pytest

**Integrante:** Luis (GitHub: oft24) · **Equipo:** 1 · **Variante:** v1-qa (Requisitos → pruebas)
**Pull request:** https://github.com/HenriqueAlvarado/finnorte-ia-v1-qa/pull/11 (rama `Luis-H`)
**Medición:** 2026-11-05 · `gemini / gemini-3.1-flash-lite` · temperatura 0.2 · `python guia/a2_etapa4_pytest.py`

## 1. Mi etapa
| Campo | Valor |
|---|---|
| Nombre en `FLUJO` | `pytest` |
| Prompt | `prompts/qa_pytest.v1.md` y `prompts/qa_pytest.v2.md` |
| Recibe (`usa=`) | `["casos"]`: la lista de la etapa 2 (`id_caso`, `titulo`, `tipo`, `dado`, `cuando`, `entonces`, `regla_citada`) |
| Entrega (esquema) | `nombre_archivo` (`^test_[a-z0-9_]+\.py$`) y `codigo_pytest`, con `additionalProperties: false` |
| Conexión | `Etapa("pytest", "qa_pytest", usa=["casos"], validar=pytest_compila_y_cubre)` |

**Cómo ayuda:** convierte los casos Dado/Cuando/Entonces en un archivo pytest que compila y corre. Cada test se rastrea a su caso, a su requisito (`@RFxx`) y a la regla de negocio de la que sale.

## 2. Mi prompt (técnicas)
- **v1** (línea base): solo el rol ("Eres QA de FinNorte. Conviertes casos de prueba en Gherkin… a un archivo pytest en Python que compile") y el formato JSON.
- **v2** agrega:
  - **restricciones técnicas:** "Montos de dinero con decimal.Decimal, nunca float"; "Nada de imports fuera de pytest y la biblioteca estándar".
  - **reglas explícitas:** "Nombre: test_ + id_caso en minúsculas… (CP-RF12-03 → test_cp_rf12_03)"; un docstring con `id_caso`, `@RF12`, tipo y `regla_citada`; al menos un assert.
  - **qué hacer si falta información:** "Si el «entonces» contiene SUPUESTO, conserva la palabra SUPUESTO en el docstring; no inventes el valor".
  - **formato JSON:** el objeto exacto de salida, con un ejemplo.

## 3. Mi validación en código (`pytest_compila_y_cubre`, `src/finnorte/etapa_pytest.py`)
Revisa 7 reglas:
1. El código compila (`ast.parse`).
2. Hay un `test_cp_rfxx_nn` por cada `id_caso`.
3. Cada test tiene un `assert` o un `pytest.raises`.
4. Cada test cita su `regla_citada`.
5. No aparecen los datos de qa-10, en ningún formato.
6. Solo importa pytest y la biblioteca estándar.
7. `nombre_archivo` corresponde al RF de los casos.

**Por qué es código y no prompt:** el modelo no puede comprobar que su código compila ni contar sus funciones con certeza. `ast` lo hace de forma determinista y sin costo, y sus errores vuelven al modelo en el reintento.

**Casos reales en que se disparó** (v1, 1.er intento, `bitacora/luis/a2_matriz_pytest_v1.md`):
- `CP-RF12-01: falta la función test_cp_rf12_01`. La v1 nombró los tests a su manera.
- `test_cp_rf12_01: no cita la regla REG-RF12-01`. El test no dice de qué regla sale.

En total, la validación devolvió **38 errores** en los 5 primeros intentos de la v1: 24 de "falta la función" y 14 de "no cita la regla".

## 4. Evidencia de ejecución
Extracto de `bitacora/luis/a2_trazas_pytest.jsonl` (copiado de `bitacora/trazas.jsonl`):
```json
{"ts": "2026-11-05T19:05:58", "tipo": "llm", "etiqueta": "v1-qa/pytest/qa_pytest.v1", "proveedor": "gemini", "modelo": "gemini-3.1-flash-lite", "tokens_entrada": 812, "tokens_salida": 550, "latencia_ms": 3601.9, "costo_usd": 0.001619, "json_valido": true}
```
Fila de mi etapa en la matriz v2 (`bitacora/luis/a2_matriz_pytest_v2.md`):

| Entrada | Rep | Prompt | Artefacto (final) | Válida | Intentos | 1.er intento | Errores |
|---|---|---|---|---|---|---|---|
| RF12 | 1 | qa_pytest.v2 | test_rf12.py · 8/8 casos con su test | ✓ | 1 | ✓ | — |

## 5. Consistencia (RF12 × 3)
- **v1:** `[(False, 8, 'test_rf12.py')] × 3`. Falló las 3 veces y siempre igual: los 8 tests con un nombre distinto de `test_cp_rf12_nn` (8 errores de "falta la función" en cada repetición). Es un fallo consistente porque el prompt v1 no dice cómo nombrar los tests. En una corrida anterior la v1 sí varió entre repeticiones: en una nombró bien los tests pero sin citar la regla.
- **v2:** `[(True, 8, 'test_rf12.py')] × 3`. Válida al primer intento las 3 veces, con los 8 casos cubiertos y el mismo nombre de archivo. Las reglas explícitas quitan las decisiones libres que variaban.

## 6. Mi mejora v2 medida
**Qué falló en la v1:**
- no seguía un nombre por caso (24 veces "falta la función");
- no citaba la regla (14 veces);
- escribió `assert True` en 34 de sus 38 tests, que no prueban nada.

**`cambios:` de la v2:** "v2 fija el nombre de cada test, exige @RFxx y regla citada por test, Decimal para montos y un fixture que omite (skip) mientras no haya sistema real".

**Antes y después.** Los mismos casos de entrada (`a2_casos_entrada.json`), la misma validación y 5 corridas por versión:

| Métrica | v1 | v2 |
|---|---|---|
| Válidas al 1.er intento | **0/5** | **5/5** |
| Válidas tras el reintento | 0/5 | 5/5 |
| Errores de validación (1.er intento) | 38 | 0 |
| Llamadas al modelo | 10 | 5 |
| Costo total (US$) | 0.0194 | 0.0175 |
| Latencia promedio por llamada (ms) | 6 130 | 6 506 |

La v2 genera casi el doble de texto por llamada (1 228 tokens frente a 635), pero nunca reintenta. Por eso cuesta menos y tarda la mitad por archivo.

Las dos corridas anteriores dieron lo mismo: la v1 con 0/5 al primer intento (y 0/5 y 1/5 tras el reintento), la v2 con 5/5.

**Los archivos de la v2 corren:** los 38 tests de los 5 archivos (`bitacora/luis/generados/v2/`) se recolectan con pytest y salen *skipped*, como pide el prompt mientras no exista el sistema.

**Limitaciones que encontré (siguiente mejora):**
- **Ningún test usa a `sistema`** (0 de 38): los asserts comparan valores locales, así que todavía no pueden fallar. Arreglarlo requiere una v3 y una regla 8 en código: cada assert debe revisar un resultado obtenido de `sistema`.
- **El archivo de RF07 trae correos sintéticos**, y el detector de PII del equipo los marca como fuga. Hay que acordar marcadores como `<CORREO_SINTETICO_1>` (ver el PR #10).

## 7. Mis commits
- PR: https://github.com/HenriqueAlvarado/finnorte-ia-v1-qa/pull/11
- `git log --author="oft24" --oneline`

**Uso de IA:** usé un asistente de código para revisar la etapa y preparar la medición. El detalle está en `ai_log.md`.
