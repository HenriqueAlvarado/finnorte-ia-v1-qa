"""A4 · paso 4: pruebas del validador de lógica tradicional (src/finnorte/validador_v1qa.py)."""
from finnorte.validador_v1qa import validar_variante_v1qa

CASOS_COMPLETOS = [
    {"titulo": "Registro exitoso", "dado": "datos válidos", "cuando": "se registra",
     "entonces": "el registro es exitoso y se crea la cuenta"},
    {"titulo": "Correo duplicado", "dado": "un correo ya registrado", "cuando": "se intenta registrar de nuevo",
     "entonces": "se rechaza por correo duplicado"},
    {"titulo": "Contraseña corta", "dado": "una contraseña de 5 caracteres", "cuando": "se registra",
     "entonces": "se rechaza: la contraseña debe tener al menos 8 caracteres"},
    {"titulo": "Confirmación", "dado": "un registro exitoso", "cuando": "se completa",
     "entonces": "se envía un mensaje de confirmación al correo"},
]
PYTEST_OK = "def test_a():\n    assert sistema(1) == 1\n"
PYTEST_ROTO = "def test_a(:\n    pass\n"


def _salida(casos=CASOS_COMPLETOS, pytest_codigo=PYTEST_OK, errores_citas=None):
    return {
        "errores_citas": errores_citas or [],
        "artefacto": {"casos": {"casos": casos}, "pytest": {"codigo_pytest": pytest_codigo, "nombre_archivo": "test_rf01.py"}},
    }


def test_cubre_los_4_escenarios_y_pytest_compila_ok():
    r = validar_variante_v1qa(_salida())
    assert r["cubre_los_4_escenarios"] and r["pytest_compila"] and r["ok"]
    assert all(r["escenarios_registro"].values())


def test_falta_un_escenario_se_detecta_y_ok_es_falso():
    sin_confirmacion = CASOS_COMPLETOS[:3]
    r = validar_variante_v1qa(_salida(casos=sin_confirmacion))
    assert not r["escenarios_registro"]["mensaje_confirmacion"]
    assert not r["cubre_los_4_escenarios"] and not r["ok"]


def test_pytest_que_no_compila_se_detecta():
    r = validar_variante_v1qa(_salida(pytest_codigo=PYTEST_ROTO))
    assert not r["pytest_compila"] and "no compila" in r["pytest_detalle"] and not r["ok"]


def test_informacion_externa_detectada_por_errores_citas():
    r = validar_variante_v1qa(_salida(errores_citas=["la fuente qa-99 no recuperada"]))
    assert not r["sin_informacion_externa"] and not r["ok"]


def test_requisito_distinto_al_de_registro_no_marca_ok_pero_no_truena():
    otro = [{"titulo": "Límite", "dado": "x", "cuando": "y", "entonces": "z"}]
    r = validar_variante_v1qa(_salida(casos=otro))
    assert not r["ok"] and not any(r["escenarios_registro"].values())
