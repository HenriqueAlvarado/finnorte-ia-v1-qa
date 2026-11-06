from finnorte.etapa_analizar import validar_analizar
from finnorte.etapa_casos import DATOS_PROHIBIDOS


def analizar_con(dato):
    return {
        "requisito_id": "RF12",
        "es_operacion_dinero": True,
        "reglas_negocio": [
            {
                "id": "REG-RF12-01",
                "texto": "Validar la cuenta destino."
            }
        ],
        "datos_prueba": [dato],
        "ambiguedades": []
    }


def test_acepta_marcador_sintetico():
    errores = validar_analizar(
        analizar_con("CLABE_VALIDA_1"),
        {}
    )
    assert errores == []


def test_rechaza_clabe_con_formato_sensible():
    dato = "123456789012345678"
    errores = validar_analizar(analizar_con(dato), {})

    assert errores
    assert dato not in " ".join(errores)


def test_rechaza_correo_sintetico_con_formato_personal():
    dato = "persona.prueba@example.com"
    errores = validar_analizar(analizar_con(dato), {})

    assert errores
    assert dato not in " ".join(errores)


def test_rechaza_datos_especificos_de_qa10():
    dato = DATOS_PROHIBIDOS[0]
    errores = validar_analizar(analizar_con(dato), {})

    assert errores
    assert dato not in " ".join(errores)


def test_rechaza_clabe_qa10_con_separadores():
    dato = next(
        valor for valor in DATOS_PROHIBIDOS
        if len(valor) == 18 and valor.isdigit()
    )
    separado = " ".join(dato[i:i + 3] for i in range(0, 18, 3))

    errores = validar_analizar(analizar_con(separado), {})

    assert errores
    assert separado not in " ".join(errores)


def test_conserva_validacion_de_identificadores():
    datos = analizar_con("CLABE_VALIDA_1")
    datos["reglas_negocio"][0]["id"] = "REG-RF99-01"

    errores = validar_analizar(datos, {})

    assert any("REG-RF12-01" in error for error in errores)
