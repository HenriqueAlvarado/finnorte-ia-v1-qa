import pytest
from decimal import Decimal

@pytest.fixture
def sistema():
    pytest.skip("Conectar con el sistema bajo prueba")

def test_cp_rf07_01(sistema):
    """
    id_caso: CP-RF07-01
    requisito: @RF07
    tipo: positivo
    regla_citada: REG-RF07-07
    """
    # Dado un usuario con correo 'usuario@dominio.com' y contraseña 'a1bcdefg'
    # Cuando el usuario intenta registrarse
    resultado = sistema.registrar(correo='usuario@dominio.com', password='a1bcdefg')
    # Entonces se muestra el mensaje 'Registro exitoso. Revisa tu correo para activar tu cuenta'
    assert resultado == 'Registro exitoso. Revisa tu correo para activar tu cuenta'

def test_cp_rf07_02(sistema):
    """
    id_caso: CP-RF07-02
    requisito: @RF07
    tipo: negativo
    regla_citada: REG-RF07-02
    """
    # Dado un correo 'usuario@dominio.com' ya registrado en el sistema
    # Cuando el usuario intenta registrarse con el mismo correo
    resultado = sistema.registrar(correo='usuario@dominio.com', password='a1bcdefg')
    # Entonces se muestra el mensaje 'No pudimos completar el registro con esos datos'
    assert resultado == 'No pudimos completar el registro con esos datos'

def test_cp_rf07_03(sistema):
    """
    id_caso: CP-RF07-03
    requisito: @RF07
    tipo: limite
    regla_citada: REG-RF07-03
    """
    # Dado un usuario con correo 'nuevo@dominio.com' y contraseña 'a1bcdefg'
    # Cuando el usuario intenta registrarse
    resultado = sistema.registrar(correo='nuevo@dominio.com', password='a1bcdefg')
    # Entonces se muestra el mensaje 'Registro exitoso. Revisa tu correo para activar tu cuenta'
    assert resultado == 'Registro exitoso. Revisa tu correo para activar tu cuenta'

def test_cp_rf07_04(sistema):
    """
    id_caso: CP-RF07-04
    requisito: @RF07
    tipo: negativo
    regla_citada: REG-RF07-03
    """
    # Dado un usuario con correo 'nuevo@dominio.com' y contraseña 'a1bcdef'
    # Cuando el usuario intenta registrarse
    resultado = sistema.registrar(correo='nuevo@dominio.com', password='a1bcdef')
    # Entonces SUPUESTO: el sistema debe rechazar el registro, falta confirmar el mensaje de error exacto con el dueño del producto
    assert resultado == "SUPUESTO: el sistema debe rechazar el registro"

def test_cp_rf07_05(sistema):
    """
    id_caso: CP-RF07-05
    requisito: @RF07
    tipo: limite
    regla_citada: REG-RF07-09
    """
    # Dado un dispositivo que ya ha registrado 3 cuentas en las últimas 24 horas
    # Cuando el usuario intenta registrar una cuarta cuenta
    resultado = sistema.registrar(correo='cuarta@dominio.com', password='password123')
    # Entonces SUPUESTO: el sistema debe rechazar el registro, falta confirmar el mensaje de error exacto con el dueño del producto
    assert resultado == "SUPUESTO: el sistema debe rechazar el registro"