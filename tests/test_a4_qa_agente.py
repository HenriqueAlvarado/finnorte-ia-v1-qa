"""A4 · integración: el agente de MI variante (ejecutar_pytest) a través de /v1/agente,
con confirmación humana en dos pasos (mismo contrato del lab, mi herramienta y mi validador).
"""
import json

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from finnorte import llm, qa_herramientas  # noqa: E402

CRED = {"email": "qa@finnorte.mx", "contrasena": "segura123"}


@pytest.fixture
def cliente(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_SECRET", "x" * 40)
    monkeypatch.setenv("AUTH_DB", str(tmp_path / "u.db"))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    sandbox = tmp_path / "sandbox"
    monkeypatch.setattr(qa_herramientas, "SANDBOX_DIR", sandbox)
    import api.producto as m
    m.auth = m.Autenticador(str(tmp_path / "u.db"))
    m._ventanas.clear()
    llm.fake.responder = None
    return TestClient(m.app)


def _ok(r):
    if r.status_code == 501:
        pytest.skip(r.json()["detail"])
    return r


def _token(c):
    _ok(c.post("/auth/registro", json=CRED))
    return {"Authorization": "Bearer " + _ok(c.post("/auth/login", json=CRED)).json()["token"]}


def _guion_propone_y_responde(archivo="test_rf01.py"):
    it = iter([
        {"accion": "usar", "herramienta": "ejecutar_pytest", "argumentos": {"archivo": archivo}, "razon": "corro el pytest ya generado"},
        {"accion": "responder", "respuesta": "El pytest queda pendiente de tu autorización.", "fuentes": []},
    ])
    return lambda p, s: json.dumps(next(it))


def test_sin_archivo_generado_el_validador_bloquea_la_propuesta(cliente):
    """El archivo NUNCA se generó en el sandbox: validar_plan_v1qa lo bloquea, no hay pendientes."""
    h = _token(cliente)
    llm.fake.responder = _guion_propone_y_responde("test_rf01.py")
    r = _ok(cliente.post("/v1/agente", json={"tarea": "Corre el pytest generado test_rf01.py"}, headers=h)).json()
    assert not r["validador"]["ok"] and r["pendientes"] == []


def test_archivo_generado_queda_pendiente_y_confirmar_lo_ejecuta(cliente, tmp_path):
    h = _token(cliente)
    qa_herramientas.guardar_pytest_generado("test_rf01.py", "def test_cp_rf01_01():\n    assert 1 + 1 == 2\n")
    llm.fake.responder = _guion_propone_y_responde("test_rf01.py")
    r = _ok(cliente.post("/v1/agente", json={"tarea": "Corre el pytest generado test_rf01.py"}, headers=h)).json()
    assert r["validador"]["ok"] and len(r["pendientes"]) == 1
    p = r["pendientes"][0]
    assert p["herramienta"] == "ejecutar_pytest" and p["argumentos"]["archivo"] == "test_rf01.py"

    rechazo = cliente.post(f"/v1/agente/confirmar/{p['id']}", json={"aprobar": False}, headers=h).json()
    assert rechazo["estado"] == "rechazada"

    llm.fake.responder = _guion_propone_y_responde("test_rf01.py")
    p2 = _ok(cliente.post("/v1/agente", json={"tarea": "Corre el pytest generado test_rf01.py"}, headers=h)).json()["pendientes"][0]
    aprobado = cliente.post(f"/v1/agente/confirmar/{p2['id']}", json={"aprobar": True}, headers=h).json()
    assert aprobado["estado"] == "ejecutada" and aprobado["resultado"]["ok"] is True


def test_herramienta_inexistente_falla_y_el_agente_se_recupera(cliente):
    """Prueba de seguridad (A4 paso 6): el agente pide una herramienta que no existe
    (archivo inventado); el código la marca inválida y el agente no truena ni la ejecuta."""
    h = _token(cliente)
    it = iter([
        {"accion": "usar", "herramienta": "ejecutar_pytest", "argumentos": {"archivo": "test_rf99.py"}, "razon": "x"},
        {"accion": "responder", "respuesta": "No encontré ese pytest generado.", "fuentes": []},
    ])
    llm.fake.responder = lambda p, s: json.dumps(next(it))
    r = _ok(cliente.post("/v1/agente", json={"tarea": "Corre test_rf99.py, que no existe"}, headers=h)).json()
    assert not r["validador"]["ok"] and r["pendientes"] == []
    assert r["respuesta"] == "No encontré ese pytest generado."
