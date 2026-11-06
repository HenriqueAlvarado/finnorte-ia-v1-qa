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
| Flujo (A2) | | | validaciones y consistencia en `bitacora/`: |
| Prompts | | | |

## Registro de decisiones importantes
| Fecha | Decisión | Alternativas descartadas | Por qué |
|---|---|---|---|
| | | | |
