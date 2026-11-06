import pytest
from decimal import Decimal

@pytest.fixture
def sistema():
    pytest.skip("Conectar con el sistema bajo prueba")

def test_cp_rf15_01(sistema):
    """CP-RF15-01 @RF15 positivo REG-RF15-01"""
    # Dado un cliente nivel 1 con acumulado diario de 10,000 MXN
    # Cuando realiza una transferencia de 5,000 MXN
    resultado = sistema.ejecutar("transferir", monto=Decimal("5000.00"), nivel=1, acumulado=Decimal("10000.00"))
    # Entonces se acepta la transferencia
    assert resultado["estado"] == "aceptada"

def test_cp_rf15_02(sistema):
    """CP-RF15-02 @RF15 negativo REG-RF15-04"""
    # Dado un cliente nivel 1 con acumulado diario de 18,000 MXN
    # Cuando realiza una transferencia de 1.00 MXN
    resultado = sistema.ejecutar("transferir", monto=Decimal("1.00"), nivel=1, acumulado=Decimal("18000.00"))
    # Entonces se rechaza con el mensaje 'Alcanzaste tu límite diario'
    assert resultado["estado"] == "rechazada"
    assert resultado["mensaje"] == "Alcanzaste tu límite diario"

def test_cp_rf15_03(sistema):
    """CP-RF15-03 @RF15 limite_exacto REG-RF15-01"""
    # Dado un cliente nivel 1 con acumulado diario de 17,999 MXN
    # Cuando realiza una transferencia de 1.00 MXN
    resultado = sistema.ejecutar("transferir", monto=Decimal("1.00"), nivel=1, acumulado=Decimal("17999.00"))
    # Entonces se acepta la transferencia
    assert resultado["estado"] == "aceptada"

def test_cp_rf15_04(sistema):
    """CP-RF15-04 @RF15 un_centavo_arriba REG-RF15-04"""
    # Dado un cliente nivel 2 con acumulado diario de 120,000 MXN
    # Cuando realiza una transferencia de 0.01 MXN
    resultado = sistema.ejecutar("transferir", monto=Decimal("0.01"), nivel=2, acumulado=Decimal("120000.00"))
    # Entonces se rechaza con el mensaje 'Alcanzaste tu límite diario'
    assert resultado["estado"] == "rechazada"
    assert resultado["mensaje"] == "Alcanzaste tu límite diario"

def test_cp_rf15_05(sistema):
    """CP-RF15-05 @RF15 monto_cero REG-RF15-01"""
    # Dado un cliente nivel 1
    # Cuando realiza una transferencia de 0.00 MXN
    resultado = sistema.ejecutar("transferir", monto=Decimal("0.00"), nivel=1)
    # Entonces SUPUESTO: falta confirmar el mensaje de error específico para monto cero
    assert resultado["estado"] == "rechazada"

def test_cp_rf15_06(sistema):
    """CP-RF15-06 @RF15 monto_negativo REG-RF15-01"""
    # Dado un cliente nivel 1
    # Cuando realiza una transferencia de -100.00 MXN
    resultado = sistema.ejecutar("transferir", monto=Decimal("-100.00"), nivel=1)
    # Entonces SUPUESTO: falta confirmar el comportamiento del sistema ante montos negativos
    assert resultado["estado"] == "rechazada"

def test_cp_rf15_07(sistema):
    """CP-RF15-07 @RF15 idempotencia REG-RF15-01"""
    # Dado un cliente nivel 1 con una transferencia exitosa realizada hace 1 hora
    # Cuando reintenta la misma transferencia con la misma Idempotency-Key
    resultado = sistema.ejecutar("transferir", idempotency_key="<KEY_SINTETICA_1>", reintento=True)
    # Entonces se devuelve la respuesta de la operación original sin generar un segundo cargo
    assert resultado["estado"] == "aceptada"

def test_cp_rf15_08(sistema):
    """CP-RF15-08 @RF15 limite REG-RF15-02"""
    # Dado un cliente nivel 1 con acumulado de 18,000 MXN a las 23:59:59
    # Cuando realiza una transferencia de 1,000 MXN a las 00:00:01
    resultado = sistema.ejecutar("transferir", monto=Decimal("1000.00"), hora="00:00:01", acumulado_previo=Decimal("18000.00"))
    # Entonces se acepta la transferencia
    assert resultado["estado"] == "aceptada"

def test_cp_rf15_09(sistema):
    """CP-RF15-09 @RF15 limite REG-RF15-03"""
    # Dado un cliente nivel 1 con acumulado de 17,000 MXN
    # Cuando realiza una transferencia de 5,000 MXN que es rechazada por CLABE inválida
    resultado = sistema.ejecutar("transferir", monto=Decimal("5000.00"), clabe="<CLABE_INVALIDA_1>")
    # Entonces el acumulado diario permanece en 17,000 MXN
    assert resultado["estado"] == "rechazada"
    assert resultado["acumulado_actual"] == Decimal("17000.00")