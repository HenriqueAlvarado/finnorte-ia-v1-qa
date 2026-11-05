"""Pruebas del esquema de la etapa 3 (revisar): prompts/esquemas/qa_revisar.schema.json."""
import copy
import json
from pathlib import Path

import jsonschema

RUTA = Path(__file__).resolve().parents[1] / "prompts" / "esquemas" / "qa_revisar.schema.json"
ESQUEMA = json.loads(RUTA.read_text(encoding="utf-8"))
VALIDADOR = jsonschema.Draft202012Validator(ESQUEMA)

TIPOS_CASO = ["positivo", "negativo", "limite", "monto_cero", "monto_negativo",
              "limite_exacto", "un_centavo_arriba", "idempotencia"]
TIPOS_HALLAZGO_ORIGINALES = ["datos_reales", "entonces_no_verificable", "sin_regla_citada", "id_mal_formado"]

BASE = {
    "cobertura_tipos": {"positivo": 2, "negativo": 1, "limite": 1, "monto_cero": 0, "monto_negativo": 0,
                        "limite_exacto": 0, "un_centavo_arriba": 0, "idempotencia": 0},
    "casos_faltantes": [],
    "cumple_qa08": True,
    "hallazgos": [],
}


def salida(**cambios):
    d = copy.deepcopy(BASE)
    d.update(copy.deepcopy(cambios))
    return d


def valido(d):
    return not list(VALIDADOR.iter_errors(d))


def hallazgo(caso_id="CP-RF12-01", tipo="sin_regla_citada", detalle="sin_regla_citada: regla_citada vacía"):
    return {"caso_id": caso_id, "tipo": tipo, "detalle": detalle}


# --- raíz -----------------------------------------------------------------------------------

def test_salida_minima_valida():
    assert valido(salida())


def test_salida_completa_valida():
    d = salida(
        cobertura_tipos={t: 1 for t in TIPOS_CASO} | {"idempotencia": 0},
        casos_faltantes=[{"requisito": "RF12", "tipo_faltante": "idempotencia"}],
        cumple_qa08=False,
        hallazgos=[hallazgo(), hallazgo("CP-RF12-04", "datos_reales", "patrón: CLABE de 18 dígitos en el campo dado")],
    )
    assert valido(d)


def test_falta_campo_raiz():
    for campo in BASE:
        d = salida()
        del d[campo]
        assert not valido(d), campo


def test_campo_raiz_extra():
    assert not valido(salida(abstuvo=True))


# --- cobertura_tipos ------------------------------------------------------------------------

def test_cobertura_falta_llave():
    d = salida()
    del d["cobertura_tipos"]["idempotencia"]
    assert not valido(d)


def test_cobertura_llave_extra():
    d = salida()
    d["cobertura_tipos"]["seguridad"] = 1
    assert not valido(d)


def test_cobertura_negativa():
    d = salida()
    d["cobertura_tipos"]["negativo"] = -1
    assert not valido(d)


def test_cobertura_no_entera():
    for valor in (1.5, "2", None):
        d = salida()
        d["cobertura_tipos"]["positivo"] = valor
        assert not valido(d), valor


# --- casos_faltantes ------------------------------------------------------------------------

def test_requisito_patron_invalido():
    for req in ("RF1", "rf12", "RF123", "RF-12", "CP-RF12-01", ""):
        d = salida(casos_faltantes=[{"requisito": req, "tipo_faltante": "positivo"}])
        assert not valido(d), req


def test_tipo_faltante_acepta_los_8():
    d = salida(casos_faltantes=[{"requisito": "RF12", "tipo_faltante": t} for t in TIPOS_CASO])
    assert valido(d)


def test_tipo_faltante_fuera_de_enum():
    for t in ("seguridad", "Positivo", "limite exacto", "tipo_invalido"):
        d = salida(casos_faltantes=[{"requisito": "RF12", "tipo_faltante": t}])
        assert not valido(d), t


def test_casos_faltantes_duplicados():
    f = {"requisito": "RF12", "tipo_faltante": "negativo"}
    assert not valido(salida(casos_faltantes=[f, f]))


def test_casos_faltantes_campo_extra():
    d = salida(casos_faltantes=[{"requisito": "RF12", "tipo_faltante": "negativo", "nota": "x"}])
    assert not valido(d)


# --- cumple_qa08 ----------------------------------------------------------------------------

def test_cumple_qa08_no_booleano():
    for valor in ("true", 1, None):
        assert not valido(salida(cumple_qa08=valor)), valor


# --- hallazgos ------------------------------------------------------------------------------

def test_hallazgo_caso_id_vacio():
    assert not valido(salida(hallazgos=[hallazgo(caso_id="")]))


def test_hallazgo_detalle_vacio():
    assert not valido(salida(hallazgos=[hallazgo(detalle="")]))


def test_hallazgo_acepta_los_4_tipos_originales():
    # caso_id sin patrón a propósito: se copia tal cual aunque esté mal formado, o SIN-ID-<n>.
    ids = ["CP-RF12-01", "CP-12-01", "SIN-ID-3", "caso1"]
    d = salida(hallazgos=[hallazgo(i, t, f"{t}: detalle") for i, t in zip(ids, TIPOS_HALLAZGO_ORIGINALES)])
    assert valido(d)


def test_hallazgos_duplicados():
    h = hallazgo()
    assert not valido(salida(hallazgos=[h, h]))


def test_hallazgo_tipo_invalido_aceptado():
    d = salida(hallazgos=[hallazgo("CP-RF12-05", "tipo_invalido", "tipo_invalido: el tipo «seguridad» no es uno de los 8")])
    assert valido(d)


def test_hallazgo_tipo_desconocido_rechazado():
    for t in ("tipo invalido", "TIPO_INVALIDO", "tipo_desconocido", "positivo"):
        assert not valido(salida(hallazgos=[hallazgo(tipo=t)])), t
