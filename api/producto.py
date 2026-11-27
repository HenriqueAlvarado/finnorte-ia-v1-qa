"""Servicio HTTP del producto (Laboratorio A3+A4).   uvicorn api.producto:app --reload   →  http://127.0.0.1:8000/docs

Archivo NUEVO del kit: no reemplaza tu api/main.py.
Base resuelta del laboratorio: el caso guía (src/finnorte/caso_guia/). Lo que completas tú:
  · Laboratorio y A3: las 5 funciones TODO(LAB) de api/auth.py
  · A3: tu endpoint POST /v1/<tu-variante> con su propio modelo de entrada, conectado a tu motor
  · A4: tus herramientas y tu ejecutor (ver _herramientas() y agente())

Endpoints
  GET  /salud                                estado, proveedor y modelo (sin token)
  POST /auth/registro   {"email","contrasena"} crea usuario (contraseña con hash y sal)
  POST /auth/login      {"email","contrasena"} → {"token", "tipo": "Bearer", "expira_en_s"}
  POST /v1/preguntas    {"pregunta"}          caso guía: respuesta con citas (requiere token)
  POST /v1/variante     {"entrada": {...}}    tu variante.sistema(); si aún no existe, motor DEMO (requiere token)
  POST /v1/agente       {"tarea"}             agente con herramientas; lo sensible queda PENDIENTE    ← A4
  POST /v1/agente/confirmar/{id} {"aprobar"}   confirmación humana con los datos exactos               ← A4

Todos los errores salen en problem+json (ing-07). Límite de solicitudes por usuario y por minuto.
"""
from __future__ import annotations

import os
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from api.auth import VIGENCIA_S, Autenticador, ErrorAuth, validar_token
from finnorte import agente_servicio, herramientas, llm, qa_herramientas, variante
from finnorte.caso_guia import asistente as caso_guia
from finnorte.caso_guia import motor_demo
from finnorte.config import RAIZ, config
from finnorte.validador_v1qa import validar_variante_v1qa

app = FastAPI(title="FinNorte · Producto (servicio con token + Gemini + agente)", version="2.0")
auth = Autenticador(os.getenv("AUTH_DB", str(RAIZ / "bitacora" / "usuarios.db")))
_ventanas: dict[str, list[float]] = {}
LIMITE_POR_MINUTO = int(os.getenv("API_LIMITE", "30"))


# ───────────────────────────── errores problem+json (ing-07) ─────────────────────────────
def problema(status: int, title: str, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, media_type="application/problem+json",
                        content={"type": f"https://docs.finnorte.mx/errores/{status}", "title": title,
                                 "status": status, "detail": detail, "trace_id": uuid.uuid4().hex[:12]})


class ErrorHTTP(Exception):
    def __init__(self, status, title, detail):
        self.status, self.title, self.detail = status, title, detail


@app.exception_handler(ErrorHTTP)
async def _manejar(_: Request, e: ErrorHTTP):
    return problema(e.status, e.title, e.detail)


@app.exception_handler(RequestValidationError)
async def _validacion(_: Request, e: RequestValidationError):
    detalle = "; ".join(f"{'.'.join(str(x) for x in err['loc'][1:])}: {err['msg']}" for err in e.errors())[:300]
    return problema(422, "Entrada inválida", detalle)


@app.exception_handler(NotImplementedError)
async def _pendiente(_: Request, e: NotImplementedError):
    return problema(501, "Pieza pendiente", f"{e} · complétala siguiendo el manual del laboratorio")


TITULOS = {401: "No autorizado", 409: "Conflicto", 422: "Entrada inválida", 429: "Demasiadas solicitudes"}


def _de_auth(e: ErrorAuth) -> ErrorHTTP:
    return ErrorHTTP(e.status, TITULOS.get(e.status, "Error"), str(e))


# ───────────────────────────── autenticación ─────────────────────────────
class Credenciales(BaseModel):
    email: str = Field(min_length=5, max_length=120)
    contrasena: str = Field(min_length=1, max_length=128)


@app.post("/auth/registro", status_code=201)
def registro(c: Credenciales):
    try:
        auth.registrar(c.email, c.contrasena)
    except ErrorAuth as e:
        raise _de_auth(e)
    return {"mensaje": "Registro exitoso"}


@app.post("/auth/login")
def login(c: Credenciales):
    try:
        return {"token": auth.login(c.email, c.contrasena), "tipo": "Bearer", "expira_en_s": VIGENCIA_S}
    except ErrorAuth as e:
        raise _de_auth(e)


_bearer = HTTPBearer(auto_error=False, description="Pega aquí SOLO el token de /auth/login (sin la palabra Bearer)")


def usuario_actual(cred: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> str:
    """Dependencia: exige 'Authorization: Bearer <token>' válido y aplica el límite por usuario.
    HTTPBearer hace que /docs muestre el botón Authorize (candado)."""
    if cred is None or cred.scheme.lower() != "bearer":
        raise ErrorHTTP(401, "No autorizado", "Falta la cabecera Authorization: Bearer <token>")
    try:
        usuario = validar_token(cred.credentials.strip())
    except ErrorAuth as e:
        raise _de_auth(e)
    ahora = time.time()
    ventana = [t for t in _ventanas.get(usuario, []) if ahora - t < 60]
    if len(ventana) >= LIMITE_POR_MINUTO:
        raise ErrorHTTP(429, "Demasiadas solicitudes", f"Límite de {LIMITE_POR_MINUTO} por minuto")
    _ventanas[usuario] = ventana + [ahora]
    return usuario


# ───────────────────────────── endpoints del producto ─────────────────────────────
@app.get("/salud")
def salud():
    c = config()
    return {"estado": "ok", "llm": f"{c.llm_proveedor}/{c.llm_modelo}", "embeddings": c.emb_proveedor,
            "variante": variante.VARIANTE, "caso_guia": "BM25 + agente de referencia"}


class Pregunta(BaseModel):
    pregunta: str = Field(min_length=3, max_length=500)


@app.post("/v1/preguntas")
def preguntar(p: Pregunta, usuario: str = Depends(usuario_actual)):
    try:
        out = caso_guia.responder(p.pregunta)
    except llm.LLMError as e:
        raise ErrorHTTP(503, "Proveedor del modelo no disponible", str(e)[:200])
    return {k: out[k] for k in ("respuesta", "fuentes", "abstuvo", "latencia_ms", "costo_usd")}


class EntradaVariante(BaseModel):
    entrada: dict = Field(description='La entrada de tu variante, p. ej. {"pregunta": "..."} o {"codigo": "..."}')


@app.post("/v1/variante")
def ejecutar_variante(e: EntradaVariante, usuario: str = Depends(usuario_actual)):
    """Llama a TU variante.sistema() (Avance 1). Si aún no existe, responde el motor DEMO ("motor": "demo").
    A3: crea además tu propio endpoint POST /v1/<tu-variante> con un modelo de entrada propio de tu variante."""
    try:
        try:
            out = variante.sistema(e.entrada)
        except NotImplementedError:
            out = motor_demo.sistema(e.entrada)
    except ValueError as err:
        raise ErrorHTTP(422, "Entrada inválida", str(err)[:200])
    except llm.LLMError as err:
        raise ErrorHTTP(503, "Proveedor del modelo no disponible", str(err)[:200])
    return out


class Tarea(BaseModel):
    tarea: str = Field(min_length=5, max_length=800)


class Decision(BaseModel):
    aprobar: bool


# A3 · mi endpoint de variante ────────────────────────────────────────────────────────────
class EntradaQA(BaseModel):
    """Entrada propia de v1-qa: un requisito funcional (RFxx) a analizar/generar casos+pytest."""
    requisito: str = Field(min_length=10, max_length=4000,
                           description='Ej. "RF12 · Transferencia SPEI\\nRF12.4 Una solicitud repetida no deberá generar un doble cargo."')
    version_prompt: int | None = Field(default=None, ge=1, le=2, description="1 o 2; por defecto usa la vigente (2)")
    usar_rag: bool | None = Field(default=None, description="A4: permite forzar RAG on/off para comparar mejoras")
    controles: bool | None = Field(default=None, description="A4: permite forzar verificacion de citas on/off para comparar mejoras")


@app.post("/v1/qa")
def ejecutar_qa(e: EntradaQA, usuario: str = Depends(usuario_actual)):
    """A3: MI endpoint de variante. Llama a variante.sistema() (el motor real del Avance 1,
    no el demo). Protegido por token (Depends(usuario_actual), que también aplica el límite
    de solicitudes por minuto) y con errores en problem+json (ing-07) vía ErrorHTTP."""
    cfg = {}
    if e.version_prompt:
        cfg["version_prompt"] = e.version_prompt
    if e.usar_rag is not None:
        cfg["usar_rag"] = e.usar_rag
    if e.controles is not None:
        cfg["controles"] = e.controles
    cfg = cfg or None
    try:
        out = variante.sistema({"requisito": e.requisito}, config=cfg)
    except ValueError as err:
        raise ErrorHTTP(422, "Entrada inválida", str(err)[:200])
    except llm.LLMError as err:
        raise ErrorHTTP(503, "Proveedor del modelo no disponible", str(err)[:200])
    # A4: si el flujo llegó a generar un pytest, lo dejo en el sandbox para que el agente
    # pueda correrlo después con mi herramienta ejecutar_pytest (ver qa_herramientas.py).
    etapa_pytest = (out.get("artefacto") or {}).get("pytest") or {}
    qa_herramientas.guardar_pytest_generado(etapa_pytest.get("nombre_archivo"), etapa_pytest.get("codigo_pytest"))
    out["validador"] = validar_variante_v1qa(out)   # A4 paso 4: corre en CADA respuesta
    return out


# A4 · agente de MI variante ──────────────────────────────────────────────────────────────
def _herramientas():
    return qa_herramientas.herramientas_v1qa()      # A4: mi herramienta (ejecutar_pytest)


@app.post("/v1/agente")
def agente(t: Tarea, usuario: str = Depends(usuario_actual)):
    try:
        return agente_servicio.iniciar(t.tarea, usuario, _herramientas(),
                                       ejecutor=herramientas.ejecutar_agente,
                                       validador=qa_herramientas.validar_plan_v1qa)
    except llm.LLMError as e:
        raise ErrorHTTP(503, "Proveedor del modelo no disponible", str(e)[:200])


@app.post("/v1/agente/confirmar/{id_}")
def confirmar(id_: str, d: Decision, usuario: str = Depends(usuario_actual)):
    try:
        return agente_servicio.resolver(id_, usuario, d.aprobar, _herramientas())
    except KeyError as e:
        raise ErrorHTTP(404, "Acción no encontrada", str(e))
