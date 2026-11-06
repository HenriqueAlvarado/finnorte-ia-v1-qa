# Acuerdos del equipo

> Llénenlo al formar el equipo y actualícenlo en cada entrega. El profesor lo revisa junto con el historial de Git y la coevaluación.

## Datos
| Campo | Valor |
|---|---|
| Equipo | finnorte-ia-v1-qa |
| Variante | v1-qa |
| Repositorio | https://github.com/HenriqueAlvarado/finnorte-ia-v1-qa |
| Canal de comunicación | Discord y WhatsApp |
| Horario fijo de trabajo semanal | 7:30 p.m. a 10:00 p.m. |

## Integrantes y roles
Los roles **rotan en cada entrega**; todos programan.

| Integrante | Usuario de GitHub | Rol Avance 1 | Rol Avance 2 | Rol Final |
|---|---|---|---|---|
| Henrique | HenriqueAlvarado | Integración (`sistema()`, fusión de ramas) | | |
| Luis | oft24 | Evaluación (casos, contrato, configuraciones A–D) | | |
| Caro (Monserrat) | Monsecode | Prompts y flujo (v1/v2, esquemas, reglas) | | |
| Gera | GeraEsc | Documento y evidencia (PDF, bitácoras) | | |

## Dueños de etapa del flujo (A2 · individual)
Cada integrante es dueño de **una** etapa: su prompt v1 y esquema, su validación en código (`validar=`) y su v2 medida.

| Etapa | Nombre en `FLUJO` | Prompt (`prompts/<id>.v1.md`) | Dueño (integrante) | Usuario de GitHub |
|---|---|---|---|---|
| 1 | `analizar` | `prompts/qa_analizar.v1.md` | Gera | GeraEsc |
| 2 | `casos` | `prompts/qa_casos.v1.md` | Caro (Monserrat) | Monsecode |
| 3 | `revisar` | `prompts/qa_revisar.v1.md` | Henrique | HenriqueAlvarado |
| 4 | `pytest` | `prompts/qa_pytest.v1.md` | Luis | oft24 |

## Reglas de trabajo
- Nadie sube directo a `main`: cada integrante trabaja en su rama y abre un pull request. Quien abre el PR no lo fusiona; otro integrante lo revisa y hace el merge. La aprobación formal de GitHub no siempre se usa. En la semana 3, 6 de 11 PR los fusionó su propio autor (#1, #3, #4, #6, #5 y #9) por las prisas de la entrega; desde el #12 la regla se aplica sin excepción.
- Cada pull request dice qué cambió y cómo se probó.
- Las llaves van en `.env`, nunca en el repositorio. Si se filtra una, se revoca en menos de 1 hora (ing-02).
- Si alguien no puede cumplir, lo avisa **antes** de la fecha, no después.

## Decisión de fusión (Avance 1)
| Pieza | Opciones (de quién) | Elegida | Evidencia que la justifica |
|---|---|---|---|
| Buscador (A1) | Los 4 buscadores de la A1 individual (Henrique, Gera, Caro y Luis) | El de Henrique (commit `fa3e909`, `src/finnorte/retrieval.py`), que es el que se integró al flujo | **Comparación cualitativa del equipo, no una medición con datos.** El equipo comparó los 4 buscadores a mano: tres quedaron prácticamente empatados y uno dio un punto menos. Como los empatados eran equivalentes, elegir cualquiera de ellos no cambiaba el resultado: Henrique propuso usar el suyo y el equipo lo aceptó, sin otro criterio de desempate. **Limitación:** no se corrió acierto@3 sobre un conjunto de preguntas común (`evals/` solo tiene la plantilla `a1_plantilla.jsonl`), así que no hay un número que respalde la elección. |
| Flujo (A2) | Cada integrante diseñó y midió su propia etapa por separado (`bitacora/gera/`, `bitacora/monsecode/`, `bitacora/luis/`); no hubo flujos completos alternativos | Un solo `FLUJO` de 4 etapas encadenadas (`analizar` → `casos` → `revisar` → `pytest`) en `src/finnorte/variante.py`, con `FLUJO_V1` para comparar versiones (PR #12) | `bitacora/a2_matriz.md`: RF12 × 3 repeticiones con gemini-3.5-flash, **3 de 3 flujos completos válidos**; todas las etapas válidas al primer intento, salvo `pytest` (2 intentos en la repetición 1). Antes y después del flujo completo: medición A–D (`bitacora/av1_A.json` a `av1_D.json` y `bitacora/av1_notas.md`; 20 casos × 3 repeticiones, gemini-3.1-flash-lite). Prompts v2 (B − A): +0.05 de exactitud, IC 95 % (0.00, 0.12), no concluyente; contexto RAG (C − B): +0.23, IC (0.08, 0.38), concluyente; motor completo (D − A): +0.27, IC (0.12, 0.42). **Limitación:** la matriz del flujo completo usa una sola entrada (RF12). |
| Prompts | Por etapa, la v1 contra la versión más reciente (v2 en `qa_analizar` y `qa_casos`, v3 en `qa_pytest`; `qa_revisar` solo tiene v1 en `main`) | La versión más reciente de cada etapa, que es la que usa el `FLUJO` (`version=None`): `qa_analizar.v2`, `qa_casos.v2`, `qa_revisar.v1` y `qa_pytest.v3` | `qa_casos`: v1 0 de 5 corridas válidas, v2 4 de 5 (`bitacora/monsecode/a2_comparacion_casos.md`). `qa_pytest`: v2 0 de 5, v3 5 de 5 válidas al primer intento (`bitacora/luis/medicion_v2_v3/`). `qa_analizar`: v1 3 de 3 solicitudes válidas; v2 1 de 3, con 2 errores del proveedor (HTTP 503 y 429), por lo que la comparación no es concluyente (`bitacora/gera/comparacion_v1_v2.json`). Mediciones con gemini-3.1-flash-lite (`casos` y `pytest`) y gemini-3.5-flash (`analizar`). En el flujo completo, el paso de prompts v1 a v2 (A contra B de la medición A–D) mejora la exactitud solo +0.05 y no es concluyente. |

## Registro de decisiones importantes
| Fecha | Decisión | Alternativas descartadas | Por qué |
|---|---|---|---|
| 2026-11-05 | En operaciones de dinero, `qa_casos` y `qa_revisar` exigen los 8 tipos de caso, incluido `limite` | Dar por cubierto `limite` con `limite_exacto` o `un_centavo_arriba` (regla de la v1 de `qa_casos`) | La medición mostró que con la regla v1 las 5 corridas quedaban con tipos faltantes según `qa_revisar` (PR #7, `bitacora/monsecode/`) |
| 2026-11-05 | Medir con `gemini-3.1-flash-lite` y `gemini-3.5-flash` | `gemini-2.5-flash`, el valor por defecto del andamio | Devuelve 404 para cuentas nuevas, y la cuota gratuita se agota con pocas llamadas al día (HTTP 429) |
| 2026-11-06 | El mensaje de error de `validar=` de `qa_casos` no incluye ningún fragmento de datos reales de qa-10 | Mostrar los primeros 12 caracteres del dato (versión anterior) | Henrique detectó que el fragmento quedaba en `trazas.jsonl` y se reenviaba al modelo en el reintento; corregido en el PR #17, con una prueba que lo verifica |
