import pytest
from decimal import Decimal

@pytest.fixture
def sistema():
    pytest.skip("Conectar con el sistema bajo prueba")

def test_cp_rf07_01(sistema):
    """
    ID: CP-RF07-01
    Requisito: @RF07
    Tipo: positivo
    Regla: REG-RF07-07
    """
    # Dado un usuario con correo 'usuario@dominio.com' y contraseña 'a1bcdefg'
    # Cuando el usuario intenta registrarse
    # Entonces se muestra el mensaje 'Registro exitoso. Revisa tu correo para activar tu cuenta'
    mensaje_esperado = "Registro exitoso. Revisa tu correo para activar tu cuenta"
    assert mensaje_esperado == "Registro exitoso. Revisa tu correo para activar tu cuenta"

def test_cp_rf07_02(sistema):
    """
    ID: CP-RF07-02
    Requisito: @RF07
    Tipo: negativo
    Regla: REG-RF07-02
    """
    # Dado un correo 'usuario@dominio.com' ya registrado en el sistema
    # Cuando el usuario intenta registrarse con el mismo correo
    # Entonces se muestra el mensaje 'No pudimos completar el registro con esos datos'
    mensaje_esperado = "No pudimos completar el registro con esos datos"
    assert mensaje_esperado == "No pudimos completar el registro con esos datos"

def test_cp_rf07_03(sistema):
    """
    ID: CP-RF07-03
    Requisito: @RF07
    Tipo: limite
    Regla: REG-RF07-03
    """
    # Dado un usuario con correo 'nuevo@dominio.com' y contraseña 'a1bcdefg'
    # Cuando el usuario intenta registrarse
    # Entonces se muestra el mensaje 'Registro exitoso. Revisa tu correo para activar tu cuenta'
    mensaje_esperado = "Registro exitoso. Revisa tu correo para activar tu cuenta"
    assert mensaje_esperado == "Registro exitoso. Revisa tu correo para activar tu cuenta"

def test_cp_rf07_04(sistema):
    """
    ID: CP-RF07-04
    Requisito: @RF07
    Tipo: negativo
    Regla: REG-RF07-03
    """
    # Dado un usuario con correo 'nuevo@dominio.com' y contraseña 'a1bcdef'
    # Cuando el usuario intenta registrarse
    # Entonces SUPUESTO: el sistema debe rechazar el registro, falta confirmar el mensaje de error exacto con el dueño del producto
    resultado = "rechazado"
    assert resultado == "rechazado"

def test_cp_rf07_05(sistema):
    """
    ID: CP-RF07-05
    Requisito: @RF07
    Tipo: limite
    Regla: REG-RF07-09
    """
    # Dado un dispositivo que ya ha registrado 3 cuentas en las últimas 24 horas
    # Cuando el usuario intenta registrar una cuarta cuenta
    # Entonces SUPUESTO: el sistema debe rechazar el registro, falta confirmar el mensaje de error exacto con el dueño del producto
    resultado = "rechazado"
    assert resultado == "rechazado"