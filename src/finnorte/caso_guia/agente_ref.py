"""Ejecutor de REFERENCIA del agente (base del laboratorio, NO es tu A4).

Sirve para que el laboratorio muestre el flujo completo: el modelo PROPONE una acción en JSON,
el código valida el esquema, detecta repeticiones, respeta el tope de pasos y NUNCA ejecuta
una herramienta sensible sin confirmación.

`confirmar(h, args)` devuelve:
  True  → aprobada: se ejecuta
  False → rechazada: no se ejecuta
  None  → PENDIENTE: la decisión llega en otra solicitud (servicio web); tampoco se ejecuta

En la A4 implementas TU ejecutar_agente en src/finnorte/herramientas.py (con este mismo contrato)
y lo conectas en api/producto.py. Puedes leer este archivo para entender el flujo; copiarlo no
cuenta como tu implementación.

Sin red (LLM_PROVIDER=fake) se usa un guion simulado del caso guía de despliegues.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable

import jsonschema

from .. import llm, trazas
from ..config import config


@dataclass
class Paso:
    n: int
    propuesta: dict
    resultado: Any = None
    estado: str = ""          # ejecutada | rechazada | pendiente | invalida | repetida | respuesta


@dataclass
class ResultadoAgente:
    respuesta: str
    fuentes: list
    pasos: list[Paso] = field(default_factory=list)
    terminado: bool = True


SISTEMA = """Eres un asistente de ingeniería de FinNorte que resuelve tareas en pasos.
En cada turno devuelve SOLO un JSON con una de dos formas:
{{"accion": "usar", "herramienta": "<nombre>", "argumentos": {{...}}, "razon": "<por qué>"}}
{{"accion": "responder", "respuesta": "<respuesta final>", "fuentes": ["<id>", ...]}}
Herramientas disponibles:
{catalogo}
No inventes herramientas ni resultados. Antes de crear un ticket revisa la ventana de despliegue."""


def _catalogo(herrs: dict) -> str:
    return "\n".join(f"- {h.nombre}: {h.descripcion}. Argumentos (JSON Schema): {json.dumps(h.esquema, ensure_ascii=False)}"
                     + (" [SENSIBLE: requiere confirmación]" if h.sensible else "") for h in herrs.values())


class _GuionSimulado:
    """Guion del caso guía para LLM_PROVIDER=fake: revisar ventana → (si se permite) crear ticket → responder."""

    def __init__(self, tarea: str):
        f = re.search(r"\d{4}-\d{2}-\d{2}", tarea)
        r = re.search(r"riesgo (alto|medio|bajo)", tarea)
        self.plan = {"fecha": f.group(0) if f else "2026-11-24", "riesgo": r.group(1) if r else "alto"}

    def __call__(self, mensaje: str) -> dict:
        if mensaje.startswith("Tarea:"):
            return {"accion": "usar", "herramienta": "revisar_ventana_despliegue", "argumentos": dict(self.plan),
                    "razon": "Primero reviso la regla de ing-03"}
        if mensaje.startswith("Resultado de revisar_ventana_despliegue") and '"permitido": true' in mensaje:
            return {"accion": "usar", "herramienta": "crear_ticket_cambio",
                    "argumentos": {"titulo": "Despliegue de pagos-api", **self.plan}, "razon": "La ventana está permitida"}
        if mensaje.startswith("Resultado de revisar_ventana_despliegue"):
            return {"accion": "responder", "respuesta": f"No se puede desplegar el {self.plan['fecha']} (ing-03).", "fuentes": ["ing-03"]}
        return {"accion": "responder", "respuesta": "El ticket queda pendiente de tu autorización.", "fuentes": ["ing-03"]}


def ejecutar(tarea: str, herramientas: list, confirmar: Callable[[Any, dict], bool | None] | None = None,
             max_pasos: int = 6) -> ResultadoAgente:
    herrs = {h.nombre: h for h in herramientas}
    sistema = SISTEMA.format(catalogo=_catalogo(herrs))
    guion = _GuionSimulado(tarea) if (config().llm_proveedor == "fake" and llm.fake.responder is None) else None
    historial: list[dict] = []
    pasos: list[Paso] = []
    vistos: set[tuple[str, str]] = set()
    mensaje = f"Tarea: {tarea}"
    for n in range(1, max_pasos + 1):
        if guion:
            prop = guion(mensaje)
            texto = json.dumps(prop, ensure_ascii=False)
        else:
            r = llm.generar(mensaje, sistema, json=True, historial=historial, etiqueta=f"caso_guia/agente/paso{n}")
            prop, texto = (r.datos if isinstance(r.datos, dict) else {}), r.texto
        historial += [{"rol": "user", "texto": mensaje}, {"rol": "model", "texto": texto}]
        paso = Paso(n, prop)
        pasos.append(paso)
        if prop.get("accion") == "responder":
            paso.estado = "respuesta"
            trazas.registrar("agente", paso=n, estado=paso.estado)
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
                except Exception as e:  # el error vuelve al modelo como observación
                    paso.resultado = f"ERROR: {e}"
                paso.estado = "ejecutada"
                mensaje = f"Resultado de {h.nombre}: {json.dumps(paso.resultado, ensure_ascii=False, default=str)[:3000]}"
        trazas.registrar("agente", paso=n, herramienta=prop.get("herramienta"), estado=paso.estado)
    return ResultadoAgente("No pude completar la tarea en el número máximo de pasos.", [], pasos, terminado=False)
