"""Pruebas de los prompts de la etapa 3 (qa_revisar v1 y v2): cargan, renderizan y su ejemplo cumple el esquema."""
import json

import jsonschema
import pytest

from finnorte import prompts
from finnorte.variante import FLUJO, FLUJO_V1

LLAVES = ["positivo", "negativo", "limite", "monto_cero", "monto_negativo", "limite_exacto", "un_centavo_arriba",
          "idempotencia"]


def _ejemplo(p):
    _, usuario = p.render(analizar="{}", casos="{}")
    return json.loads(usuario.strip().splitlines()[-1])


@pytest.mark.parametrize("version", [1, 2])
def test_carga_renderiza_y_el_ejemplo_cumple_el_esquema(version):
    p = prompts.cargar("qa_revisar", version)
    assert p.variables == {"analizar", "casos"} and p.salida_json
    assert not list(jsonschema.Draft202012Validator(p.esquema).iter_errors(_ejemplo(p)))


def test_v2_pide_los_campos_en_orden_de_dependencia():
    # hallazgos → cobertura_tipos → casos_faltantes → cumple_qa08 (v1 decidía cumple_qa08 antes de los hallazgos)
    assert list(_ejemplo(prompts.cargar("qa_revisar", 2))) == ["hallazgos", "cobertura_tipos", "casos_faltantes",
                                                                "cumple_qa08"]
    assert list(_ejemplo(prompts.cargar("qa_revisar", 1)))[-1] == "hallazgos"   # la v1 no cambia


def test_v2_cuenta_por_el_campo_tipo_y_lista_las_8_llaves_exactas():
    p = prompts.cargar("qa_revisar", 2)
    texto = p.sistema
    assert "TAL COMO VIENE" in texto and "No reclasifiques" in texto
    lista = texto.split("exactamente estas 8 llaves", 1)[1].split("\n", 1)[0]
    assert [ll for ll in LLAVES if ll in lista] == LLAVES


def test_v2_documenta_sus_cambios():
    assert prompts.cargar("qa_revisar", 2).meta["cambios"].startswith("v2 corrige fallos medidos en v1")


def test_flujo_usa_la_v2_y_flujo_v1_la_v1():
    revisar = {f.nombre: next(e for e in f.etapas if e.nombre == "revisar") for f in (FLUJO, FLUJO_V1)}
    assert prompts.cargar("qa_revisar", revisar[FLUJO.nombre].version).version == 2
    assert revisar[FLUJO_V1.nombre].version == 1
