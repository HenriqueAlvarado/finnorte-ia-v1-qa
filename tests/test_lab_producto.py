"""Pruebas del Laboratorio A3 + A4 (kit v2). Corren sin red (LLM_PROVIDER=fake).

Solo dependen de lo que el laboratorio enseña:
  · la base resuelta del caso guía (src/finnorte/caso_guia/)
  · las 5 funciones TODO(LAB) de api/auth.py que completas tú

Resultado esperado:
  · sin completar api/auth.py → 3 passed, 9 skipped (el motivo dice qué función falta)
  · con api/auth.py completo  → 12 passed

Para la A3 y la A4 escribe tus propias pruebas en tests/test_a3_*.py y tests/test_a4_*.py.
"""
import json
import time

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from finnorte import llm, trazas  # noqa: E402
from finnorte.caso_guia.herramientas import TICKETS  # noqa: E402

CRED = {"email": "ana@finnorte.mx", "contrasena": "segura123"}
TAREA_MARTES = "Quiero desplegar un cambio de riesgo alto en pagos-api el 2026-11-24. Si se puede, crea el ticket."
TAREA_VIERNES = "Quiero desplegar un cambio de riesgo alto en pagos-api el 2026-11-27. Si se puede, crea el ticket."


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_SECRET", "x" * 40)
    monkeypatch.setenv("AUTH_DB", str(tmp_path / "u.db"))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setattr(llm.fake, "responder", None)      # guion simulado del caso guía
    import api.producto as m
    m.auth = m.Autenticador(str(tmp_path / "u.db"))
    m._ventanas.clear()
    TICKETS.clear()
    return TestClient(m.app)


def _ok(r):
    """501 = pieza del laboratorio pendiente: la prueba se OMITE y el motivo dice qué función falta."""
    if r.status_code == 501:
        pytest.skip(r.json()["detail"])
    return r


def _token(c, cred=CRED):
    _ok(c.post("/auth/registro", json=cred))
    return {"Authorization": "Bearer " + _ok(c.post("/auth/login", json=cred)).json()["token"]}


# ───────────── no dependen de api/auth.py (Checkpoint 1) ─────────────
def test_salud(cliente):
    assert cliente.get("/salud").json()["estado"] == "ok"


def test_sin_token_401_problem_json(cliente):
    r = cliente.post("/v1/preguntas", json={"pregunta": "¿Cada cuánto se rotan los secretos?"})
    assert r.status_code == 401 and r.headers["content-type"].startswith("application/problem+json")
    assert {"type", "title", "status", "detail", "trace_id"} <= set(r.json())


def test_entrada_invalida_422(cliente):
    r = cliente.post("/auth/registro", json={"email": "malo", "contrasena": "x"})
    assert r.status_code == 422 and r.headers["content-type"].startswith("application/problem+json")


# ───────────── dependen de api/auth.py (Checkpoint 2) ─────────────
def test_mismo_mensaje_usuario_inexistente_y_contrasena_mala(cliente):
    _ok(cliente.post("/auth/registro", json=CRED))
    a = _ok(cliente.post("/auth/login", json={**CRED, "contrasena": "mala12345"})).json()
    b = _ok(cliente.post("/auth/login", json={"email": "nadie@finnorte.mx", "contrasena": "segura123"})).json()
    assert a["status"] == b["status"] == 401 and a["detail"] == b["detail"]


def test_token_alterado_y_expirado(cliente):
    h = _token(cliente)
    alterado = {"Authorization": h["Authorization"][:-2] + "xx"}
    assert cliente.post("/v1/preguntas", json={"pregunta": "hola hola"}, headers=alterado).status_code == 401
    from api import auth
    viejo = auth.emitir_token(CRED["email"], ahora=time.time() - 16 * 60)
    r = cliente.post("/v1/preguntas", json={"pregunta": "hola hola"}, headers={"Authorization": f"Bearer {viejo}"})
    assert r.status_code == 401 and "expirado" in r.json()["detail"]


def test_bloqueo_tras_5_intentos(cliente):
    _ok(cliente.post("/auth/registro", json=CRED))
    for _ in range(5):
        _ok(cliente.post("/auth/login", json={**CRED, "contrasena": "mala12345"}))
    assert cliente.post("/auth/login", json=CRED).status_code == 429


def test_contrasena_no_se_guarda_en_texto_plano(cliente):
    _ok(cliente.post("/auth/registro", json=CRED))
    import api.producto as m
    guardado = m.auth.db.execute("SELECT hash FROM usuarios").fetchone()[0]
    assert CRED["contrasena"] not in guardado and guardado.startswith("pbkdf2$")


# ───────────── el producto completo (Checkpoint 3) ─────────────
def test_pregunta_del_caso_guia_con_fuentes(cliente):
    r = _ok(cliente.post("/v1/preguntas", json={"pregunta": "¿Cada cuánto se rotan los secretos?"}, headers=_token(cliente)))
    assert r.status_code == 200 and r.json()["fuentes"] and not r.json()["abstuvo"]


def test_agente_deja_pendiente_y_rechazo_no_ejecuta(cliente):
    h = _token(cliente)
    r = _ok(cliente.post("/v1/agente", json={"tarea": TAREA_MARTES}, headers=h)).json()
    assert r["validador"]["ok"] and len(r["pendientes"]) == 1 and TICKETS == []
    p = r["pendientes"][0]
    assert p["herramienta"] == "crear_ticket_cambio" and p["argumentos"]["fecha"] == "2026-11-24"
    out = cliente.post(f"/v1/agente/confirmar/{p['id']}", json={"aprobar": False}, headers=h).json()
    assert out["estado"] == "rechazada" and TICKETS == []
    assert any(e.get("estado") == "rechazada" for e in trazas.leer("agente"))


def test_agente_confirmado_ejecuta_exactamente_lo_aprobado_una_vez(cliente):
    h = _token(cliente)
    p = _ok(cliente.post("/v1/agente", json={"tarea": TAREA_MARTES}, headers=h)).json()["pendientes"][0]
    out = cliente.post(f"/v1/agente/confirmar/{p['id']}", json={"aprobar": True}, headers=h).json()
    assert out["estado"] == "ejecutada" and TICKETS[0]["fecha"] == "2026-11-24"
    assert cliente.post(f"/v1/agente/confirmar/{p['id']}", json={"aprobar": True}, headers=h).status_code == 404


def test_viernes_no_deja_nada_que_autorizar(cliente):
    h = _token(cliente)
    r = _ok(cliente.post("/v1/agente", json={"tarea": TAREA_VIERNES}, headers=h)).json()
    assert r["pendientes"] == [] and TICKETS == []


def test_otro_usuario_no_puede_confirmar(cliente):
    h = _token(cliente)
    p = _ok(cliente.post("/v1/agente", json={"tarea": TAREA_MARTES}, headers=h)).json()["pendientes"][0]
    h2 = _token(cliente, {"email": "beto@finnorte.mx", "contrasena": "segura456"})
    assert cliente.post(f"/v1/agente/confirmar/{p['id']}", json={"aprobar": True}, headers=h2).status_code == 404
