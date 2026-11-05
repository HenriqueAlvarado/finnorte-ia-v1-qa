"""Pruebas de validar_revisar (etapa 3). Los datos de qa-10 se leen del corpus: no se copian aquí."""
import copy
import re

from finnorte import pii
from finnorte.qa_revisar import QA10, TIPOS, validar_revisar

CLABE_PRUEBA = "646180" + "0" * 12

ANALIZAR = {"requisito_id": "RF12", "es_operacion_dinero": False,
            "reglas_negocio": [{"id": "REG-RF12-01", "texto": "..."}],
            "datos_prueba": [{"campo": "clabe_destino", "valor": CLABE_PRUEBA}], "ambiguedades": []}


def caso(n, tipo, **extra):
    c = {"id_caso": f"CP-RF12-{n:02d}", "titulo": f"caso {n}", "tipo": tipo, "dado": "un cliente de nivel 1",
         "cuando": "transfiere 100.00 MXN", "entonces": "el sistema devuelve el estado 'aceptada'",
         "regla_citada": "REG-RF12-01"}
    c.update(extra)
    return c


CASOS = {"casos": [caso(1, "positivo"), caso(2, "positivo"), caso(3, "negativo"), caso(4, "limite")]}


def salida(cobertura=None, faltantes=(), cumple=True, hallazgos=()):
    base = dict.fromkeys(TIPOS, 0) | {"positivo": 2, "negativo": 1, "limite": 1}
    return {"cobertura_tipos": base | (cobertura or {}), "casos_faltantes": list(faltantes),
            "cumple_qa08": cumple, "hallazgos": list(hallazgos)}


def correr(datos, analizar=ANALIZAR, casos=CASOS):
    return validar_revisar(datos, {"analizar": copy.deepcopy(analizar), "casos": copy.deepcopy(casos)})


def qa10(tipo):
    return next(v for t, v in pii.detectar(QA10.read_text(encoding="utf-8")) if t == tipo)


def h(caso_id, tipo, detalle="detalle"):
    return {"caso_id": caso_id, "tipo": tipo, "detalle": f"{tipo}: {detalle}"}


# --- casos base ------------------------------------------------------------------------------

def test_salida_coherente_sin_errores():
    assert correr(salida()) == []


def test_analizar_sin_requisito_id_siempre_es_error():
    for analizar in ({}, {"requisito_id": ""}, {"requisito_id": "RF-12"}):
        errores = correr(salida(cumple=False), analizar=analizar)
        assert len(errores) == 1 and "requisito_id" in errores[0]


def test_conteo_distinto_usa_el_mensaje_acordado():
    errores = correr(salida(cobertura={"positivo": 3}))
    assert "cobertura_tipos.positivo reportado como 3 pero el conteo real en casos es 2" in errores


# --- reglas de conteo ----------------------------------------------------------------------

def test_rf_distinto_no_cuenta():
    casos = {"casos": CASOS["casos"][:3] + [caso(4, "limite", id_caso="CP-RF07-04")]}
    ok = salida(cobertura={"limite": 0}, faltantes=[{"requisito": "RF12", "tipo_faltante": "limite"}],
                cumple=False, hallazgos=[h("CP-RF07-04", "id_mal_formado")])
    assert correr(ok, casos=casos) == []


def test_sin_id_y_id_sin_rf_cuentan():
    casos = {"casos": [caso(1, "positivo", id_caso=""), caso(2, "positivo", id_caso="CP-12-02"),
                       caso(3, "negativo"), caso(4, "limite")]}
    ok = salida(cumple=False, hallazgos=[h("SIN-ID-1", "id_mal_formado"), h("CP-12-02", "id_mal_formado")])
    assert correr(ok, casos=casos) == []


def test_tipo_invalido_no_cuenta_ni_bloquea():
    casos = {"casos": CASOS["casos"] + [caso(5, "seguridad")]}
    assert correr(salida(hallazgos=[h("CP-RF12-05", "tipo_invalido")]), casos=casos) == []


def test_supuesto_cuenta():
    casos = {"casos": CASOS["casos"][:3] + [caso(4, "limite", entonces="SUPUESTO: se rechaza la operación")]}
    assert correr(salida(), casos=casos) == []


def test_dinero_ausente_exige_los_8():
    analizar = {k: v for k, v in ANALIZAR.items() if k != "es_operacion_dinero"}
    errores = correr(salida(), analizar=analizar)
    assert sum("casos_faltantes debe incluir" in e for e in errores) == 5
    assert any(e.startswith("cumple_qa08 reportado como true pero debe ser false") for e in errores)


def test_faltante_que_sobra_es_error():
    errores = correr(salida(faltantes=[{"requisito": "RF12", "tipo_faltante": "idempotencia"}]))
    assert "casos_faltantes no debe incluir idempotencia para RF12" in errores


# --- cumple_qa08 (4.1) ---------------------------------------------------------------------

def test_sin_regla_citada_no_bloquea_y_entonces_no_verificable_si():
    assert correr(salida(hallazgos=[h("CP-RF12-01", "sin_regla_citada")])) == []
    errores = correr(salida(hallazgos=[h("CP-RF12-01", "entonces_no_verificable")]))
    assert any(e.startswith("cumple_qa08 reportado como true pero debe ser false") for e in errores)


def test_caso_id_inexistente_es_error():
    errores = correr(salida(hallazgos=[h("SIN-ID-9", "sin_regla_citada")]))
    assert any(e.startswith("hallazgos[0].caso_id no corresponde") for e in errores)


# --- id_mal_formado: unión modelo + código -------------------------------------------------

def test_id_mal_formado_no_reportado_es_error_y_bloquea_cumple():
    casos = {"casos": [caso(1, "positivo", id_caso="CP-RF12-1")] + CASOS["casos"][1:]}
    errores = correr(salida(), casos=casos)
    assert "el caso CP-RF12-1 tiene un id_caso que falta, no sigue CP-RFxx-nn o es de otro requisito, " \
           "y falta su hallazgo id_mal_formado" in errores
    assert any(e.startswith("cumple_qa08 reportado como true pero debe ser false") for e in errores)


def test_sin_id_no_reportado_es_error():
    casos = {"casos": [caso(1, "positivo", id_caso=None)] + CASOS["casos"][1:]}
    assert any(e.startswith("el caso SIN-ID-1 tiene un id_caso") for e in correr(salida(cumple=False), casos=casos))


def test_rf_de_tres_digitos_cuenta_pero_es_mal_formado():
    casos = {"casos": [caso(1, "positivo", id_caso="CP-RF123-01")] + CASOS["casos"][1:]}
    assert correr(salida(cumple=False, hallazgos=[h("CP-RF123-01", "id_mal_formado")]), casos=casos) == []


# --- datos reales: unión modelo + código y orden de 4 pasos --------------------------------

def test_dato_real_en_titulo_se_detecta():
    casos = {"casos": CASOS["casos"][:3] + [caso(4, "limite", titulo="aviso a alguien@empresa.mx")]}
    errores = correr(salida(cobertura={"limite": 0}, faltantes=[{"requisito": "RF12", "tipo_faltante": "limite"}],
                            cumple=False), casos=casos)
    assert errores == ["el caso CP-RF12-04 tiene un valor con forma de CORREO en el campo titulo "
                       "que no es dato de prueba, y falta su hallazgo datos_reales"]


def test_dato_real_reportado_por_el_modelo_no_cuenta():
    # p. ej. un nombre de persona: solo el modelo lo ve, pero el código respeta su hallazgo.
    ok = salida(cobertura={"limite": 0}, faltantes=[{"requisito": "RF12", "tipo_faltante": "limite"}],
                cumple=False, hallazgos=[h("CP-RF12-04", "datos_reales")])
    assert correr(ok) == []


def test_qa10_detectado_por_codigo_aunque_cambie_el_formato():
    telefono = qa10("TELEFONO")
    sin_espacios = re.sub(r"\D", "", telefono)
    casos = {"casos": CASOS["casos"][:3] + [caso(4, "limite", dado=f"un cliente con teléfono {sin_espacios}")]}
    errores = correr(salida(cobertura={"limite": 0}, faltantes=[{"requisito": "RF12", "tipo_faltante": "limite"}],
                            cumple=False), casos=casos)
    assert errores == ["el caso CP-RF12-04 tiene un valor con forma de TELEFONO en el campo dado "
                       "que no es dato de prueba, y falta su hallazgo datos_reales"]
    assert all(sin_espacios not in e and telefono not in e for e in errores)


def test_qa10_gana_aunque_el_dominio_sea_de_prueba_o_este_en_datos_prueba():
    correo = qa10("CORREO")
    assert correo.endswith(".example")
    analizar = ANALIZAR | {"datos_prueba": [correo]}
    casos = {"casos": CASOS["casos"][:3] + [caso(4, "limite", cuando=f"envía el aviso a {correo}")]}
    errores = correr(salida(cobertura={"limite": 0}, faltantes=[{"requisito": "RF12", "tipo_faltante": "limite"}],
                            cumple=False), analizar=analizar, casos=casos)
    assert any("forma de CORREO" in e for e in errores)
    assert all(correo not in e for e in errores)


def test_valores_de_prueba_permitidos():
    casos = {"casos": [caso(1, "positivo", dado=f"una CLABE destino {CLABE_PRUEBA[:6]} {CLABE_PRUEBA[6:]}"),
                       caso(2, "positivo", cuando="avisa a persona@ejemplo.com y a qa@sandbox.example"),
                       caso(3, "negativo"), caso(4, "limite")]}
    assert correr(salida(), casos=casos) == []


def test_clabe_que_no_es_de_prueba_se_detecta():
    otra = "0123456789" * 2
    casos = {"casos": CASOS["casos"][:3] + [caso(4, "limite", dado=f"la CLABE {otra[:18]}")]}
    errores = correr(salida(), casos=casos)
    assert any("forma de CLABE en el campo dado" in e for e in errores)
    assert all(otra[:18] not in e for e in errores)


# --- mi propia salida ----------------------------------------------------------------------

def test_mi_salida_no_puede_tener_valores_sensibles_ni_de_prueba():
    for valor, tipo in ((CLABE_PRUEBA, "CLABE"), ("persona@ejemplo.com", "CORREO"), ("81 5550 1234", "TELEFONO")):
        datos = salida(hallazgos=[h("CP-RF12-01", "sin_regla_citada", f"se encontró {valor}")])
        errores = correr(datos)
        assert any(f"tu respuesta contiene un valor con forma de {tipo}" in e for e in errores), tipo
        assert all(valor not in e for e in errores)
