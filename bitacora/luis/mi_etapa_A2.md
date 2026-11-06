# A2 · Mi etapa: pytest (qa_pytest)

Luis (oft24) · Equipo 1 · Variante v1-qa · Repositorio: github.com/HenriqueAlvarado/finnorte-ia-v1-qa

## 1. Mi etapa

Soy dueño de la etapa 4 del flujo analizar → casos → revisar → pytest. Recibe la salida de la etapa casos (`usa=["casos"]`) y entrega un JSON con `nombre_archivo` y `codigo_pytest`. El esquema es estricto (`additionalProperties: false`).

Con esto, QA recibe un archivo pytest que compila y corre, con un test por caso. Cada test indica de qué requisito (`@RF12`) y de qué regla de negocio sale.

En el flujo del equipo la etapa está conectada así:

```python
Etapa("pytest", "qa_pytest", usa=["casos"], validar=pytest_compila_y_cubre)
```

`FLUJO` usa la v3 y `FLUJO_V1`, la v1.

## 2. Mi prompt

La v1 (`prompts/qa_pytest.v1.md`) solo tiene rol y formato: "Eres QA de FinNorte. Conviertes casos de prueba en Gherkin (Dado / Cuando / Entonces) a un archivo pytest en Python que compile", más el JSON de salida. No dice cómo nombrar los tests ni qué hacer si falta información, y eso se vio al medirla.

La v2 agrega:

- **Reglas explícitas:** "Nombre: test_ + id_caso en minúsculas (CP-RF12-03 → test_cp_rf12_03)", y un docstring con `id_caso`, `@RFxx`, tipo y `regla_citada`.
- **Restricciones técnicas:** montos con `Decimal`, nunca `float`, y solo pytest y la biblioteca estándar.
- **Qué hacer si falta información:** "Si el «entonces» contiene SUPUESTO, conserva la palabra SUPUESTO… no inventes el valor".

La v3 fija cómo se prueba al sistema: `resultado = sistema.ejecutar("accion", **datos)`, con asserts sobre lo que regresa. También pide los datos de prueba como marcadores (`<CLABE_VALIDA_1>`).

## 3. Mi validación en código

`pytest_compila_y_cubre` (`src/finnorte/etapa_pytest.py`) revisa 9 reglas:

1. el código compila (`ast.parse`);
2. hay un test por cada `id_caso`;
3. cada test tiene un assert;
4. cada test cita su regla;
5. no aparecen los datos de qa-10;
6. solo importa pytest y la biblioteca estándar;
7. el nombre del archivo corresponde al RF;
8. el assert revisa un resultado de `sistema`;
9. no hay datos con forma de correo, CLABE o teléfono.

Es código porque el modelo no puede comprobar que su propio archivo compila ni contar sus funciones. `ast` lo hace siempre igual y sin costo. Los errores vuelven al modelo en el reintento.

Casos reales en que se disparó (primer intento):
- v1: `CP-RF12-01: falta la función test_cp_rf12_01` (`bitacora/luis/a2_matriz_pytest_v1.md`);
- v2: `test_cp_rf12_01: el assert no revisa ningún resultado de sistema` (`bitacora/luis/medicion_v2_v3/a2_matriz_pytest_v2.md`).

## 4. Evidencia de ejecución

Traza de la etapa (`bitacora/luis/medicion_v2_v3/a2_trazas_pytest.jsonl`):

```json
{"ts": "2026-11-05T20:59:32", "etiqueta": "v1-qa/pytest/qa_pytest.v3", "modelo": "gemini-3.1-flash-lite", "tokens_entrada": 1392, "tokens_salida": 1129, "latencia_ms": 6073.9, "costo_usd": 0.00324}
```

Fila de mi etapa en la matriz del equipo (`bitacora/a2_matriz.md`, RF12, gemini-3.5-flash):

| Rep | Etapa | Prompt | Artefacto | Válida | Intentos | ms | US$ |
|---|---|---|---|---|---|---|---|
| 1 | pytest | qa_pytest.v3 | test_rf12.py · 8 tests · 194 líneas | ✓ | 2 | 40984 | 0.010768 |

## 5. Consistencia (RF12, 3 repeticiones)

- **v1:** falló las 3 veces de la misma forma. Los 8 tests salieron con nombres distintos de `test_cp_rf12_nn`, porque el prompt no lo indica.
- **v2 (con las reglas 1 a 7) y v3 (con las 9):** válidas las 3 veces al primer intento, con los 8 casos cubiertos y el mismo nombre de archivo. Las reglas explícitas quitan las decisiones que el modelo tomaba distinto en cada corrida.
- **Matriz del equipo:** con la v3, la etapa fue válida en las 3 repeticiones. El archivo midió 178 a 195 líneas.

## 6. Mi mejora medida

Las dos versiones reciben los mismos casos de entrada (`bitacora/luis/a2_casos_entrada.json`): RF07, RF12 × 3 y RF15. Modelo `gemini-3.1-flash-lite`.

**v1 → v2**, con las reglas 1 a 7. Fallos de la v1: no nombraba los tests por caso (24 veces), no citaba la regla (14) y escribía `assert True` en 34 de 38 tests. `cambios:` de la v2: "fija el nombre de cada test, exige @RFxx y regla citada por test, Decimal para montos y un fixture que omite (skip) mientras no haya sistema real".

**v2 → v3**, con las reglas 1 a 9. Fallos de la v2: ninguno de sus 38 tests llamaba a `sistema` y el archivo de RF07 traía correos sintéticos.

| | v1 | v2 | v3 |
|---|---|---|---|
| Válidas al 1.er intento (reglas 1 a 7) | 0/5 | 5/5 | |
| Válidas al 1.er intento (reglas 1 a 9) | | 0/5 | 5/5 |
| Errores de validación en el 1.er intento | 38 | 0 con reglas 1 a 7; 39 con 1 a 9 | 0 |
| Tests que llaman a `sistema` | | 0/38 | 38/38 |
| Llamadas al modelo | 10 | 5 | 5 |

Evidencia: `bitacora/luis/a2_matriz_pytest_v1.md`, `a2_matriz_pytest_v2.md`, `bitacora/luis/medicion_v2_v3/`. Los 38 tests de la v3 se recolectan con pytest y salen *skipped* mientras no exista el sistema real.

## 7. Mis commits

PR #11 (etapa 4) y PR #20 (evaluación). En el repo: `git log --author="oft24" --oneline`.

Uso de IA: usé un asistente de código para revisar la etapa y preparar la medición. El detalle está en `ai_log.md`.
