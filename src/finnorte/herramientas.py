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
                    max_pasos: int = 5, contexto: str = "",
                    simulador: Callable[[str], dict] | None = None) -> ResultadoAgente:
    herrs = {h.nombre: h for h in herramientas}
    sistema = SISTEMA_AGENTE.format(catalogo=_catalogo(herrs))
    historial: list[dict] = []
    pasos: list[Paso] = []
    ejecutadas: set[str] = set()            # firmas (herramienta + argumentos) ya ejecutadas: detecta repeticiones
    mensaje = f"Tarea: {tarea}" + (f"\n\nContexto:\n{contexto}" if contexto else "")

    for n in range(1, max_pasos + 1):                       # TOPE DE PASOS: el bucle nunca es infinito
        if simulador is not None:
            propuesta = simulador(mensaje)
            texto = json.dumps(propuesta, ensure_ascii=False)
        else:
            r = llm.generar(mensaje, sistema, json=True, historial=historial, etiqueta=f"agente/paso{n}")
            propuesta, texto = (r.datos if isinstance(r.datos, dict) else {}), r.texto
        historial += [{"rol": "user", "texto": mensaje}, {"rol": "model", "texto": texto}]
        paso = Paso(n, propuesta)
        pasos.append(paso)

        if propuesta.get("accion") == "responder":
            paso.estado = "respuesta"
            trazas.registrar("agente", paso=n, estado=paso.estado)
            return ResultadoAgente(str(propuesta.get("respuesta", "")), list(propuesta.get("fuentes") or []), pasos)

        mensaje = _procesar_propuesta(paso, herrs, ejecutadas, confirmar)
        trazas.registrar("agente", paso=n, herramienta=propuesta.get("herramienta"), estado=paso.estado)

    return ResultadoAgente("No pude completar la tarea en el número máximo de pasos.", [], pasos, terminado=False)


def _errores_de_esquema(herramienta: Herramienta, argumentos: Any) -> list[str]:
    """Valida los argumentos que PROPUSO el modelo contra el esquema JSON de la herramienta (nunca se confía en ellos)."""
    return [e.message for e in jsonschema.Draft202012Validator(herramienta.esquema).iter_errors(argumentos)]


def _procesar_propuesta(paso: Paso, herrs: dict[str, Herramienta], ejecutadas: set[str],
                        confirmar: Callable[[Herramienta, dict], bool | None] | None) -> str:
    """Decide qué pasa con una propuesta de «usar» una herramienta. Fija paso.estado y devuelve el mensaje
    que se le regresa al modelo como observación.

    Orden de las barreras (todas en código, ninguna depende de que el modelo se porte bien):
      1. ¿existe la herramienta?  2. ¿los argumentos cumplen el esquema?  3. ¿ya se ejecutó igual?
      4. ¿es sensible?  Entonces solo se ejecuta si confirmar(...) devuelve EXACTAMENTE True.
         False = rechazada, None = pendiente (la decisión llega en otra solicitud): en ambos casos NO se ejecuta.
    """
    propuesta = paso.propuesta
    herramienta = herrs.get(str(propuesta.get("herramienta", "")))
    if propuesta.get("accion") != "usar" or herramienta is None:
        paso.estado = "invalida"
        return f"Acción inválida. Usa una herramienta de la lista {list(herrs)} o responde. Recibí: {json.dumps(propuesta, ensure_ascii=False)[:300]}"

    argumentos = propuesta.get("argumentos")
    argumentos = {} if argumentos is None else argumentos
    errores = _errores_de_esquema(herramienta, argumentos)
    if errores:
        paso.estado = "invalida"
        return f"Argumentos inválidos para {herramienta.nombre}: {errores[:3]}"

    firma = herramienta.nombre + json.dumps(argumentos, sort_keys=True, ensure_ascii=False)
    if firma in ejecutadas:
        paso.estado = "repetida"
        return f"Ya ejecutaste {herramienta.nombre} con esos mismos argumentos. Usa ese resultado o responde."

    if herramienta.sensible:
        try:
            decision = confirmar(herramienta, argumentos) if confirmar else False
        except Exception:                                   # si la confirmación falla, se rechaza: nunca se ejecuta por error
            decision = False
        if decision is not True:
            paso.estado = "pendiente" if decision is None else "rechazada"
            if decision is None:
                return (f"{herramienta.nombre}({argumentos}) quedó PENDIENTE de confirmación humana. "
                        "No la repitas; responde avisando que espera autorización.")
            return f"La persona NO confirmó {herramienta.nombre}({argumentos}). No la ejecutes; responde explicando qué se necesita."

    ejecutadas.add(firma)
    try:
        paso.resultado = herramienta.funcion(**argumentos)
    except Exception as e:                                  # una falla de la herramienta vuelve al modelo como observación
        paso.resultado = f"ERROR: {type(e).__name__}: {e}"
    paso.estado = "ejecutada"
    return f"Resultado de {herramienta.nombre}: {json.dumps(paso.resultado, ensure_ascii=False, default=str)[:3000]}"
