"""A3 · Pruebas del servicio: token expirado, token alterado, 422 y el endpoint POST /v1/qa. Sin red (proveedor fake)."""
import time

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from finnorte import llm  # noqa: E402

CRED = {"email": "qa@finnorte.mx", "contrasena": "segura123"}
REQ_1 = "RF12.2 El monto por operación no podrá exceder el límite de su nivel de cuenta"
REQ_2 = "RF07.1 El usuario debe poder consultar el saldo de sus cuentas activas"


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_SECRET", "x" * 40)
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setattr(llm.fake, "responder", None)
    import api.producto as m
    m.auth = m.Autenticador(str(tmp_path / "u.db"))
    m._ventanas.clear()
    return TestClient(m.app)


def _headers(c):
    c.post("/auth/registro", json=CRED)
    return {"Authorization": "Bearer " + c.post("/auth/login", json=CRED).json()["token"]}


def test_token_expirado_da_401(cliente):
    from api import auth
    viejo = auth.emitir_token(CRED["email"], ahora=time.time() - 16 * 60)
    r = cliente.post("/v1/qa", json={"requisito": REQ_1}, headers={"Authorization": f"Bearer {viejo}"})
    assert r.status_code == 401 and "expirado" in r.json()["detail"]


def test_token_alterado_da_401(cliente):
    h = _headers(cliente)
    r = cliente.post("/v1/qa", json={"requisito": REQ_1}, headers={"Authorization": h["Authorization"][:-2] + "xx"})
    assert r.status_code == 401 and r.headers["content-type"].startswith("application/problem+json")


def test_qa_sin_token_da_401_problem_json(cliente):
    r = cliente.post("/v1/qa", json={"requisito": REQ_1})
    assert r.status_code == 401
    assert {"type", "title", "status", "detail", "trace_id"} <= set(r.json())


@pytest.mark.parametrize("cuerpo", [{}, {"requisito": "corto"}, {"requisito": "x" * 2001}, {"pregunta": REQ_1}])
def test_qa_entrada_invalida_da_422(cliente, cuerpo):
    r = cliente.post("/v1/qa", json=cuerpo, headers=_headers(cliente))
    assert r.status_code == 422 and r.headers["content-type"].startswith("application/problem+json")


def test_qa_ignora_el_campo_archivo(cliente):
    """«archivo» haría leer archivos del servidor: el modelo de entrada no lo acepta y se ignora."""
    r = cliente.post("/v1/qa", json={"requisito": REQ_1, "archivo": "../../.env"}, headers=_headers(cliente))
    assert ".env" not in r.text and "TOKEN_SECRET" not in r.text


@pytest.mark.parametrize("requisito", [REQ_1, REQ_2])
def test_qa_con_dos_entradas_reales_responde_la_estructura_del_motor(cliente, requisito):
    r = cliente.post("/v1/qa", json={"requisito": requisito}, headers=_headers(cliente))
    assert r.status_code == 200, r.text
    assert {"respuesta", "fuentes", "abstuvo"} <= set(r.json())


def test_limite_de_solicitudes_da_429(cliente, monkeypatch):
    import api.producto as m
    monkeypatch.setattr(m, "LIMITE_POR_MINUTO", 2)
    h = _headers(cliente)
    codigos = [cliente.post("/v1/qa", json={"requisito": "x" * 5}, headers=h).status_code for _ in range(4)]
    assert 429 in codigos
