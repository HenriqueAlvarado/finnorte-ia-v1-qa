"""Caso guía de los viernes: «Pregúntale al Manual de Ingeniería de FinNorte».

Es el ejemplo resuelto que construimos juntos en clase (corpus común en corpus/comun/).
Tu equipo construye lo mismo para SU variante en src/finnorte/variante.py.

    from finnorte.asistente import Asistente
    a = Asistente.crear()                                  # indexa corpus/comun
    a.responder("¿Cada cuánto se rotan los secretos?")     # dict listo para evaluación
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass

from . import controles, llm, prompts, trazas
from .config import RAIZ
from .retrieval import Indice, contexto_para_prompt


@dataclass
class OpcionesAsistente:
    version_prompt: int | None = None   # None = la más reciente
    usar_rag: bool = True
    k: int = 4
    umbral: float = 0.35               # calíbralo con tus casos (T6): depende del proveedor de embeddings
    controles: bool = True             # citas + abstención + clasificación + saneo
    autocritica: bool = False          # una llamada extra por respuesta


class Asistente:
    def __init__(self, indice: Indice | None, opciones: OpcionesAsistente | None = None, prompt_id: str = "responder"):
        self.indice = indice
        self.op = opciones or OpcionesAsistente()
        self.prompt_id = prompt_id

    @classmethod
    def crear(cls, carpeta=RAIZ / "corpus" / "comun", **opciones) -> "Asistente":
        return cls(Indice.desde_carpeta(carpeta), OpcionesAsistente(**opciones))

    def responder(self, pregunta: str | dict) -> dict:
        if isinstance(pregunta, dict):
            pregunta = pregunta.get("pregunta", "")
        t0 = time.perf_counter()
        costo = 0.0
        op = self.op
        abstencion = {"respuesta": controles.RESPUESTA_ABSTENCION, "fuentes": [], "abstuvo": True, "errores_citas": []}

        # 1 · Recuperar
        recuperados = self.indice.buscar(pregunta, k=op.k) if (op.usar_rag and self.indice) else []
        # 2 · Controles de entrada: fuera lo confidencial; sin contexto suficiente, ni se llama al modelo
        if op.controles:
            recuperados = controles.opcional(controles.filtrar_clasificacion, recuperados, por_defecto=recuperados)
            if op.usar_rag and controles.debe_abstenerse(recuperados, op.umbral):
                return self._cerrar(abstencion, pregunta, t0, costo, recuperados)
        # 3 · Generar
        p = prompts.cargar(self.prompt_id, op.version_prompt)
        contexto = contexto_para_prompt(recuperados) or "(sin contexto)"
        sistema, usuario = p.render(contexto=contexto, pregunta=pregunta)
        r = llm.generar(usuario, sistema, json=p.salida_json, etiqueta=f"asistente/{p.nombre}")
        costo += r.costo_usd
        # 4 · Respuesta y fuentes (la v1 responde en texto: las citas salen de las marcas «doc:ID»)
        if isinstance(r.datos, dict):
            respuesta = str(r.datos.get("respuesta", ""))
            fuentes = [str(f) for f in (r.datos.get("fuentes") or [])]
            abstuvo = bool(r.datos.get("abstuvo", False))
        else:
            respuesta = r.texto.strip()
            fuentes = list(dict.fromkeys(re.findall(r"doc:([\w.\-]+(?:#\d+)?)", respuesta)))
            abstuvo = False
        if abstuvo:
            return self._cerrar(abstencion | {"respuesta": respuesta or abstencion["respuesta"]}, pregunta, t0, costo, recuperados)
        # 5 · Verificar citas: con controles, una cita no recuperada no se muestra
        errores = controles.verificar_citas(fuentes, recuperados)
        if op.controles and any("no recuperada" in e for e in errores):
            return self._cerrar(abstencion | {"errores_citas": errores}, pregunta, t0, costo, recuperados)
        if op.controles and op.autocritica:
            revision = controles.autocritica(respuesta, contexto, pregunta)
            if not revision["soportada"]:
                return self._cerrar(abstencion | {"errores_citas": errores + revision["problemas"]},
                                    pregunta, t0, costo, recuperados)
        # 6 · Sanear la salida
        if op.controles:
            respuesta, _avisos = controles.opcional(controles.sanear_salida, respuesta, por_defecto=(respuesta, []))
        salida = {"respuesta": respuesta, "fuentes": fuentes, "abstuvo": False, "errores_citas": errores}
        return self._cerrar(salida, pregunta, t0, costo, recuperados)

    def _cerrar(self, salida: dict, pregunta: str, t0: float, costo: float, recuperados) -> dict:
        salida["latencia_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        salida["costo_usd"] = costo
        salida["recuperados"] = [(r.fragmento.id, round(r.puntaje, 3)) for r in recuperados]
        trazas.registrar("respuesta", pregunta=pregunta[:200], abstuvo=salida["abstuvo"], fuentes=salida["fuentes"],
                         latencia_ms=salida["latencia_ms"], costo_usd=round(costo, 6))
        return salida
