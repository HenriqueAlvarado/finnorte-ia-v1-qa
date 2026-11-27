"""A3 · paso 3: POST /v1/qa — mi endpoint de variante (requisito #2 de la actividad):
protegido por token, usa variante.sistema() (el motor real, no el demo), y aplica el
límite de solicitudes por minuto ya presente en usuario_actual()."""
import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from finnorte import llm  # noqa: E402

CRED = {"email": "a3b@finnorte.mx", "contrasena": "segura123"}
REQUISITO = "RF12 · Transferencia SPEI\nRF12.4 Una solicitud repetida no deberá generar un doble cargo."


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_SECRET", "x" * 40)
    monkeypatch.setenv("AUTH_DB", str(tmp_path / "u.db"))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("API_LIMITE", "3")
    monkeypatch.setattr(llm.fake, "responder", None)
    import api.producto as m
    m.auth = m.Autenticador(str(tmp_path / "u.db"))
    m._ventanas.clear()
    monkeypatch.setattr(m, "LIMITE_POR_MINUTO", 3)   # setattr, no asignación directa: se revierte solo
    return TestClient(m.app)


def _ok(r):
    if r.status_code == 501:
        pytest.skip(r.json()["detail"])
    return r


def _token(c):
    _ok(c.post("/auth/registro", json=CRED))
    return {"Authorization": "Bearer " + _ok(c.post("/auth/login", json=CRED)).json()["token"]}


def test_endpoint_usa_el_motor_real_de_la_variante_y_corre_el_validador(cliente):
    h = _token(cliente)
    r = _ok(cliente.post("/v1/qa", json={"requisito": REQUISITO}, headers=h))
    assert r.status_code == 200
    body = r.json()
    assert {"respuesta", "fuentes", "abstuvo", "artefacto", "validador"} <= set(body)
    assert "cubre_los_4_escenarios" in body["validador"]


def test_endpoint_limita_la_tasa_de_solicitudes(cliente):
    h = _token(cliente)
    for _ in range(3):
        _ok(cliente.post("/v1/qa", json={"requisito": REQUISITO}, headers=h))
    r = cliente.post("/v1/qa", json={"requisito": REQUISITO}, headers=h)
    assert r.status_code == 429
    assert r.headers["content-type"].startswith("application/problem+json")
