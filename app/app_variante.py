"""A4 · interfaz de MI variante (v1-qa), sobre el SERVICIO de la A3 (no funciones locales).
   streamlit run app/app_variante.py

Parte de app/cliente_api.py del laboratorio (login, manejo de errores, patrón de llamadas)
y lo adapta a v1-qa:
  - "Mi variante": entra un requisito (RFxx), sale el artefacto de variante.sistema() con
    fuentes citadas y el VALIDADOR de lógica tradicional (A4 paso 4) corriendo en cada
    respuesta, no solo al final.
  - "Agente": igual que el lab (confirmación humana en 2 pasos) pero ahora con MI
    herramienta (ejecutar_pytest) y MI validador de plan (qa_herramientas.validar_plan_v1qa).

Antes: en otra terminal, uvicorn api.producto:app --reload
La URL del servicio se lee de API_URL (env o .env; por defecto http://127.0.0.1:8000).
"""
from __future__ import annotations

import os
from pathlib import Path

import requests
import streamlit as st


def _cargar_env(archivo: Path = Path(__file__).resolve().parents[1] / ".env") -> None:
    if archivo.exists():
        for linea in archivo.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                clave, valor = linea.split("=", 1)
                os.environ.setdefault(clave.strip(), valor.strip().strip('"').strip("'"))


_cargar_env()
API = os.getenv("API_URL", "http://127.0.0.1:8000")
st.set_page_config(page_title="FinNorte · v1-qa", page_icon="🧪", layout="wide")


def llamar(metodo: str, ruta: str, **kw) -> tuple[int, dict]:
    h = {"Authorization": f"Bearer {st.session_state['token']}"} if st.session_state.get("token") else {}
    try:
        r = requests.request(metodo, f"{API}{ruta}", headers=h, timeout=90, **kw)
        return r.status_code, (r.json() if r.content else {})
    except requests.RequestException as e:
        return 0, {"title": "Servicio no disponible", "detail": f"¿Está corriendo uvicorn en {API}? ({type(e).__name__})"}


def mostrar_error(status: int, cuerpo: dict):
    if status == 401:
        st.session_state.pop("token", None)
        st.warning("Tu sesión expiró o no es válida. Vuelve a iniciar sesión.")
    elif status == 429:
        st.warning(f"{cuerpo.get('detail', 'Demasiadas solicitudes')}. Espera un minuto.")
    elif status == 503:
        st.error("El modelo (Gemini) no respondió a tiempo. Intenta de nuevo en unos segundos.")
    else:
        st.error(f"{cuerpo.get('title', 'Error')}: {cuerpo.get('detail', '')}")
    if cuerpo.get("trace_id"):
        st.caption(f"trace_id: {cuerpo['trace_id']}")


def mostrar_validador(v: dict):
    """A4 paso 4: el validador de lógica tradicional, visible en CADA respuesta."""
    st.markdown("#### 🔎 Validador (lógica tradicional, corre en cada respuesta)")
    (st.success if v.get("ok") else st.warning)("Validador: OK" if v.get("ok") else "Validador: incompleto")
    cols = st.columns(4)
    etiquetas = {"registro_exitoso": "Registro exitoso", "correo_duplicado": "Correo duplicado",
                "contrasena_corta": "Contraseña < 8", "mensaje_confirmacion": "Mensaje confirmación"}
    for col, (clave, nombre) in zip(cols, etiquetas.items()):
        ok = v.get("escenarios_registro", {}).get(clave)
        col.metric(nombre, "✅" if ok else "—")
    st.caption(f"pytest compila: {'✅' if v.get('pytest_compila') else '❌ ' + str(v.get('pytest_detalle'))} · "
              f"sin información externa: {'✅' if v.get('sin_informacion_externa') else '❌'}")


# ───────────────────────────── sesión ─────────────────────────────
s, salud = llamar("GET", "/salud")
st.sidebar.markdown(f"**Servicio:** {API}  \n" + (f"**Modelo:** {salud.get('llm')}  \n**Variante:** {salud.get('variante')}"
                                                  if s == 200 else "🔴 sin conexión"))
if not st.session_state.get("token"):
    st.sidebar.subheader("Iniciar sesión")
    email = st.sidebar.text_input("Correo")
    contrasena = st.sidebar.text_input("Contraseña", type="password")
    c1, c2 = st.sidebar.columns(2)
    if c1.button("Entrar", use_container_width=True):
        st_, cuerpo = llamar("POST", "/auth/login", json={"email": email, "contrasena": contrasena})
        if st_ == 200:
            st.session_state["token"] = cuerpo["token"]
            st.rerun()
        else:
            mostrar_error(st_, cuerpo)
    if c2.button("Registrarme", use_container_width=True):
        st_, cuerpo = llamar("POST", "/auth/registro", json={"email": email, "contrasena": contrasena})
        st.sidebar.success("Cuenta creada; ahora entra.") if st_ == 201 else mostrar_error(st_, cuerpo)
    st.title("🧪 FinNorte · v1-qa")
    st.info("Inicia sesión para usar el asistente. Tu token dura 15 minutos.")
    st.stop()

if st.sidebar.button("Cerrar sesión"):
    st.session_state.clear()
    st.rerun()
modo = st.sidebar.radio("Modo", ["Mi variante (v1-qa)", "Agente (ejecutar_pytest)"])
st.sidebar.caption("Ficticio · uso educativo · LSCA2318 · A4")

# ───────────────────────────── Mi variante ─────────────────────────────
if modo == "Mi variante (v1-qa)":
    st.title("🧩 Mi variante · v1-qa")
    st.caption("Entra un requisito (RFxx); genero casos Gherkin + revisión + pytest, con fuentes del corpus.")
    requisito = st.text_area("Requisito", height=160,
                             placeholder="RF01 · Registro de usuarios\nRF01.1 El correo debe ser único.\n"
                                        "RF01.2 La contraseña debe tener al menos 8 caracteres.\n"
                                        "RF01.3 Al completar el registro se envía un mensaje de confirmación.")
    if st.button("Ejecutar", type="primary", disabled=len(requisito.strip()) < 10):
        with st.spinner("Recuperando contexto, corriendo el flujo de 4 etapas y validando…"):
            st_, out = llamar("POST", "/v1/qa", json={"requisito": requisito})
        if st_ != 200:
            mostrar_error(st_, out)
        else:
            (st.warning if out.get("abstuvo") else st.success)(out.get("respuesta", ""))
            if out.get("fuentes"):
                with st.expander(f"Fuentes ({len(out['fuentes'])})"):
                    st.write(out["fuentes"])
            if out.get("artefacto"):
                with st.expander("Artefacto estructurado (casos, revisión, pytest)"):
                    st.json(out["artefacto"])
            if out.get("errores_citas"):
                st.error(f"Citas con problema: {out['errores_citas']}")
            st.caption(f"⏱ {out.get('latencia_ms', 0):.0f} ms · 💲 US${out.get('costo_usd', 0):.5f}")
            if out.get("validador"):
                mostrar_validador(out["validador"])

# ───────────────────────────── Agente ─────────────────────────────
else:
    st.title("🤖 Agente · ejecutar_pytest con confirmación humana")
    st.caption("1) Genera el pytest en «Mi variante». 2) Aquí pide al agente que lo corra: "
              "ejecutar_pytest es SENSIBLE, así que no corre nada hasta que tú lo autorizas.")
    tarea = st.text_area("Tarea", "Corre el pytest que generó mi variante: test_rf01.py")
    if st.button("Ejecutar agente", type="primary"):
        with st.spinner("El agente está trabajando (cada paso es una llamada al modelo)…"):
            st_, out = llamar("POST", "/v1/agente", json={"tarea": tarea})
        if st_ != 200:
            mostrar_error(st_, out)
        else:
            st.session_state["agente"] = out
    out = st.session_state.get("agente")
    if out:
        (st.success if out["terminado"] else st.error)(out["respuesta"])
        v = out["validador"]
        (st.success if v["ok"] else st.error)("Validador del plan: OK" if v["ok"] else "Validador del plan: " + " · ".join(v["hallazgos"]))
        for p in out["pasos"]:
            with st.expander(f"Paso {p['n']} · {p['accion']} {p['herramienta'] or ''} · {p['estado']}"):
                st.json(p)
        for p in out["pendientes"]:
            st.warning(f"**Acción pendiente:** `{p['herramienta']}`")
            st.json(p["argumentos"])                         # los datos EXACTOS que se van a ejecutar
            c1, c2 = st.columns(2)
            for col, aprobar, etiqueta in ((c1, True, "✅ Autorizar"), (c2, False, "⛔ Rechazar")):
                if col.button(etiqueta, key=f"{p['id']}-{aprobar}", use_container_width=True):
                    st_, r = llamar("POST", f"/v1/agente/confirmar/{p['id']}", json={"aprobar": aprobar})
                    if st_ != 200:
                        mostrar_error(st_, r)
                    else:
                        st.session_state["agente"]["pendientes"] = []
                        st.session_state["ultimo"] = r
                        st.rerun()
        if st.session_state.get("ultimo"):
            r = st.session_state["ultimo"]
            (st.success if r["estado"] == "ejecutada" else st.info)(f"Acción {r['estado']}: {r.get('resultado', r.get('argumentos'))}")
