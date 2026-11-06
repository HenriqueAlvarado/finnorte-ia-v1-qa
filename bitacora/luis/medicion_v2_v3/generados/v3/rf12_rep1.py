import pytest
from decimal import Decimal

@pytest.fixture
def sistema():
    pytest.skip("Conectar con el sistema bajo prueba")

def test_cp_rf12_01(sistema):
    """
    id_caso: CP-RF12-01
    etiqueta: @RF12
    tipo: positivo
    regla_citada: REG-RF12-01
    """
    # Dado una cuenta nivel 1 con saldo suficiente
    # Cuando se realiza una transferencia de 100.00 MXN a una CLABE válida con concepto 'Pago renta'
    resultado = sistema.ejecutar("transferir", monto=Decimal("100.00"), clabe="<CLABE_VALIDA_1>", concepto="Pago renta")
    # Entonces se acepta la transferencia
    assert resultado["estado"] == "aceptada"

def test_cp_rf12_02(sistema):
    """
    id_caso: CP-RF12-02
    etiqueta: @RF12
    tipo: negativo
    regla_citada: REG-RF12-01
    """
    # Dado una cuenta nivel 1
    # Cuando se intenta transferir a una CLABE de 17 dígitos
    resultado = sistema.ejecutar("transferir", monto=Decimal("10.00"), clabe="<CLABE_17_DIGITOS>")
    # Entonces se rechaza la operación
    assert resultado["estado"] == "rechazada"

def test_cp_rf12_03(sistema):
    """
    id_caso: CP-RF12-03
    etiqueta: @RF12
    tipo: limite
    regla_citada: REG-RF12-02
    """
    # Dado una cuenta nivel 1
    # Cuando se transfiere el monto mínimo de 1.00 MXN
    resultado = sistema.ejecutar("transferir", monto=Decimal("1.00"), clabe="<CLABE_VALIDA_1>")
    # Entonces se acepta la transferencia
    assert resultado["estado"] == "aceptada"

def test_cp_rf12_04(sistema):
    """
    id_caso: CP-RF12-04
    etiqueta: @RF12
    tipo: monto_cero
    regla_citada: REG-RF12-02
    """
    # Dado una cuenta nivel 1
    # Cuando se intenta transferir 0.00 MXN
    resultado = sistema.ejecutar("transferir", monto=Decimal("0.00"), clabe="<CLABE_VALIDA_1>")
    # Entonces se rechaza la transferencia
    assert resultado["estado"] == "rechazada"

def test_cp_rf12_05(sistema):
    """
    id_caso: CP-RF12-05
    etiqueta: @RF12
    tipo: monto_negativo
    regla_citada: REG-RF12-02
    """
    # Dado una cuenta nivel 1
    # Cuando se intenta transferir -50.00 MXN
    resultado = sistema.ejecutar("transferir", monto=Decimal("-50.00"), clabe="<CLABE_VALIDA_1>")
    # Entonces se rechaza la transferencia
    assert resultado["estado"] == "rechazada"

def test_cp_rf12_06(sistema):
    """
    id_caso: CP-RF12-06
    etiqueta: @RF12
    tipo: limite_exacto
    regla_citada: REG-RF12-03
    """
    # Dado una cuenta nivel 2
    # Cuando se transfiere el monto máximo de 50,000.00 MXN
    resultado = sistema.ejecutar("transferir", monto=Decimal("50000.00"), clabe="<CLABE_VALIDA_1>")
    # Entonces se acepta la transferencia
    assert resultado["estado"] == "aceptada"

def test_cp_rf12_07(sistema):
    """
    id_caso: CP-RF12-07
    etiqueta: @RF12
    tipo: un_centavo_arriba
    regla_citada: REG-RF12-03
    """
    # Dado una cuenta nivel 2
    # Cuando se intenta transferir 50,000.01 MXN
    resultado = sistema.ejecutar("transferir", monto=Decimal("50000.01"), clabe="<CLABE_VALIDA_1>")
    # Entonces se rechaza con el mensaje 'El monto excede el límite por operación'
    assert resultado["estado"] == "rechazada"
    assert resultado["mensaje"] == "El monto excede el límite por operación"

def test_cp_rf12_08(sistema):
    """
    id_caso: CP-RF12-08
    etiqueta: @RF12
    tipo: idempotencia
    regla_citada: REG-RF12-07
    """
    # Dado una transferencia realizada con Idempotency-Key 'ABC-123'
    sistema.ejecutar("transferir", monto=Decimal("100.00"), clabe="<CLABE_VALIDA_1>", idempotency_key="ABC-123")
    # Cuando se envía una segunda solicitud con la misma Idempotency-Key 'ABC-123' dentro de las 24 horas
    resultado = sistema.ejecutar("transferir", monto=Decimal("100.00"), clabe="<CLABE_VALIDA_1>", idempotency_key="ABC-123")
    # Entonces se rechaza el segundo cargo y se devuelve el resultado de la primera operación
    assert resultado["estado"] == "rechazada"