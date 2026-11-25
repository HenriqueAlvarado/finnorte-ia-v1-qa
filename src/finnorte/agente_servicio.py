"""Agente detrás de una API (Laboratorio A3+A4): confirmación humana en DOS PASOS.

En una app web el agente no puede "esperar" a que alguien dé clic. Por eso:

  1. POST /v1/agente        → el agente trabaja; si propone una herramienta SENSIBLE, NO la ejecuta.
                               El código guarda la acción exacta (herramienta + argumentos) como PENDIENTE
                               y devuelve un id de confirmación.
  2. POST /v1/agente/confirmar/{id} {"aprobar": true|false}
                            → si se aprueba, el CÓDIGO ejecuta exactamente lo guardado (el modelo ya no
                               interviene); si se rechaza, no se ejecuta nada. Ambos casos quedan en la bitácora.

Antes de guardar una acción pendiente corre un VALIDADOR de lógica tradicional (`validar_plan`):
si la acción no está respaldada por las herramientas de consulta, se bloquea y ni siquiera se ofrece.

Laboratorio: por defecto usa el ejecutor de REFERENCIA (caso_guia.agente_ref).
A4: pasa tu propio ejecutor, por ejemplo  iniciar(..., ejecutor=herramientas.ejecutar_agente),
y tu validador de la variante con  validador=mi_validador.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Callable

from . import trazas
from .caso_guia import agente_ref

VIGENCIA_PENDIENTE_S = 10 * 60


@dataclass
class Pendiente:
    id: str
    usuario: str
    herramienta: str
    argumentos: dict
    creado: float = field(default_factory=time.time)


_PENDIENTES: dict[str, Pendiente] = {}


def validar_plan(resultado, propuestas: list[tuple[str, dict]]) -> list[str]:
    """Validador del CASO GUÍA (cámbialo por el de tu variante en la A4).

    Regla de negocio (ing-03): un ticket de cambio solo se ofrece si en ESTA ejecución
    revisar_ventana_despliegue dijo permitido=True para la MISMA fecha y el MISMO riesgo.
    """
    hallazgos = []
    revisadas = {(p.propuesta.get("argumentos", {}).get("fecha"), p.propuesta.get("argumentos", {}).get("riesgo")):
                 (p.resultado or {}).get("permitido")
                 for p in resultado.pasos
                 if p.propuesta.get("herramienta") == "revisar_ventana_despliegue" and p.estado == "ejecutada"
                 and isinstance(p.resultado, dict)}
    for nombre, args in propuestas:
        if nombre != "crear_ticket_cambio":
            continue
        clave = (args.get("fecha"), args.get("riesgo"))
        if clave not in revisadas:
            hallazgos.append(f"El ticket para {clave[0]} no pasó por revisar_ventana_despliegue con riesgo {clave[1]}")
        elif revisadas[clave] is not True:
            hallazgos.append(f"La ventana del {clave[0]} NO está permitida (ing-03); no se puede crear el ticket")
    return hallazgos


def iniciar(tarea: str, usuario: str, herramientas: list, max_pasos: int = 6,
            validador: Callable[[object, list[tuple[str, dict]]], list[str]] = validar_plan,
            ejecutor: Callable | None = None) -> dict:
    propuestas: list[tuple[str, dict]] = []

    def confirmar(h: Herramienta, args: dict) -> None:
        propuestas.append((h.nombre, dict(args)))
        return None                      # None = "pendiente": nunca se ejecuta dentro del agente

    r = (ejecutor or agente_ref.ejecutar)(tarea, herramientas, confirmar=confirmar, max_pasos=max_pasos)
    hallazgos = validador(r, propuestas)
    pendientes = []
    if not hallazgos:
        for nombre, args in propuestas[:1]:          # una acción sensible por ejecución
            p = Pendiente(uuid.uuid4().hex[:12], usuario, nombre, args)
            _PENDIENTES[p.id] = p
            pendientes.append({"id": p.id, "herramienta": nombre, "argumentos": args,
                               "mensaje": f"¿Autorizas {nombre} con estos datos exactos? {args}",
                               "expira_en_s": VIGENCIA_PENDIENTE_S})
    trazas.registrar("agente_api", usuario=usuario, tarea=tarea[:200], pasos=len(r.pasos),
                     propuestas_sensibles=len(propuestas), pendientes=[x["id"] for x in pendientes], validador=hallazgos)
    return {"respuesta": r.respuesta, "fuentes": r.fuentes, "terminado": r.terminado,
            "pasos": [{"n": p.n, "accion": p.propuesta.get("accion"), "herramienta": p.propuesta.get("herramienta"),
                       "argumentos": p.propuesta.get("argumentos"), "estado": p.estado, "resultado": p.resultado}
                      for p in r.pasos],
            "validador": {"ok": not hallazgos, "hallazgos": hallazgos},
            "pendientes": pendientes}


def resolver(id_: str, usuario: str, aprobar: bool, herramientas: list) -> dict:
    p = _PENDIENTES.get(id_)
    if p is None or p.usuario != usuario:
        raise KeyError("No existe una acción pendiente con ese id para tu usuario")
    del _PENDIENTES[id_]                                  # un solo uso
    if time.time() - p.creado > VIGENCIA_PENDIENTE_S:
        trazas.registrar("agente", estado="expirada", herramienta=p.herramienta, usuario=usuario)
        return {"estado": "expirada", "herramienta": p.herramienta}
    if not aprobar:
        trazas.registrar("agente", estado="rechazada", herramienta=p.herramienta, argumentos=p.argumentos, usuario=usuario)
        return {"estado": "rechazada", "herramienta": p.herramienta, "argumentos": p.argumentos}
    h = {x.nombre: x for x in herramientas}[p.herramienta]
    resultado = h.funcion(**p.argumentos)                 # exactamente lo que la persona vio y aprobó
    trazas.registrar("agente", estado="confirmada", herramienta=p.herramienta, argumentos=p.argumentos,
                     usuario=usuario, resultado=resultado)
    return {"estado": "ejecutada", "herramienta": p.herramienta, "argumentos": p.argumentos, "resultado": resultado}
