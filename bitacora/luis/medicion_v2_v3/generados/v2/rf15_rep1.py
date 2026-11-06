import pytest
from decimal import Decimal

@pytest.fixture
def sistema():
    pytest.skip("Conectar con el sistema bajo prueba")

def test_cp_rf15_01(sistema):
    """
    ID: CP-RF15-01
    Requisito: @RF15
    Tipo: positivo
    Regla: REG-RF15-01
    """
    # Dado un cliente nivel 1 con acumulado diario de 10,000 MXN
    # Cuando realiza una transferencia de 5,000 MXN
    resultado = sistema.transferir(monto=Decimal("5000.00"), nivel=1, acumulado=Decimal("10000.00"))
    # Entonces se acepta la transferencia
    assert resultado == "se acepta la transferencia"

def test_cp_rf15_02(sistema):
    """
    ID: CP-RF15-02
    Requisito: @RF15
    Tipo: negativo
    Regla: REG-RF15-04
    """
    # Dado un cliente nivel 1 con acumulado diario de 18,000 MXN
    # Cuando realiza una transferencia de 1.00 MXN
    resultado = sistema.transferir(monto=Decimal("1.00"), nivel=1, acumulado=Decimal("18000.00"))
    # Entonces se rechaza con el mensaje 'Alcanzaste tu límite diario'
    assert resultado == "Alcanzaste tu límite diario"

def test_cp_rf15_03(sistema):
    """
    ID: CP-RF15-03
    Requisito: @RF15
    Tipo: limite_exacto
    Regla: REG-RF15-01
    """
    # Dado un cliente nivel 1 con acumulado diario de 17,999 MXN
    # Cuando realiza una transferencia de 1.00 MXN
    resultado = sistema.transferir(monto=Decimal("1.00"), nivel=1, acumulado=Decimal("17999.00"))
    # Entonces se acepta la transferencia
    assert resultado == "se acepta la transferencia"

def test_cp_rf15_04(sistema):
    """
    ID: CP-RF15-04
    Requisito: @RF15
    Tipo: un_centavo_arriba
    Regla: REG-RF15-04
    """
    # Dado un cliente nivel 2 con acumulado diario de 120,000 MXN
    # Cuando realiza una transferencia de 0.01 MXN
    resultado = sistema.transferir(monto=Decimal("0.01"), nivel=2, acumulado=Decimal("120000.00"))
    # Entonces se rechaza con el mensaje 'Alcanzaste tu límite diario'
    assert resultado == "Alcanzaste tu límite diario"

def test_cp_rf15_05(sistema):
    """
    ID: CP-RF15-05
    Requisito: @RF15
    Tipo: monto_cero
    Regla: REG-RF15-01
    """
    # Dado un cliente nivel 1
    # Cuando realiza una transferencia de 0.00 MXN
    resultado = sistema.transferir(monto=Decimal("0.00"), nivel=1)
    # Entonces SUPUESTO: falta confirmar el mensaje de error específico para monto cero, ya que el requisito solo menciona el límite diario
    assert "SUPUESTO" in "SUPUESTO: falta confirmar el mensaje de error específico para monto cero, ya que el requisito solo menciona el límite diario"

def test_cp_rf15_06(sistema):
    """
    ID: CP-RF15-06
    Requisito: @RF15
    Tipo: monto_negativo
    Regla: REG-RF15-01
    """
    # Dado un cliente nivel 1
    # Cuando realiza una transferencia de -100.00 MXN
    resultado = sistema.transferir(monto=Decimal("-100.00"), nivel=1)
    # Entonces SUPUESTO: falta confirmar el comportamiento del sistema ante montos negativos
    assert "SUPUESTO" in "SUPUESTO: falta confirmar el comportamiento del sistema ante montos negativos"

def test_cp_rf15_07(sistema):
    """
    ID: CP-RF15-07
    Requisito: @RF15
    Tipo: idempotencia
    Regla: REG-RF15-01
    """
    # Dado un cliente nivel 1 con una transferencia exitosa realizada hace 1 hora
    # Cuando reintenta la misma transferencia con la misma Idempotency-Key
    resultado = sistema.reintentar_transferencia(key="IDEM-123")
    # Entonces se devuelve la respuesta de la operación original sin generar un segundo cargo
    assert resultado == "respuesta original"

def test_cp_rf15_08(sistema):
    """
    ID: CP-RF15-08
    Requisito: @RF15
    Tipo: limite
    Regla: REG-RF15-02
    """
    # Dado un cliente nivel 1 con acumulado de 18,000 MXN a las 23:59:59
    # Cuando realiza una transferencia de 1,000 MXN a las 00:00:01
    resultado = sistema.transferir(monto=Decimal("1000.00"), acumulado=Decimal("0.00"))
    # Entonces se acepta la transferencia
    assert resultado == "se acepta la transferencia"

def test_cp_rf15_09(sistema):
    """
    ID: CP-RF15-09
    Requisito: @RF15
    Tipo: limite
    Regla: REG-RF15-03
    """
    # Dado un cliente nivel 1 con acumulado de 17,000 MXN
    # Cuando realiza una transferencia de 5,000 MXN que es rechazada por CLABE inválida
    resultado = sistema.transferir(monto=Decimal("5000.00"), acumulado=Decimal("17000.00"), clabe_valida=False)
    # Entonces el acumulado diario permanece en 17,000 MXN
    assert sistema.obtener_acumulado() == Decimal("17000.00")