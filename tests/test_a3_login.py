import pytest

from api.auth import hash_contrasena
from a3 import login_seguridad, login_eficiencia, login_mantenible

VERSIONES = [
    login_seguridad,
    login_eficiencia,
    login_mantenible,
]


@pytest.fixture
def usuarios():
    return {
        "admin": hash_contrasena("1234")
    }


@pytest.mark.parametrize("modulo", VERSIONES)
def test_login_exitoso(modulo, usuarios):
    assert modulo.login("admin", "1234", usuarios) == "access granted"


@pytest.mark.parametrize("modulo", VERSIONES)
def test_contrasena_incorrecta(modulo, usuarios):
    assert modulo.login("admin", "incorrecta", usuarios) == (
        "Correo o contraseña incorrectos"
    )


@pytest.mark.parametrize("modulo", VERSIONES)
def test_usuario_inexistente(modulo, usuarios):
    assert modulo.login("nadie", "1234", usuarios) == (
        "Correo o contraseña incorrectos"
    )


@pytest.mark.parametrize("modulo", VERSIONES)
def test_mensaje_uniforme(modulo, usuarios):
    incorrecta = modulo.login("admin", "mala", usuarios)
    inexistente = modulo.login("nadie", "1234", usuarios)
    assert incorrecta == inexistente


@pytest.mark.parametrize("modulo", VERSIONES)
def test_entrada_invalida(modulo, usuarios):
    assert modulo.login(None, "1234", usuarios) == (
        "Correo o contraseña incorrectos"
    )
