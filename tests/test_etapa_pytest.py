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
    for v in (1, 2, 3):
        p = prompts.cargar("qa_pytest", v)
        assert p.variables == {"casos"} and p.salida_json
    esquema = prompts.cargar("qa_pytest").esquema
    assert validar_esquema({"nombre_archivo": "test_rf12.py", "codigo_pytest": CODIGO_OK}, esquema) == []
    assert validar_esquema({"nombre_archivo": "rf12.txt", "codigo_pytest": CODIGO_OK}, esquema)
    assert validar_esquema({"codigo_pytest": CODIGO_OK}, esquema)
    # esquema estricto: el modelo no puede inventar campos
    assert validar_esquema({"nombre_archivo": "test_rf12.py", "codigo_pytest": CODIGO_OK, "notas": "x"}, esquema)


def test_trampa_qa10_con_otro_formato():
    for dato in ('telefono="55-5550-7788"', 'telefono="5555507788"', 'clabe="0021-8070-0000-0000-19"'):
        codigo = CODIGO_OK.replace('Decimal("100.00")', f'Decimal("100.00"), {dato}')
        errores = pytest_compila_y_cubre({"codigo_pytest": codigo}, PREVIAS)
        assert any("qa-10" in e for e in errores), dato


def test_imports_fuera_de_la_biblioteca_estandar():
    codigo = "import requests\nfrom finnorte import llm\n" + CODIGO_OK
    errores = pytest_compila_y_cubre({"codigo_pytest": codigo}, PREVIAS)
    assert any("['finnorte', 'requests']" in e for e in errores)
    # pytest, decimal y otros módulos estándar sí se permiten
    assert pytest_compila_y_cubre({"codigo_pytest": "import json, datetime\n" + CODIGO_OK}, PREVIAS) == []


def test_assert_sobre_valores_locales_no_prueba_al_sistema():
    codigo = CODIGO_OK.replace('assert sistema.transferir(Decimal("100.00")) == "aceptada"',
                               'monto = Decimal("100.00")\n    assert monto == Decimal("100.00")')
    errores = pytest_compila_y_cubre({"codigo_pytest": codigo}, PREVIAS)
    assert any("test_cp_rf12_01: el assert no revisa ningún resultado de sistema" in e for e in errores)
    # pytest.raises sin llamar a sistema tampoco cuenta
    codigo = CODIGO_OK.replace('sistema.transferir(Decimal("0"))', 'Decimal("x")')
    assert any("test_cp_rf12_02: el assert no revisa" in e for e in pytest_compila_y_cubre({"codigo_pytest": codigo}, PREVIAS))


def test_resultado_guardado_en_variable_si_cuenta():
    codigo = CODIGO_OK.replace('assert sistema.transferir(Decimal("100.00")) == "aceptada"',
                               'resultado = sistema.ejecutar("transferir", monto=Decimal("100.00"))\n    assert resultado["estado"] == "aceptada"')
    assert pytest_compila_y_cubre({"codigo_pytest": codigo}, PREVIAS) == []


def test_datos_con_forma_de_pii():
    for dato, forma in (('"nuevo.cliente@ejemplo.com"', "correo"), ('"646180157000000004"', "18 dígitos"),
                        ('"55 1234 5678"', "teléfono")):
        codigo = CODIGO_OK.replace('Decimal("100.00")', f'Decimal("100.00"), dato={dato}')
        errores = pytest_compila_y_cubre({"codigo_pytest": codigo}, PREVIAS)
        assert any("forma de PII" in e and forma in e for e in errores), dato
    codigo = CODIGO_OK.replace('Decimal("100.00")', 'Decimal("100.00"), correo="<CORREO_SINTETICO_1>"')
    assert pytest_compila_y_cubre({"codigo_pytest": codigo}, PREVIAS) == []


def test_nombre_archivo_corresponde_al_requisito():
    errores = pytest_compila_y_cubre({"nombre_archivo": "test_rf07.py", "codigo_pytest": CODIGO_OK}, PREVIAS)
    assert any("debe ser test_rf12.py" in e for e in errores)


# --- Casos borde de la validación (Luis · etapa 4) ---

def _salida(codigo: str, archivo: str = "test_rf12.py") -> dict:
    return {"nombre_archivo": archivo, "codigo_pytest": codigo}


def test_codigo_vacio_no_tiene_tests():
    errores = pytest_compila_y_cubre(_salida(""), PREVIAS)
    assert "codigo_pytest no tiene ninguna función test_" in errores
    assert any("falta la función test_cp_rf12_01" in e for e in errores)


def test_raises_sin_llamar_al_sistema_no_cuenta():
    codigo = CODIGO_OK.replace('        sistema.transferir(Decimal("0"))', '        Decimal("x")')
    errores = pytest_compila_y_cubre(_salida(codigo), PREVIAS)
    assert any(e.startswith("test_cp_rf12_02: el assert no revisa") for e in errores)


def test_tests_dentro_de_una_clase_tambien_se_revisan():
    codigo = '''import pytest
from decimal import Decimal


class TestRF12:
    def test_cp_rf12_01(self, sistema):
        """REG-RF12-01"""
        assert sistema.transferir(Decimal("100.00")) == "aceptada"

    def test_cp_rf12_02(self, sistema):
        """REG-RF12-02"""
        with pytest.raises(ValueError):
            sistema.transferir(Decimal("0"))
'''
    assert pytest_compila_y_cubre(_salida(codigo), PREVIAS) == []


def test_error_de_sintaxis_dice_la_linea():
    errores = pytest_compila_y_cubre(_salida("def test_cp_rf12_01(:\n    pass\n"), PREVIAS)
    assert len(errores) == 1 and errores[0].startswith("codigo_pytest no compila: línea 1")


def test_funcion_repetida_se_detecta():
    repetida = '''

def test_cp_rf12_01(sistema):
    """REG-RF12-01"""
    assert sistema.transferir(Decimal("1.00")) == "aceptada"
'''
    errores = pytest_compila_y_cubre(_salida(CODIGO_OK + repetida), PREVIAS)
    assert errores == ["codigo_pytest define dos veces test_cp_rf12_01: pytest solo correría la última"]


def test_supuesto_se_conserva_en_el_test():
    previas = {"casos": {"casos": [dict(c) for c in PREVIAS["casos"]["casos"]]}}
    previas["casos"]["casos"][0]["entonces"] = "SUPUESTO: se rechaza con el mensaje de límite"
    errores = pytest_compila_y_cubre(_salida(CODIGO_OK), previas)
    assert errores == ["test_cp_rf12_01: el «entonces» de CP-RF12-01 es un SUPUESTO; consérvalo en el docstring o en un comentario"]
    con_supuesto = CODIGO_OK.replace('"""CP-RF12-01 @RF12 positivo · REG-RF12-01"""', '"""CP-RF12-01 @RF12 positivo · REG-RF12-01 · SUPUESTO"""')
    assert pytest_compila_y_cubre(_salida(con_supuesto), previas) == []
