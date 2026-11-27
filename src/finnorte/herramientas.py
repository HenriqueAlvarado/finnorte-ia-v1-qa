"""Agente con herramientas (T10): el modelo PROPONE una acción en JSON; tu código decide y la ejecuta.

Funciona igual con cualquier proveedor porque no depende del "function calling" nativo:
el modelo responde
  {"accion": "usar", "herramienta": "nombre", "argumentos": {...}, "razon": "..."}
o
  {"accion": "responder", "respuesta": "...", "fuentes": [...]}

Reglas que el código hace cumplir (no el modelo):
- Solo herramientas registradas; argumentos validados contra su esquema.
- Herramientas marcadas `sensible=True` requieren confirmación humana.
- Máximo de pasos para evitar bucles; todo queda en la bitácora.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

import jsonschema

from . import llm, trazas


@dataclass
class Herramienta:
    nombre: str
    descripcion: str
    esquema: dict                      # JSON Schema de los argumentos
    funcion: Callable[..., Any]
    sensible: bool = False             # requiere confirmación humana


@dataclass
class Paso:
    n: int
    propuesta: dict
    resultado: Any = None
    estado: str = ""                   # ejecutada | rechazada | invalida | respuesta | sin_confirmar


@dataclass
class ResultadoAgente:
    respuesta: str
    fuentes: list
    pasos: list[Paso] = field(default_factory=list)
    terminado: bool = True


def _catalogo(herrs: dict[str, Herramienta]) -> str:
    return "\n".join(f"- {h.nombre}: {h.descripcion}. Argumentos (JSON Schema): {json.dumps(h.esquema, ensure_ascii=False)}"
                     + (" [SENSIBLE: requiere confirmación]" if h.sensible else "") for h in herrs.values())


SISTEMA_AGENTE = """Eres un asistente de ingeniería de FinNorte que resuelve tareas en pasos.
En cada turno devuelve SOLO un JSON con una de dos formas:
{{"accion": "usar", "herramienta": "<nombre>", "argumentos": {{...}}, "razon": "<por qué>"}}
{{"accion": "responder", "respuesta": "<respuesta final>", "fuentes": ["<id>", ...]}}
Herramientas disponibles:
{catalogo}
No inventes herramientas ni resultados. Si una herramienta falla, decide si reintentar o responder con lo que tienes."""


def ejecutar_agente(tarea: str, herramientas: list[Herramienta], confirmar: Callable[[Herramienta, dict], bool] | None = None,
                    max_pasos: int = 5, contexto: str = "") -> ResultadoAgente:
    """Mi ejecutor de A4 (mismo contrato que caso_guia/agente_ref.py, sin el guion simulado:
    siempre llama a finnorte.llm.generar, así que en pruebas basta con fijar llm.fake.responder).

    En cada paso: el modelo propone JSON; valido el esquema de los argumentos con jsonschema;
    detecto repetición exacta (misma herramienta + mismos argumentos) para no hacer bucles;
    si la herramienta es sensible pido confirmación (confirmar) y solo ejecuto si regresa True
    (False = rechazada, None = pendiente de una confirmación posterior, p. ej. vía API en dos pasos).
    """
    herrs = {h.nombre: h for h in herramientas}
    sistema = SISTEMA_AGENTE.format(catalogo=_catalogo(herrs))
    historial: list[dict] = []
    pasos: list[Paso] = []
    vistos: set[tuple[str, str]] = set()
    mensaje = f"Tarea: {tarea}" + (f"\n\nContexto:\n{contexto}" if contexto else "")
    for n in range(1, max_pasos + 1):
        r = llm.generar(mensaje, sistema, json=True, historial=historial, etiqueta=f"v1qa/agente/paso{n}")
        prop = r.datos if isinstance(r.datos, dict) else {}
        texto = r.texto
        historial += [{"rol": "user", "texto": mensaje}, {"rol": "model", "texto": texto}]
        paso = Paso(n, prop)
        pasos.append(paso)

        if prop.get("accion") == "responder":
            paso.estado = "respuesta"
            trazas.registrar("agente_v1qa", paso=n, estado=paso.estado)
            return ResultadoAgente(str(prop.get("respuesta", "")), list(prop.get("fuentes", [])), pasos)

        h = herrs.get(prop.get("herramienta", ""))
        if prop.get("accion") != "usar" or h is None:
            paso.estado = "invalida"
            mensaje = f"Acción inválida. Usa una herramienta de la lista {list(herrs)} o responde. Recibí: {texto[:300]}"
        else:
            args = prop.get("argumentos", {}) or {}
            errores = [e.message for e in jsonschema.Draft202012Validator(h.esquema).iter_errors(args)]
            firma = (h.nombre, json.dumps(args, sort_keys=True, ensure_ascii=False))
            if firma in vistos:
                paso.estado = "repetida"
                mensaje = f"Ya ejecutaste {h.nombre} con esos mismos argumentos. Usa ese resultado o responde."
            elif errores:
                paso.estado = "invalida"
                mensaje = f"Argumentos inválidos para {h.nombre}: {errores[:3]}"
            elif h.sensible and (decision := (confirmar(h, args) if confirmar else False)) is not True:
                paso.estado = "pendiente" if decision is None else "rechazada"
                mensaje = (f"{h.nombre}({args}) quedó PENDIENTE de confirmación humana. No la repitas; responde avisando que espera autorización."
                           if decision is None else
                           f"La persona NO confirmó {h.nombre}({args}). No la ejecutes; responde explicando qué se necesita.")
            else:
                vistos.add(firma)
                try:
                    paso.resultado = h.funcion(**args)
                except Exception as e:   # la falla de la herramienta vuelve al modelo como observación, no tumba el agente
                    paso.resultado = f"ERROR: {e}"
                paso.estado = "ejecutada"
                mensaje = f"Resultado de {h.nombre}: {json.dumps(paso.resultado, ensure_ascii=False, default=str)[:3000]}"
        trazas.registrar("agente_v1qa", paso=n, herramienta=prop.get("herramienta"), estado=paso.estado)
    return ResultadoAgente("No pude completar la tarea en el número máximo de pasos.", [], pasos, terminado=False)
