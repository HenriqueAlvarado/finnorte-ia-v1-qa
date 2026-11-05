"""TU SISTEMA: el motor de la variante de tu equipo.

Contrato mínimo (lo usa `python -m finnorte evaluar ... --sistema finnorte.variante:sistema`,
la API de la semana 4 y la interfaz de la semana 5):

    sistema(entrada: dict) -> dict con
        respuesta: str        el artefacto final en texto (casos, hallazgos, respuesta, README, triage)
        fuentes: list[str]    ids de fragmentos/documentos del corpus que respaldan la salida
        abstuvo: bool         True si la entrada está fuera de alcance o no hay contexto suficiente
        errores_citas: list   salida de controles.verificar_citas
        artefacto: dict       (opcional) la salida estructurada (JSON) de tu última etapa
        costo_usd, latencia_ms

Construye esto por incrementos:
  A1  → INDICE con el corpus de tu variante (corpus/<variante>/) y búsqueda semántica
  A2  → FLUJO de 4 etapas con prompts versionados en prompts/ y esquemas en prompts/esquemas/
  Av1 → RAG (contexto en el prompt) + controles + evaluación contra tu contrato de calidad
"""
from __future__ import annotations

import time
from pathlib import Path

from . import controles
from .config import RAIZ
from .pipeline import Etapa, Pipeline
from .retrieval import Indice, contexto_para_prompt

VARIANTE = "v?-cambia-esto"          # v1-qa | v2-revisor | v3-soporte | v4-documentador | v5-triage
_INDICE: Indice | None = None


def indice() -> Indice:
    global _INDICE
    if _INDICE is None:
        _INDICE = Indice.desde_carpeta(RAIZ / "corpus" / VARIANTE)
    return _INDICE


def leer_entrada(entrada: dict) -> str:
    """Normaliza la entrada de los casos de evaluación a texto."""
    if "archivo" in entrada:
        return (RAIZ / entrada["archivo"]).read_text(encoding="utf-8")
    for clave in ("requisito", "codigo", "pregunta", "log"):
        if clave in entrada:
            return str(entrada[clave])
    raise ValueError(f"Entrada sin campo reconocido: {list(entrada)}")


# TODO(A2): define tus etapas. Ejemplo para v1-qa:
#   Etapa("analizar", "qa_analizar"), Etapa("casos", "qa_casos", usa=["analizar"]),
#   Etapa("revisar", "qa_revisar", usa=["analizar", "casos"]), Etapa("pytest", "qa_pytest", usa=["casos"])
FLUJO = Pipeline([], nombre=VARIANTE)
# Avance 1 · para comparar v1 contra v2 define también FLUJO_V1 con las mismas etapas y version=1
# (o pasa version=... a cada Etapa). Si no lo defines, se usa FLUJO para las dos configuraciones.
FLUJO_V1: Pipeline | None = None

# Configuración del motor. guia/av1_configuraciones.py la cambia para medir A, B, C y D.
CONFIG_POR_DEFECTO = {
    "version_prompt": 2,   # 1 o 2: qué versión de prompts usa el flujo
    "usar_rag": True,      # recuperar contexto del corpus de la variante (A1)
    "controles": True,     # abstención, filtrado de confidenciales, citas verificadas, saneo
    "k": 4,                # fragmentos a recuperar
    "umbral": 0.35,        # similitud mínima para no abstenerse (ajústalo con tus datos)
}


def armar_salida(t0: float, respuesta: str, fuentes: list[str], abstuvo: bool,
                 errores_citas: list[str] | None = None, artefacto: dict | None = None, costo_usd: float = 0.0) -> dict:
    """Arma el dict que esperan la evaluación, la API (S4) y la interfaz (S5)."""
    return {"respuesta": respuesta, "fuentes": fuentes, "abstuvo": abstuvo, "errores_citas": errores_citas or [],
            "artefacto": artefacto or {}, "costo_usd": costo_usd,
            "latencia_ms": round((time.perf_counter() - t0) * 1000, 1)}


def sistema(entrada: dict, config: dict | None = None) -> dict:
    """El motor de tu variante. Sigue los 6 pasos; el caso guía (asistente.py) hace lo mismo con una sola etapa."""
    cfg = {**CONFIG_POR_DEFECTO, **(config or {})}
    t0 = time.perf_counter()
    texto = leer_entrada(entrada)

    # Paso 1 · Recuperar (tu buscador de la A1)
    #   recuperados = indice().buscar(texto, k=cfg["k"]) if cfg["usar_rag"] else []
    # Paso 2 · Controles de entrada (si cfg["controles"])
    #   recuperados = controles.opcional(controles.filtrar_clasificacion, recuperados, por_defecto=recuperados)  # Avance 2: fuera lo confidencial
    #   if cfg["usar_rag"] and controles.debe_abstenerse(recuperados, cfg["umbral"]):
    #       return armar_salida(t0, controles.RESPUESTA_ABSTENCION, [], True)
    # Paso 3 · Flujo de la A2 con el contexto
    #   flujo = FLUJO_V1 if (cfg["version_prompt"] == 1 and FLUJO_V1) else FLUJO
    #   r = flujo.ejecutar({"entrada": texto, "contexto": contexto_para_prompt(recuperados) or "(sin contexto)"})
    #   final = r.salidas[...]   # la salida estructurada de tu última etapa (revisa ResultadoFlujo en pipeline.py)
    # Paso 4 · Respuesta y fuentes: convierte el artefacto a texto y toma las fuentes que citó el modelo
    # Paso 5 · Verificar citas: errores = controles.verificar_citas(fuentes, recuperados)
    #   si hay citas "no recuperada" y cfg["controles"] → abstente (no muestres algo con fuentes inventadas)
    # Paso 6 · Sanear la salida (cfg["controles"]):
    #   respuesta, avisos = controles.opcional(controles.sanear_salida, respuesta, por_defecto=(respuesta, []))
    #   return armar_salida(t0, respuesta, fuentes, False, errores, artefacto=final, costo_usd=r.costo_usd)
    raise NotImplementedError("Avance 1: implementa los 6 pasos de sistema() (ver comentarios y asistente.py)")
