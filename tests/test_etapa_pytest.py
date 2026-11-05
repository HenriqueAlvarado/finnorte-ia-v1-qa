from finnorte import prompts
from finnorte.etapa_pytest import nombre_test, pytest_compila_y_cubre
from finnorte.pipeline import validar_esquema

PREVIAS = {"casos": {"casos": [
    {"id_caso": "CP-RF12-01", "titulo": "Transferencia válida", "tipo": "positivo",
     "dado": "...", "cuando": "...", "entonces": "...", "regla_citada": "REG-RF12-01"},
    {"id_caso": "CP-RF12-02", "titulo": "Monto cero", "tipo": "monto_cero",
     "dado": "...", "cuando": "...", "entonces": "...", "regla_citada": "REG-RF12-02"},
]}}

CODIGO_OK = '''import pytest
from decimal import Decimal


@pytest.fixture
def sistema():
    pytest.skip("Conectar con el sistema bajo prueba")


def test_cp_rf12_01(sistema):
    """CP-RF12-01 @RF12 positivo · REG-RF12-01"""
    assert sistema.transferir(Decimal("100.00")) == "aceptada"


def test_cp_rf12_02(sistema):
    """CP-RF12-02 @RF12 monto_cero · REG-RF12-02"""
    with pytest.raises(ValueError):
        sistema.transferir(Decimal("0"))
'''


def test_nombre_test():
    assert nombre_test("CP-RF12-03") == "test_cp_rf12_03"


def test_codigo_valido_pasa():
    assert pytest_compila_y_cubre({"nombre_archivo": "test_rf12.py", "codigo_pytest": CODIGO_OK}, PREVIAS) == []


def test_codigo_que_no_compila():
    errores = pytest_compila_y_cubre({"codigo_pytest": "def test_x(:\n  pass"}, PREVIAS)
    assert errores and "no compila" in errores[0]


def test_falta_un_caso():
    codigo = CODIGO_OK.split("def test_cp_rf12_02")[0]
    errores = pytest_compila_y_cubre({"codigo_pytest": codigo}, PREVIAS)
    assert any("CP-RF12-02" in e for e in errores)


def test_sin_assert_y_sin_regla():
    codigo = "def test_cp_rf12_01():\n    pass\n\ndef test_cp_rf12_02():\n    '''REG-RF12-02'''\n    assert True\n"
    errores = pytest_compila_y_cubre({"codigo_pytest": codigo}, PREVIAS)
    assert any("no tiene assert" in e for e in errores)
    assert any("no cita la regla REG-RF12-01" in e for e in errores)


def test_trampa_qa10():
    codigo = CODIGO_OK.replace('Decimal("100.00")', 'Decimal("2500"), clabe="002180700000000019"')
    errores = pytest_compila_y_cubre({"codigo_pytest": codigo}, PREVIAS)
    assert any("qa-10" in e for e in errores)


def test_esquema_y_prompts():
    for v in (1, 2):
        p = prompts.cargar("qa_pytest", v)
        assert p.variables == {"casos"} and p.salida_json
    esquema = prompts.cargar("qa_pytest").esquema
    assert validar_esquema({"nombre_archivo": "test_rf12.py", "codigo_pytest": CODIGO_OK}, esquema) == []
    assert validar_esquema({"nombre_archivo": "rf12.txt", "codigo_pytest": CODIGO_OK}, esquema)
    assert validar_esquema({"codigo_pytest": CODIGO_OK}, esquema)
