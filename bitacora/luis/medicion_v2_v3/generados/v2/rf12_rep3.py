import pytest
from decimal import Decimal

@pytest.fixture
def sistema():
    pytest.skip("Conectar con el sistema bajo prueba")

def test_cp_rf12_01(sistema):
    """
    ID: CP-RF12-01
    Etiqueta: @RF12
    Tipo: positivo
    Regla: REG-RF12-01
    """
    # Dado una cuenta nivel 1 con saldo suficiente
    # Cuando se realiza una transferencia de 100.00 MXN a una CLABE válida con concepto 'Pago renta'
    resultado = sistema.transferir(monto=Decimal("100.00"), clabe="000000000000000000", concepto="Pago renta")
    # Entonces se acepta la transferencia
    assert resultado == "se acepta la transferencia"

def test_cp_rf12_02(sistema):
    """
    ID: CP-RF12-02
    Etiqueta: @RF12
    Tipo: negativo
    Regla: REG-RF12-01
    """
    # Dado una cuenta nivel 1
    # Cuando se intenta transferir a una CLABE de 17 dígitos
    resultado = sistema.transferir(monto=Decimal("100.00"), clabe="12345678901234567")
    # Entonces se rechaza la operación
    assert resultado == "se rechaza la operación"

def test_cp_rf12_03(sistema):
    """
    ID: CP-RF12-03
    Etiqueta: @RF12
    Tipo: limite
    Regla: REG-RF12-02
    """
    # Dado una cuenta nivel 1
    # Cuando se transfiere el monto mínimo de 1.00 MXN
    resultado = sistema.transferir(monto=Decimal("1.00"))
    # Entonces se acepta la transferencia
    assert resultado == "se acepta la transferencia"

def test_cp_rf12_04(sistema):
    """
    ID: CP-RF12-04
    Etiqueta: @RF12
    Tipo: monto_cero
    Regla: REG-RF12-02
    """
    # Dado una cuenta nivel 1
    # Cuando se intenta transferir 0.00 MXN
    resultado = sistema.transferir(monto=Decimal("0.00"))
    # Entonces se rechaza la transferencia
    assert resultado == "se rechaza la transferencia"

def test_cp_rf12_05(sistema):
    """
    ID: CP-RF12-05
    Etiqueta: @RF12
    Tipo: monto_negativo
    Regla: REG-RF12-02
    """
    # Dado una cuenta nivel 1
    # Cuando se intenta transferir -50.00 MXN
    resultado = sistema.transferir(monto=Decimal("-50.00"))
    # Entonces se rechaza la transferencia
    assert resultado == "se rechaza la transferencia"

def test_cp_rf12_06(sistema):
    """
    ID: CP-RF12-06
    Etiqueta: @RF12
    Tipo: limite_exacto
    Regla: REG-RF12-03
    """
    # Dado una cuenta nivel 2
    # Cuando se transfiere el monto máximo de 50,000.00 MXN
    resultado = sistema.transferir(monto=Decimal("50000.00"))
    # Entonces se acepta la transferencia
    assert resultado == "se acepta la transferencia"

def test_cp_rf12_07(sistema):
    """
    ID: CP-RF12-07
    Etiqueta: @RF12
    Tipo: un_centavo_arriba
    Regla: REG-RF12-03
    """
    # Dado una cuenta nivel 2
    # Cuando se intenta transferir 50,000.01 MXN
    resultado = sistema.transferir(monto=Decimal("50000.01"))
    # Entonces se rechaza con el mensaje 'El monto excede el límite por operación'
    assert resultado == "El monto excede el límite por operación"

def test_cp_rf12_08(sistema):
    """
    ID: CP-RF12-08
    Etiqueta: @RF12
    Tipo: idempotencia
    Regla: REG-RF12-07
    """
    # Dado una transferencia realizada con Idempotency-Key 'ABC-123'
    # Cuando se envía una segunda solicitud con la misma Idempotency-Key 'ABC-123' dentro de las 24 horas
    resultado = sistema.transferir(monto=Decimal("100.00"), idempotency_key="ABC-123")
    # Entonces se rechaza el segundo cargo y se devuelve el resultado de la primera operación
    assert resultado == "se rechaza el segundo cargo y se devuelve el resultado de la primera operación"