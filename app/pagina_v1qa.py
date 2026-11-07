"""Página «Requisito → pytest» (variante v1-qa) para la interfaz de Streamlit.

Corre el FLUJO del equipo (analizar → casos → revisar → pytest) sobre un requisito y muestra,
etapa por etapa, si pasó su esquema y su validación en código. Si llega a la etapa 4, deja
descargar el archivo pytest generado.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import streamlit as st

from finnorte import llm
from finnorte.config import RAIZ
from finnorte.retrieval import Indice, contexto_para_prompt
from finnorte.variante import FLUJO, VARIANTE

CARPETA_REQUISITOS = RAIZ / "datos" / "v1-qa" / "requisitos"
NOMBRES_ETAPA = {"analizar": "1 · Analizar requisito", "casos": "2 · Generar casos",
                 "revisar": "3 · Revisar cobertura (qa-08)", "pytest": "4 · Exportar a pytest"}
K = 4


@st.cache_resource
def indice_v1qa() -> Indice:
    return Indice.desde_carpeta(RAIZ / "corpus" / VARIANTE)


def requisitos_de_ejemplo() -> dict[str, str]:
    return {p.stem: p.read_text(encoding="utf-8") for p in sorted(CARPETA_REQUISITOS.glob("RF*.md"))}


def resumen(nombre: str, salida) -> str:
    """Una línea que dice qué produjo la etapa."""
    if not isinstance(salida, dict):
        return "sin salida"
    if nombre == "analizar":
        return f"{salida.get('requisito_id')} · {len(salida.get('reglas_negocio') or [])} reglas · {len(salida.get('ambiguedades') or [])} ambigüedades"
    if nombre == "casos":
        casos = salida.get("casos") or []
        return f"{len(casos)} casos · {len({c.get('tipo') for c in casos})} tipos"
    if nombre == "revisar":
        return f"cumple qa-08: {'sí' if salida.get('cumple_qa08') else 'no'} · {len(salida.get('casos_faltantes') or [])} faltantes"
    if nombre == "pytest":
        codigo = salida.get("codigo_pytest") or ""
        return f"{salida.get('nombre_archivo')} · {codigo.count('def test_')} tests"
    return ""


def mostrar() -> None:
    st.title("🧪 Requisito → pruebas (v1-qa)")
    st.caption("Pega un requisito funcional. El flujo lo analiza, genera casos Dado/Cuando/Entonces, "
               "revisa la cobertura contra qa-08 y lo exporta a pytest. Cada etapa se valida en código.")

    ejemplos = requisitos_de_ejemplo()
    elegido = st.selectbox("Requisito de ejemplo", ["(escribir uno)"] + list(ejemplos))
    if elegido != "(escribir uno)" and st.session_state.get("_req_cargado") != elegido:
        st.session_state["requisito"] = ejemplos[elegido]
        st.session_state["_req_cargado"] = elegido
    texto = st.text_area("Requisito", key="requisito", height=200, max_chars=6000)
    usar_rag = st.toggle("Usar el corpus de QA como contexto (RAG)", value=True)

    if not st.button("Generar pruebas", type="primary", disabled=not texto.strip()):
        return

    t0 = time.perf_counter()
    with st.spinner("Corriendo las 4 etapas… (con Gemini tarda de 25 a 40 s)"):
        try:
            contexto = contexto_para_prompt(indice_v1qa().buscar(texto, k=K)) if usar_rag else ""
            r = FLUJO.ejecutar({"entrada": texto, "contexto": contexto or "(sin contexto)"})
        except llm.LLMError as e:
            st.error("El modelo no respondió (puede ser la cuota diaria). Intenta de nuevo en unos minutos.")
            st.caption(f"Detalle técnico: {str(e)[:160]}")
            return
    segundos = time.perf_counter() - t0

    cols = st.columns(len(FLUJO.etapas))
    hechas = {e.nombre: e for e in r.etapas}
    for col, etapa in zip(cols, FLUJO.etapas):
        e = hechas.get(etapa.nombre)
        estado = "no llegó" if e is None else ("✅ válida" if e.ok else "❌ rechazada")
        col.metric(NOMBRES_ETAPA.get(etapa.nombre, etapa.nombre), estado,
                   None if e is None else f"{e.intentos} intento{'s' if e.intentos > 1 else ''}", delta_color="off")

    (st.success if r.ok else st.warning)(
        "El flujo llegó completo a pytest." if r.ok else
        f"El flujo se detuvo en «{r.etapas[-1].nombre}»: su validación rechazó la salida aun con el reintento.")

    for e in r.etapas:
        with st.expander(f"{NOMBRES_ETAPA.get(e.nombre, e.nombre)} · {e.prompt} · {resumen(e.nombre, e.salida)}",
                         expanded=not e.ok):
            if e.errores:
                st.warning("Lo que revisó el código y no pasó:\n\n" + "\n".join(f"- {x}" for x in e.errores))
            st.json(e.salida if isinstance(e.salida, dict) else {"salida": e.salida}, expanded=False)

    salida_pytest = r.salidas.get("pytest") if r.ok else None
    if isinstance(salida_pytest, dict) and salida_pytest.get("codigo_pytest"):
        st.subheader(f"📄 {salida_pytest.get('nombre_archivo', 'test_requisito.py')}")
        st.code(salida_pytest["codigo_pytest"], language="python")
        st.download_button("Descargar archivo pytest", salida_pytest["codigo_pytest"],
                           file_name=salida_pytest.get("nombre_archivo", "test_requisito.py"), mime="text/x-python")

    st.caption(f"⏱ {segundos:.1f} s · 💲 US${r.costo_usd:.5f} · contexto: {'sí, k=' + str(K) if usar_rag else 'no'}")
    with st.expander("Trazabilidad (JSON de cada etapa)"):
        st.code(json.dumps({e.nombre: {"prompt": e.prompt, "ok": e.ok, "intentos": e.intentos, "errores": e.errores}
                            for e in r.etapas}, ensure_ascii=False, indent=2), language="json")
