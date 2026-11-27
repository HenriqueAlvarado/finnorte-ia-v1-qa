"""A3 · paso 5: las 3 pruebas mínimas del texto oficial (login exitoso, contraseña
incorrecta, usuario inexistente) a nivel de SERVICIO (no solo la función de ejemplo, que ya
se prueba en test_a3_login_versiones.py) + mis 3 propias: token expirado, token alterado,
entrada inválida (422) — el bloqueo por intentos ya está cubierto en
tests/test_lab_producto.py::test_bloqueo_tras_5_intentos y no se repite aquí.
"""
import time

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from finnorte import llm  # noqa: E402

CRED = {"email": "a3@finnorte.mx", "contrasena": "segura123"}


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_SECRET", "x" * 40)
    monkeypatch.setenv("AUTH_DB", str(tmp_path / "u.db"))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setattr(llm.fake, "responder", None)
    import api.producto as m
    m.auth = m.Autenticador(str(tmp_path / "u.db"))
    m._ventanas.clear()
    return TestClient(m.app)


def _ok(r):
    if r.status_code == 501:
        pytest.skip(r.json()["detail"])
    return r


# ---------- las 3 mínimas del texto oficial, a nivel /auth/login ----------
def test_login_exitoso(cliente):
    _ok(cliente.post("/auth/registro", json=CRED))
    r = _ok(cliente.post("/auth/login", json=CRED))
    assert r.status_code == 200 and "token" in r.json()


def test_contrasena_incorrecta(cliente):
    _ok(cliente.post("/auth/registro", json=CRED))
    r = cliente.post("/auth/login", json={**CRED, "contrasena": "otra12345"})
    assert r.status_code == 401


def test_usuario_inexistente(cliente):
    r = cliente.post("/auth/login", json={"email": "no-existe@finnorte.mx", "contrasena": "segura123"})
    assert r.status_code == 401


# ---------- mis 3 propias ----------
def test_propia_token_expirado_401(cliente):
    _ok(cliente.post("/auth/registro", json=CRED))
    from api import auth
    viejo = auth.emitir_token(CRED["email"], ahora=time.time() - 16 * 60)
    r = cliente.post("/v1/qa", json={"requisito": "RF12 requisito de prueba suficientemente largo"},
                     headers={"Authorization": f"Bearer {viejo}"})
    assert r.status_code == 401 and "expirado" in r.json()["detail"]
    assert r.headers["content-type"].startswith("application/problem+json")


def test_propia_token_alterado_401(cliente):
    _ok(cliente.post("/auth/registro", json=CRED))
    token = _ok(cliente.post("/auth/login", json=CRED)).json()["token"]
    alterado = token[:-2] + "xx"
    r = cliente.post("/v1/qa", json={"requisito": "RF12 requisito de prueba suficientemente largo"},
                     headers={"Authorization": f"Bearer {alterado}"})
    assert r.status_code == 401


def test_propia_entrada_invalida_422(cliente):
    _ok(cliente.post("/auth/registro", json=CRED))
    h = {"Authorization": "Bearer " + _ok(cliente.post("/auth/login", json=CRED)).json()["token"]}
    r = cliente.post("/v1/qa", json={"requisito": "corto"}, headers=h)   # menos de 10 caracteres
    assert r.status_code == 422 and r.headers["content-type"].startswith("application/problem+json")


def test_propia_sin_token_401(cliente):
    r = cliente.post("/v1/qa", json={"requisito": "RF12 requisito de prueba suficientemente largo"})
    assert r.status_code == 401
