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


def ejecutar_agente(
    tarea: str,
    herramientas: list[Herramienta],
    confirmar: Callable[[Herramienta, dict], bool | None] | None = None,
    max_pasos: int = 5,
    contexto: str = ""
) -> ResultadoAgente:
    """Ejecuta un agente con propuestas JSON, validación y confirmación humana.

    Una herramienta sensible nunca se ejecuta si no existe aprobación explícita.
    """
    if not isinstance(tarea, str) or not tarea.strip():
        raise ValueError("La tarea no puede estar vacía")

    max_pasos = max(1, min(int(max_pasos), 10))

    herrs = {h.nombre: h for h in herramientas}
    if len(herrs) != len(herramientas):
        raise ValueError("Hay nombres de herramientas duplicados")

    sistema = SISTEMA_AGENTE.format(catalogo=_catalogo(herrs))
    pasos: list[Paso] = []
    historial: list[dict] = []
    repetidas: set[str] = set()

    mensaje_base = f"Tarea: {tarea}"
    if contexto:
        mensaje_base += f"\\n\\nContexto:\\n{contexto}"

    def invalidar(n: int, propuesta: dict, motivo: str):
        paso = Paso(n, propuesta, {"error": motivo}, "invalida")
        pasos.append(paso)
        historial.append({
            "paso": n,
            "propuesta": propuesta,
            "estado": "invalida",
            "resultado": motivo
        })
        trazas.registrar(
            "agente",
            paso=n,
            herramienta=propuesta.get("herramienta"),
            estado="invalida",
            motivo=motivo
        )

    for numero in range(1, max_pasos + 1):
        consulta = mensaje_base

        if historial:
            consulta += (
                "\\n\\nHistorial de ejecución (JSON):\\n"
                + json.dumps(historial, ensure_ascii=False, default=str)
            )

        try:
            respuesta_llm = llm.generar(
                consulta,
                sistema,
                json=True,
                temperatura=0.0,
                etiqueta=f"agente/paso{numero}"
            )

            propuesta = respuesta_llm.datos

            if not isinstance(propuesta, dict):
                propuesta = json.loads(respuesta_llm.texto)

            if not isinstance(propuesta, dict):
                raise ValueError("La propuesta debe ser un objeto JSON")

        except Exception as exc:
            invalidar(numero, {}, f"Respuesta JSON inválida: {type(exc).__name__}")
            continue

        accion = propuesta.get("accion")

        if accion == "responder":
            respuesta = propuesta.get("respuesta")
            fuentes = propuesta.get("fuentes", [])

            if not isinstance(respuesta, str) or not respuesta.strip():
                invalidar(numero, propuesta, "La respuesta está vacía")
                continue

            if not isinstance(fuentes, list) or not all(
                isinstance(f, str) for f in fuentes
            ):
                invalidar(numero, propuesta, "Las fuentes deben ser textos")
                continue

            pasos.append(Paso(numero, propuesta, respuesta, "respuesta"))
            trazas.registrar("agente", paso=numero, estado="respuesta")

            return ResultadoAgente(
                respuesta=respuesta,
                fuentes=fuentes,
                pasos=pasos,
                terminado=True
            )

        if accion != "usar":
            invalidar(numero, propuesta, "Acción desconocida")
            continue

        nombre = propuesta.get("herramienta")
        argumentos = propuesta.get("argumentos")

        if not isinstance(nombre, str) or not isinstance(argumentos, dict):
            invalidar(numero, propuesta, "Herramienta o argumentos inválidos")
            continue

        h = herrs.get(nombre)

        if h is None:
            invalidar(numero, propuesta, "Herramienta no registrada")
            continue

        try:
            jsonschema.Draft202012Validator(h.esquema).validate(argumentos)
        except jsonschema.ValidationError:
            invalidar(numero, propuesta, "Argumentos fuera del esquema permitido")
            continue

        clave = json.dumps(
            {"herramienta": nombre, "argumentos": argumentos},
            sort_keys=True,
            ensure_ascii=False
        )

        if clave in repetidas:
            invalidar(numero, propuesta, "Propuesta repetida; se evita una ejecución duplicada")
            continue

        repetidas.add(clave)

        if h.sensible:
            decision = None

            if confirmar is not None:
                try:
                    decision = confirmar(h, dict(argumentos))
                except Exception:
                    invalidar(numero, propuesta, "No se pudo obtener la confirmación")
                    continue

            if decision is None:
                resultado = {
                    "estado": "pendiente",
                    "mensaje": "Requiere confirmación humana"
                }
                estado = "sin_confirmar"

            elif decision is False:
                resultado = {"estado": "rechazada"}
                estado = "rechazada"

            elif decision is True:
                try:
                    resultado = h.funcion(**argumentos)
                    estado = "ejecutada"
                except Exception as exc:
                    resultado = {"error": type(exc).__name__}
                    estado = "invalida"
            else:
                invalidar(numero, propuesta, "La confirmación debe ser True, False o None")
                continue

        else:
            try:
                resultado = h.funcion(**argumentos)
                estado = "ejecutada"
            except Exception as exc:
                resultado = {"error": type(exc).__name__}
                estado = "invalida"

        pasos.append(Paso(numero, propuesta, resultado, estado))

        historial.append({
            "paso": numero,
            "herramienta": nombre,
            "argumentos": argumentos,
            "estado": estado,
            "resultado": resultado
        })

        trazas.registrar(
            "agente",
            paso=numero,
            herramienta=nombre,
            estado=estado
        )

    return ResultadoAgente(
        respuesta=f"Se alcanzó el límite de {max_pasos} pasos sin completar la tarea.",
        fuentes=[],
        pasos=pasos,
        terminado=False
    )
