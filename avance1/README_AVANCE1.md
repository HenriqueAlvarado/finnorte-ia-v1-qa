# Avance 1 · Arranque del proyecto y motor de tu variante

> Esta carpeta es el **andamio del Avance 1**: la introducción al proyecto en equipo. Te lleva de «nos acaban de asignar una variante» a «tenemos un motor que mide su propia calidad».
> Entrega: **viernes 6 de noviembre, 23:59** · 15 % · etiqueta `avance1`. La **A2 (individual)** se entrega el mismo día: cada integrante es dueño de una etapa del flujo y sube su página «Mi etapa» a Canvas.

## Qué hay aquí
| Archivo | Para qué |
|---|---|
| `README_AVANCE1.md` | Este plan: semana por semana, paso a paso y la lista final |
| `equipo.md` | Acuerdos del equipo: roles, horarios, reglas de Git y decisiones. Llénalo la primera semana |
| `contrato_calidad.plantilla.yaml` | Plantilla del contrato con sugerencias por variante. Cópiala a la raíz como `contrato_calidad.yaml` |
| `casos_plantilla.jsonl` | Esqueleto de los 20 casos de evaluación con la mezcla de tipos que se pide |
| `Plantilla_Documento_Avance1.docx` | El documento técnico con sus 11 secciones y lo que debe ir en cada una |
| `../guia/av1_configuraciones.py` | Mide tus 4 configuraciones (A, B, C y D) contra el contrato |

---

## El plan en 3 semanas

### Semana 1 (13–18 oct) · Equipo, repositorio y buscador
1. **Viernes 16 · equipo cerrado.**
   - Llenen `equipo.md`: roles rotativos, canal de comunicación y horario de trabajo.
   - Regla de Git: nadie sube directo a `main`.
2. **Repositorio único del equipo.**
   - Una persona crea el repositorio en GitHub desde el zip del andamio (`git init`, primer commit, `git push`) y agrega a los demás como colaboradores.
   - En *Settings → Branches* protejan `main`: los cambios entran por pull request con al menos una aprobación.
   - En *Settings → Secrets → Actions* agreguen `GEMINI_API_KEY` (o `GROQ_API_KEY`).
3. **`variante.py`:** cambien `VARIANTE = "v?-cambia-esto"` por la suya. Ejemplo: `"v3-soporte"`.
4. **Exploren el corpus de su variante.** Cada integrante lee 2 o 3 documentos de `corpus/<variante>/` y lo comparte en 5 minutos.
   - Busquen la **trampa** (VARIANTES.md): datos personales, un documento confidencial y, en algunas variantes, una versión obsoleta.
5. **A1 individual:** cada quien construyó su buscador en su repositorio individual; para el Avance 1 elijan el mejor (paso 2 de la semana 3).

### Semana 3 (29 oct – 6 nov) · Flujo, motor, controles y medición (A2 fusionada)
1. **Hoy · dueños de etapa** (anótenlos en `equipo.md`):
   - diseñen juntos las 4 etapas (tabla de VARIANTES.md): entradas, salidas, esquema y regla de negocio de cada una;
   - cada integrante es **dueño de una etapa** (esa es su A2 individual).
2. **Decisión de fusión** (en `equipo.md`): ¿qué buscador de la A1 se queda? El criterio son **datos** (acierto@3), no gustos.
3. **Laboratorio 2 (manual Lab 2):** implementen `Pipeline.ejecutar` (`test_a2_*` en verde) y definan `FLUJO` con sus 4 etapas y `validar=`.
4. **Laboratorio 3 (manual Lab 3):** controles (`verificar_citas`, `debe_abstenerse`) e **implementen `sistema()`** en `src/finnorte/variante.py` siguiendo los 6 pasos. El caso guía (`asistente.py`) es el modelo.
5. **20 casos** en `evals/<variante>.jsonl` partiendo de `casos_plantilla.jsonl`: 12 `normal`, 4 `fuera`, 4 `limite` o `adversarial`.
6. **Contrato:** copien `avance1/contrato_calidad.plantilla.yaml` a `contrato_calidad.yaml` y fijen metas **justificadas**.
7. **Medición:** `pytest -q` y `python guia/av1_configuraciones.py --casos evals/<variante>.jsonl --rep 3`.
8. **Cada integrante:** la v2 de su etapa con el antes y después medido.
9. **Documento técnico:** llenen `Plantilla_Documento_Avance1.docx`. Cada afirmación lleva un archivo de `bitacora/` como evidencia.
10. **Viernes 6 · entrega (23:59):**
    - `git tag avance1 && git push --tags`;
    - el PDF del equipo a Canvas;
    - cada integrante sube su página **«Mi etapa»** (A2) y llena la coevaluación.

---

## Los 6 pasos de `sistema()` (resumen)
```
entrada ──► 1 recuperar (A1) ──► 2 controles de entrada ──► 3 flujo (A2) con contexto
        ──► 4 respuesta + fuentes ──► 5 verificar citas ──► 6 sanear ──► salida
```

| Paso | Pregunta que responde | Función del andamio |
|---|---|---|
| 1 | ¿Qué dice el corpus sobre esto? | `indice().buscar(texto, k)` |
| 2 | ¿Hay algo confidencial? ¿Hay suficiente contexto? | `controles.filtrar_clasificacion`, `controles.debe_abstenerse` |
| 3 | ¿Qué artefacto produce mi variante? | `FLUJO.ejecutar({...})` |
| 4 | ¿Qué le muestro al usuario y con qué fuentes? | Tu código |
| 5 | ¿Citó algo que no recuperó? | `controles.verificar_citas` |
| 6 | ¿Hay URLs, imágenes o datos que no deben salir? | `controles.sanear_salida` |

La función recibe `config` para encender y apagar piezas. Así `guia/av1_configuraciones.py` mide cuánto aporta cada una: A, B, C y D.

## Los 20 casos de evaluación
| Tipo | Cuántos | Qué prueban | Campo clave en `esperado` |
|---|---|---|---|
| `normal` | 12 | La tarea típica de tu usuario | `contiene` (datos exactos) y `fuentes` |
| `fuera` | 4 | Algo que tu sistema **no** debe responder | `debe_abstenerse: true` |
| `limite` / `adversarial` | 4 | Bordes, entradas ambiguas, órdenes escondidas, la trampa de tu corpus | `no_contiene` (lo que nunca debe salir) |

Reglas:
- Los casos `normal` usan **paráfrasis**, no el texto literal del documento.
- Al menos un caso adversarial intenta sacar la **trampa** de su corpus.
- El profesor tiene un **set oculto** de 15 casos parecidos para la presentación. Si solo pasan los suyos, sobreajustaron.

## Lista de entrega
- [ ] `VARIANTE` configurada; `sistema()` corre los 20 casos sin errores.
- [ ] `pytest -q` en verde (incluye `test_av1_*`).
- [ ] `evals/<variante>.jsonl` con 20 casos (12 / 4 / 4).
- [ ] `contrato_calidad.yaml` con metas justificadas en el documento.
- [ ] Tabla A, B, C, D con `--rep 3` o más y los intervalos (`bitacora/av1_*.json`).
- [ ] Prompts v1 y v2 versionados, con `cambios:` explicado.
- [ ] `equipo.md` con roles y la **decisión de fusión** justificada.
- [ ] `ai_log.md` del equipo actualizado.
- [ ] Documento técnico en PDF (8 a 12 páginas) con las 11 secciones.
- [ ] Etiqueta `avance1` en GitHub y commits de **todos** los integrantes.
- [ ] Coevaluación enviada.
