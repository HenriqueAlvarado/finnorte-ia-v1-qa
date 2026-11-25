"""Asistente del caso guía: «Pregúntale al Manual de Ingeniería de FinNorte». Base resuelta del laboratorio."""
from __future__ import annotations

import time

from .. import llm, trazas
from ..retrieval import contexto_para_prompt
from .buscador import buscador

ABSTENCION = "No encuentro esa información en la documentación disponible. Te sugiero consultarlo con el área responsable."

SISTEMA = """Eres el asistente del Manual de Ingeniería de FinNorte.
Responde SOLO con información del contexto y cita los ids que usaste (el texto que va después de [doc:).
Si el contexto no alcanza para responder, abstente.
Devuelve SOLO un JSON: {"respuesta": "...", "fuentes": ["<id>", ...], "abstuvo": false}"""


def _limpiar(fuente: str) -> str:
    return str(fuente).strip().removeprefix("[").removesuffix("]").removeprefix("doc:")


def responder(pregunta: str, k: int = 4) -> dict:
    t0 = time.perf_counter()
    recuperados = buscador().buscar(pregunta, k=k)
    costo = 0.0
    if not recuperados:
        salida = {"respuesta": ABSTENCION, "fuentes": [], "abstuvo": True}
    else:
        r = llm.generar(f"Contexto:\n{contexto_para_prompt(recuperados)}\n\nPregunta: {pregunta}", SISTEMA,
                        json=True, etiqueta="caso_guia/responder")
        costo = r.costo_usd
        datos = r.datos if isinstance(r.datos, dict) else {"respuesta": r.texto, "fuentes": []}
        validos = {x.fragmento.id for x in recuperados} | {x.fragmento.doc_id for x in recuperados}
        fuentes = [f for f in map(_limpiar, datos.get("fuentes", [])) if f in validos]   # solo citas recuperadas
        abstuvo = bool(datos.get("abstuvo")) or not fuentes
        salida = {"respuesta": ABSTENCION if abstuvo else str(datos.get("respuesta", "")),
                  "fuentes": [] if abstuvo else fuentes, "abstuvo": abstuvo}
    salida["latencia_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    salida["costo_usd"] = costo
    trazas.registrar("respuesta", modulo="caso_guia", pregunta=pregunta[:200], abstuvo=salida["abstuvo"],
                     fuentes=salida["fuentes"], latencia_ms=salida["latencia_ms"])
    return salida
