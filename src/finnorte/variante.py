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

import re
import time
from pathlib import Path

from . import controles
from .config import RAIZ
from .etapa_analizar import validar_analizar
from .etapa_casos import casos_cubren_qa08
from .etapa_pytest import pytest_compila_y_cubre
from .pipeline import Etapa, Pipeline
from .qa_revisar import validar_revisar
from .retrieval import Indice, contexto_para_prompt

VARIANTE = "v1-qa"
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


# A2 · Las 4 etapas del equipo. Cada una valida contra su esquema (en el prompt) y con su regla
# de negocio (validar=). Sin version=, cada etapa usa su prompt más reciente:
# qa_analizar v2, qa_casos v2, qa_revisar v2, qa_pytest v3.
def _etapas(version: int | None = None) -> list[Etapa]:
    return [
        Etapa("analizar", "qa_analizar", version=version, validar=validar_analizar),
        Etapa("casos", "qa_casos", version=version, usa=["analizar"], validar=casos_cubren_qa08),
        Etapa("revisar", "qa_revisar", version=version, usa=["analizar", "casos"], validar=validar_revisar),
        Etapa("pytest", "qa_pytest", version=version, usa=["casos"], validar=pytest_compila_y_cubre),
    ]


FLUJO = Pipeline(_etapas(), nombre=VARIANTE)
# Avance 1 · para comparar v1 contra v2 define también FLUJO_V1 con las mismas etapas y version=1
# (o pasa version=... a cada Etapa). Si no lo defines, se usa FLUJO para las dos configuraciones.
FLUJO_V1: Pipeline | None = Pipeline(_etapas(version=1), nombre=f"{VARIANTE}-v1")

# Configuración del motor. guia/av1_configuraciones.py la cambia para medir A, B, C y D.
CONFIG_POR_DEFECTO = {
    "version_prompt": 2,   # 1 o 2: qué versión de prompts usa el flujo
    "usar_rag": True,      # recuperar contexto del corpus de la variante (A1)
    "controles": True,     # abstención, filtrado de confidenciales, citas verificadas, saneo
    "k": 4,                # fragmentos a recuperar
    # Umbral calibrado el 2026-11-06 con gemini-embedding-001 y k=4 sobre evals/v1-qa.jsonl: los 4 casos fuera de
    # dominio tienen puntaje máximo de 0.606 a 0.645 y el caso de dentro más bajo (q08) 0.661. Se toma el punto
    # medio. El hueco es de solo 0.016 y se calibró con los mismos casos que se evalúan: la abstención medida es optimista.
    "umbral": 0.653,       # similitud mínima para no abstenerse
}


def armar_salida(t0: float, respuesta: str, fuentes: list[str], abstuvo: bool,
                 errores_citas: list[str] | None = None, artefacto: dict | None = None, costo_usd: float = 0.0) -> dict:
    """Arma el dict que esperan la evaluación, la API (S4) y la interfaz (S5)."""
    return {"respuesta": respuesta, "fuentes": fuentes, "abstuvo": abstuvo, "errores_citas": errores_citas or [],
            "artefacto": artefacto or {}, "costo_usd": costo_usd,
            "latencia_ms": round((time.perf_counter() - t0) * 1000, 1)}


def fuentes_citadas(salidas: dict) -> list[str]:
    """Las fuentes que citó el modelo: el campo opcional «fuente» (qa-xx) de cada caso, sin repetir."""
    casos = (salidas.get("casos") or {}).get("casos") or []
    return list(dict.fromkeys(str(c["fuente"]) for c in casos if isinstance(c, dict) and c.get("fuente")))


def respuesta_texto(salidas: dict, etapas: list) -> str:
    """El artefacto en texto: los casos en Gherkin (con la etiqueta @RFxx que pide qa-08), la revisión y el archivo pytest."""
    analizar = salidas.get("analizar") or {}
    casos = (salidas.get("casos") or {}).get("casos") or []
    revisar = salidas.get("revisar") or {}
    pytest_ = salidas.get("pytest") or {}
    lineas = []
    fallida = next((e for e in etapas if not e.ok), None)
    if fallida:
        lineas += [f"⚠ El flujo se detuvo en la etapa «{fallida.nombre}»: su salida no pasó la validación.", ""]
    if analizar:
        dinero = "sí" if analizar.get("es_operacion_dinero") else "no"
        lineas += [f"Requisito {analizar.get('requisito_id', '?')} · operación de dinero: {dinero}", ""]
    for c in casos:
        rf = re.search(r"RF\d+", str(c.get("id_caso", ""))) or re.search(r"RF\d+", str(analizar.get("requisito_id", "")))
        lineas += [f"@{rf.group(0)}" if rf else "@RF??",
                   f"Escenario: {c.get('id_caso', 'SIN-ID')} · {c.get('titulo', '')} [{c.get('tipo', '?')}]",
                   f"  Dado {c.get('dado', '')}",
                   f"  Cuando {c.get('cuando', '')}",
                   f"  Entonces {c.get('entonces', '')}",
                   f"  # regla: {c.get('regla_citada', '—')}" + (f" · fuente: {c['fuente']}" if c.get("fuente") else ""),
                   ""]
    if revisar:
        faltan = ", ".join(f["tipo_faltante"] for f in revisar.get("casos_faltantes", [])) or "ninguno"
        hallazgos = "; ".join(f"{h['caso_id']}: {h['tipo']}" for h in revisar.get("hallazgos", [])) or "ninguno"
        lineas += [f"Revisión contra qa-08: {'cumple' if revisar.get('cumple_qa08') else 'NO cumple'} · "
                   f"tipos faltantes: {faltan} · hallazgos: {hallazgos}"]
    if pytest_:
        lineas += [f"Pruebas generadas: {pytest_.get('nombre_archivo', '?')} "
                   f"({str(pytest_.get('codigo_pytest', '')).count('def test_')} tests)"]
    return "\n".join(lineas).strip()


def sistema(entrada: dict, config: dict | None = None) -> dict:
    """El motor de tu variante. Sigue los 6 pasos; el caso guía (asistente.py) hace lo mismo con una sola etapa."""
    cfg = {**CONFIG_POR_DEFECTO, **(config or {})}
    t0 = time.perf_counter()
    texto = leer_entrada(entrada)

    # Paso 1 · Recuperar (el buscador de la A1)
    recuperados = indice().buscar(texto, k=cfg["k"]) if cfg["usar_rag"] else []
    # Paso 2 · Controles de entrada: fuera lo confidencial (Avance 2) y abstención sin contexto suficiente
    if cfg["controles"]:
        recuperados = controles.opcional(controles.filtrar_clasificacion, recuperados, por_defecto=recuperados)
        if cfg["usar_rag"] and controles.debe_abstenerse(recuperados, cfg["umbral"]):
            return armar_salida(t0, controles.RESPUESTA_ABSTENCION, [], True)
    # Paso 3 · Flujo de la A2 con el contexto
    flujo = FLUJO_V1 if (cfg["version_prompt"] == 1 and FLUJO_V1) else FLUJO
    r = flujo.ejecutar({"entrada": texto, "contexto": contexto_para_prompt(recuperados) or "(sin contexto)"})
    etapas = [{"etapa": e.nombre, "prompt": e.prompt, "ok": e.ok, "intentos": e.intentos} for e in r.etapas]
    if cfg["controles"] and not r.ok:
        # Con controles, lo que una validación rechazó no se muestra ni se guarda: puede ser justo un dato real
        # (qa-10) que la etapa detectó. Tampoco los mensajes de error, que pueden citar parte del valor.
        fallida = next(e for e in r.etapas if not e.ok)
        aviso = (f"No se generaron casos de prueba confiables: la salida de la etapa «{fallida.nombre}» no pasó "
                 f"su validación después de {fallida.intentos} intentos. Revisa el requisito o vuelve a intentarlo.")
        return armar_salida(t0, aviso, [], False, [],
                            artefacto={"flujo_ok": False, "etapas": etapas}, costo_usd=r.costo_usd)
    artefacto = {**r.salidas, "flujo_ok": r.ok,
                 "etapas": [{**d, "errores": e.errores[:5]} for d, e in zip(etapas, r.etapas)]}
    # Paso 4 · Respuesta y fuentes que citó el modelo
    respuesta = respuesta_texto(r.salidas, r.etapas)
    fuentes = fuentes_citadas(r.salidas)
    # Paso 5 · Verificar citas: con controles, no se muestra algo con fuentes no recuperadas
    errores = controles.verificar_citas(fuentes, recuperados)
    if cfg["controles"] and any("no recuperada" in e for e in errores):
        return armar_salida(t0, controles.RESPUESTA_ABSTENCION, [], True, errores,
                            artefacto=artefacto, costo_usd=r.costo_usd)
    # Paso 6 · Sanear la salida (Avance 2; mientras no exista, la respuesta pasa igual)
    if cfg["controles"]:
        respuesta, _avisos = controles.opcional(controles.sanear_salida, respuesta, por_defecto=(respuesta, []))
    return armar_salida(t0, respuesta, fuentes, False, errores, artefacto=artefacto, costo_usd=r.costo_usd)
