import pytest
from decimal import Decimal

@pytest.fixture
def sistema():
    pytest.skip("Conectar con el sistema bajo prueba")

def test_cp_rf07_01(sistema):
    """
    id_caso: CP-RF07-01
    etiqueta: @RF07
    tipo: positivo
    regla_citada: REG-RF07-07
    """
    # Dado un usuario con correo '<CORREO_SINTETICO_1>' y contraseña '<CONTRASENA_8_CARACTERES>'
    # Cuando el usuario intenta registrarse
    resultado = sistema.ejecutar("registrar", correo="<CORREO_SINTETICO_1>", password="<CONTRASENA_8_CARACTERES>")
    # Entonces se muestra el mensaje 'Registro exitoso. Revisa tu correo para activar tu cuenta'
    assert resultado["estado"] == "aceptada"
    assert resultado["mensaje"] == "Registro exitoso. Revisa tu correo para activar tu cuenta"

def test_cp_rf07_02(sistema):
    """
    id_caso: CP-RF07-02
    etiqueta: @RF07
    tipo: negativo
    regla_citada: REG-RF07-02
    """
    # Dado un correo '<CORREO_SINTETICO_1>' ya registrado en el sistema
    # Cuando el usuario intenta registrarse con el mismo correo
    resultado = sistema.ejecutar("registrar", correo="<CORREO_SINTETICO_1>", password="<CONTRASENA_8_CARACTERES>")
    # Entonces se muestra el mensaje 'No pudimos completar el registro con esos datos'
    assert resultado["estado"] == "rechazada"
    assert resultado["mensaje"] == "No pudimos completar el registro con esos datos"

def test_cp_rf07_03(sistema):
    """
    id_caso: CP-RF07-03
    etiqueta: @RF07
    tipo: limite
    regla_citada: REG-RF07-03
    """
    # Dado un usuario con correo '<CORREO_SINTETICO_2>' y contraseña '<CONTRASENA_8_CARACTERES>'
    # Cuando el usuario intenta registrarse
    resultado = sistema.ejecutar("registrar", correo="<CORREO_SINTETICO_2>", password="<CONTRASENA_8_CARACTERES>")
    # Entonces se muestra el mensaje 'Registro exitoso. Revisa tu correo para activar tu cuenta'
    assert resultado["estado"] == "aceptada"
    assert resultado["mensaje"] == "Registro exitoso. Revisa tu correo para activar tu cuenta"

def test_cp_rf07_04(sistema):
    """
    id_caso: CP-RF07-04
    etiqueta: @RF07
    tipo: negativo
    regla_citada: REG-RF07-03
    """
    # Dado un usuario con correo '<CORREO_SINTETICO_2>' y contraseña '<CONTRASENA_7_CARACTERES>'
    # Cuando el usuario intenta registrarse
    resultado = sistema.ejecutar("registrar", correo="<CORREO_SINTETICO_2>", password="<CONTRASENA_7_CARACTERES>")
    # Entonces SUPUESTO: el sistema debe rechazar el registro, falta confirmar el mensaje de error exacto con el dueño del producto
    assert resultado["estado"] == "rechazada"

def test_cp_rf07_05(sistema):
    """
    id_caso: CP-RF07-05
    etiqueta: @RF07
    tipo: limite
    regla_citada: REG-RF07-09
    """
    # Dado un dispositivo que ya ha registrado 3 cuentas en las últimas 24 horas
    # Cuando el usuario intenta registrar una cuarta cuenta
    resultado = sistema.ejecutar("registrar", correo="<CORREO_SINTETICO_3>", password="<CONTRASENA_8_CARACTERES>", dispositivo_id="<DISPOSITIVO_SINTETICO_1>")
    # Entonces SUPUESTO: el sistema debe rechazar el registro, falta confirmar el mensaje de error exacto con el dueño del producto
    assert resultado["estado"] == "rechazada"