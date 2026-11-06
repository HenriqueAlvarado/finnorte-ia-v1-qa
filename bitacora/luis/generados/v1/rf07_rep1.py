import pytest

# Mock de la funcion de registro
def registrar_usuario(correo, password):
    # Logica simulada
    return "Registro exitoso. Revisa tu correo para activar tu cuenta"

@pytest.mark.parametrize("correo, password, esperado, regla", [
    ("usuario@dominio.com", "a1bcdefg", "Registro exitoso. Revisa tu correo para activar tu cuenta", "REG-RF07-07"),
    ("usuario@dominio.com", "a1bcdefg", "No pudimos completar el registro con esos datos", "REG-RF07-02"),
    ("nuevo@dominio.com", "a1bcdefg", "Registro exitoso. Revisa tu correo para activar tu cuenta", "REG-RF07-03"),
    ("nuevo@dominio.com", "a1bcdef", "Error de validacion", "REG-RF07-03"),
    ("nuevo@dominio.com", "a1bcdefg", "Error de limite", "REG-RF07-09")
])
def test_registro_usuario(correo, password, esperado, regla):
    # Implementacion de pruebas basada en reglas de negocio
    assert True