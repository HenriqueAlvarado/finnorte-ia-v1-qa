import pytest

from finnorte import agente_servicio
from finnorte.herramientas import (
    Herramienta, Paso, ResultadoAgente
)
from finnorte.validador_a4 import validar_archivo_v1qa, validar_plan_v1_qa


@pytest.fixture
def archivo_valido(tmp_path, monkeypatch):
    directorio = tmp_path / "generated"
    directorio.mkdir()

    monkeypatch.setattr(
        "finnorte.validador_a4.GENERADOS",
        directorio
    )

    (directorio / "test_rf03.py").write_text(
        '''
def test_registro_exitoso():
    assert "registro" == "registro"

def test_correo_duplicado():
    assert "duplicado" == "duplicado"

def test_contrasena_corta():
    assert "menos de 8" == "menos de 8"

def test_confirmacion():
    assert "confirmacion" == "confirmacion"
''',
        encoding="utf-8"
    )
    return directorio


def preparar_agente(monkeypatch, funcion):
    herramienta = Herramienta(
        nombre="ejecutar_pytest",
        descripcion="Ejecutar pytest",
        esquema={
            "type": "object",
            "required": ["archivo"],
            "additionalProperties": False,
            "properties": {"archivo": {"type": "string"}}
        },
        funcion=funcion,
        sensible=True
    )

    def fake_ejecutor(
        tarea, herramientas, confirmar=None,
        max_pasos=5, contexto=""
    ):
        h = herramientas[0]
        args = {"archivo": "test_rf03.py"}
        confirmar(h, args)

        propuesta = {
            "accion": "usar",
            "herramienta": h.nombre,
            "argumentos": args
        }

        return ResultadoAgente(
            respuesta="Ejecución pendiente de autorización",
            fuentes=[],
            pasos=[
                Paso(1, propuesta, {"estado": "pendiente"}, "sin_confirmar")
            ],
            terminado=True
        )

    return herramienta, fake_ejecutor


def test_validador_acepta_archivo_correcto(archivo_valido):
    assert validar_archivo_v1qa("test_rf03.py") == []


def test_validador_rechaza_ruta_externa(archivo_valido):
    assert validar_archivo_v1qa("../test_rf03.py")


def test_validador_rechaza_pruebas_omitidas(archivo_valido):
    ruta = archivo_valido / "test_rf03.py"
    ruta.write_text(
        'import pytest\npytest.skip("pendiente")\n',
        encoding="utf-8"
    )
    assert validar_archivo_v1qa("test_rf03.py")


def test_agente_deja_accion_pendiente(archivo_valido, monkeypatch):
    llamadas = []
    herramienta, ejecutor = preparar_agente(
        monkeypatch,
        lambda archivo: llamadas.append(archivo)
    )

    resultado = agente_servicio.iniciar(
        "Ejecutar pruebas",
        "usuario-a",
        [herramienta],
        ejecutor=ejecutor,
        validador=validar_plan_v1_qa
    )

    assert resultado["validador"]["ok"]
    assert len(resultado["pendientes"]) == 1
    assert llamadas == []


def test_rechazar_no_ejecuta(archivo_valido, monkeypatch):
    llamadas = []
    herramienta, ejecutor = preparar_agente(
        monkeypatch,
        lambda archivo: llamadas.append(archivo)
    )

    resultado = agente_servicio.iniciar(
        "Ejecutar pruebas",
        "usuario-b",
        [herramienta],
        ejecutor=ejecutor,
        validador=validar_plan_v1_qa
    )

    identificador = resultado["pendientes"][0]["id"]

    salida = agente_servicio.resolver(
        identificador, "usuario-b", False, [herramienta]
    )

    assert salida["estado"] == "rechazada"
    assert llamadas == []


def test_aprobar_ejecuta_una_vez(archivo_valido, monkeypatch):
    llamadas = []
    herramienta, ejecutor = preparar_agente(
        monkeypatch,
        lambda archivo: llamadas.append(archivo) or {"ok": True}
    )

    resultado = agente_servicio.iniciar(
        "Ejecutar pruebas",
        "usuario-c",
        [herramienta],
        ejecutor=ejecutor,
        validador=validar_plan_v1_qa
    )

    identificador = resultado["pendientes"][0]["id"]

    salida = agente_servicio.resolver(
        identificador, "usuario-c", True, [herramienta]
    )

    assert salida["estado"] == "ejecutada"
    assert llamadas == ["test_rf03.py"]

    with pytest.raises(KeyError):
        agente_servicio.resolver(
            identificador, "usuario-c", True, [herramienta]
        )
