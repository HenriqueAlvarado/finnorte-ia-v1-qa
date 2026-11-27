import pytest
from fastapi.testclient import TestClient

from finnorte import llm


@pytest.fixture
def entorno(monkeypatch, tmp_path):
    monkeypatch.setenv("TOKEN_SECRET", "x" * 40)
    monkeypatch.setenv("AUTH_DB", str(tmp_path / "usuarios.db"))
    monkeypatch.setenv("LLM_PROVIDER", "fake")

    import api.producto as servicio

    servicio.auth = servicio.Autenticador(
        str(tmp_path / "usuarios.db")
    )
    servicio._ventanas.clear()
    monkeypatch.setattr(servicio, "LIMITE_POR_MINUTO", 30)

    resultado = {
        "respuesta": "Se generaron escenarios de prueba.",
        "fuentes": ["qa-06"],
        "abstuvo": False,
        "errores_citas": [],
        "artefacto": {"casos": []},
        "costo_usd": 0.0,
        "latencia_ms": 10.0
    }

    llamadas = []

    def motor(entrada):
        llamadas.append(entrada)
        return resultado

    monkeypatch.setattr(servicio.variante, "sistema", motor)

    return servicio, TestClient(servicio.app), llamadas, resultado


def autenticar(cliente):
    credenciales = {
        "email": "gera.a3@finnorte.test",
        "contrasena": "GeraSegura2026!"
    }

    registro = cliente.post("/auth/registro", json=credenciales)
    assert registro.status_code == 201

    respuesta = cliente.post("/auth/login", json=credenciales)
    assert respuesta.status_code == 200

    return {
        "Authorization": "Bearer " + respuesta.json()["token"]
    }


def test_endpoint_exige_token(entorno):
    _, cliente, _, _ = entorno

    respuesta = cliente.post(
        "/v1/v1-qa",
        json={"requisito": "El sistema debe permitir registrar usuarios."}
    )

    assert respuesta.status_code == 401
    assert respuesta.headers["content-type"].startswith(
        "application/problem+json"
    )


def test_endpoint_invoca_motor_de_variante(entorno):
    _, cliente, llamadas, resultado = entorno
    headers = autenticar(cliente)

    requisito = "El sistema debe permitir registrar usuarios."

    respuesta = cliente.post(
        "/v1/v1-qa",
        json={"requisito": requisito},
        headers=headers
    )

    assert respuesta.status_code == 200
    assert llamadas == [{"requisito": requisito}]
    assert respuesta.json() == resultado


def test_endpoint_valida_entrada(entorno):
    _, cliente, _, _ = entorno
    headers = autenticar(cliente)

    respuesta = cliente.post(
        "/v1/v1-qa",
        json={"requisito": "corto"},
        headers=headers
    )

    assert respuesta.status_code == 422
    assert respuesta.headers["content-type"].startswith(
        "application/problem+json"
    )


def test_endpoint_convierte_error_de_motor(entorno, monkeypatch):
    servicio, cliente, _, _ = entorno
    headers = autenticar(cliente)

    def motor_invalido(entrada):
        raise ValueError("Requisito no válido")

    monkeypatch.setattr(
        servicio.variante,
        "sistema",
        motor_invalido
    )

    respuesta = cliente.post(
        "/v1/v1-qa",
        json={"requisito": "El sistema debe registrar usuarios."},
        headers=headers
    )

    assert respuesta.status_code == 422
    assert respuesta.headers["content-type"].startswith(
        "application/problem+json"
    )


def test_endpoint_aplica_limite_por_usuario(entorno, monkeypatch):
    servicio, cliente, _, _ = entorno
    monkeypatch.setattr(servicio, "LIMITE_POR_MINUTO", 1)
    headers = autenticar(cliente)

    datos = {
        "requisito": "El sistema debe permitir registrar usuarios."
    }

    primera = cliente.post(
        "/v1/v1-qa",
        json=datos,
        headers=headers
    )
    segunda = cliente.post(
        "/v1/v1-qa",
        json=datos,
        headers=headers
    )

    assert primera.status_code == 200
    assert segunda.status_code == 429
    assert segunda.headers["content-type"].startswith(
        "application/problem+json"
    )
