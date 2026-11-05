"""Pruebas de la etapa 2 (qa_casos): la regla de negocio en código y el esquema, sin llamar al modelo."""
import copy
import json
from pathlib import Path

from finnorte.etapa_casos import casos_cubren_qa08
from finnorte.pipeline import validar_esquema

ESQUEMA = json.loads((Path(__file__).resolve().parents[1] / "prompts" / "esquemas" / "qa_casos.schema.json").read_text(encoding="utf-8"))

ANALISIS = {
    "requisito_id": "RF12",
    "es_operacion_dinero": True,
    "reglas_negocio": [{"id": "REG-RF12-01", "texto": "Monto máximo por operación nivel 2: 50,000 MXN"},
                       {"id": "REG-RF12-02", "texto": "Solicitud repetida con la misma llave no genera segundo cargo"}],
    "datos_prueba": ["50,000.00", "50,000.01"],
    "ambiguedades": [],
}


def _caso(n, tipo, entonces="se acepta la transferencia", regla="REG-RF12-01"):
    return {"id_caso": f"CP-RF12-{n:02d}", "titulo": f"Caso {tipo}", "tipo": tipo, "dado": "una cuenta nivel 2",
            "cuando": "transfiere 50,000.00 MXN", "entonces": entonces, "regla_citada": regla}


COMPLETO = {"casos": [_caso(1, "positivo"), _caso(2, "negativo", "se rechaza con el mensaje «El monto excede el límite por operación»"),
                      _caso(3, "monto_cero", "se rechaza"), _caso(4, "monto_negativo", "se rechaza"),
                      _caso(5, "limite_exacto", "se acepta con 50,000.00"), _caso(6, "un_centavo_arriba", "se rechaza con 50,000.01"),
                      _caso(7, "idempotencia", "no se genera un segundo cargo", "REG-RF12-02"),
                      _caso(8, "limite", "se acepta con 8,000.00 en nivel 1")]}


def test_salida_completa_es_valida():
    assert validar_esquema(COMPLETO, ESQUEMA) == []
    assert casos_cubren_qa08(COMPLETO, {"analizar": ANALISIS}) == []


def test_esquema_rechaza_tipo_inventado_y_campos_extra():
    malo = copy.deepcopy(COMPLETO)
    malo["casos"][0]["tipo"] = "borde"
    malo["casos"][1]["extra"] = 1
    assert len(validar_esquema(malo, ESQUEMA)) >= 2


def test_dispara_cuando_faltan_tipos_de_dinero():
    parcial = {"casos": COMPLETO["casos"][:3]}
    errores = casos_cubren_qa08(parcial, {"analizar": ANALISIS})
    assert any("idempotencia" in e and "un_centavo_arriba" in e for e in errores)


def test_dinero_sin_tipo_limite_falla_aunque_haya_limite_exacto():
    """Fallo real medido en v1: con limite_exacto y un_centavo_arriba pero sin "limite", la etapa 3 marca casos_faltantes."""
    sin_limite = {"casos": [c for c in COMPLETO["casos"] if c["tipo"] != "limite"] + [_caso(8, "limite_exacto", "se acepta con 8,000.00")]}
    assert not any(c["tipo"] == "limite" for c in sin_limite["casos"])
    errores = casos_cubren_qa08(sin_limite, {"analizar": ANALISIS})
    assert any("limite" in e and "Faltan tipos" in e for e in errores)


def test_no_exige_tipos_de_dinero_si_no_es_dinero():
    analisis = {**ANALISIS, "requisito_id": "RF07", "es_operacion_dinero": False,
                "reglas_negocio": [{"id": "REG-RF07-01", "texto": "contraseña mínimo 8 caracteres"}]}
    casos = {"casos": [
        {"id_caso": "CP-RF07-01", "titulo": "Registro correcto", "tipo": "positivo", "dado": "un correo nuevo",
         "cuando": "se registra con contraseña de 8 caracteres", "entonces": "se muestra el mensaje de confirmación", "regla_citada": "REG-RF07-01"},
        {"id_caso": "CP-RF07-02", "titulo": "Contraseña corta", "tipo": "negativo", "dado": "un correo nuevo",
         "cuando": "usa contraseña de 7 caracteres", "entonces": "se rechaza", "regla_citada": "REG-RF07-01"},
        {"id_caso": "CP-RF07-03", "titulo": "Contraseña justa", "tipo": "limite", "dado": "un correo nuevo",
         "cuando": "usa contraseña de 8 caracteres", "entonces": "se acepta", "regla_citada": "REG-RF07-01"}]}
    assert casos_cubren_qa08(casos, {"analizar": analisis}) == []


def test_regla_citada_inexistente_y_id_repetido():
    malo = copy.deepcopy(COMPLETO)
    malo["casos"][0]["regla_citada"] = "REG-RF12-99"
    malo["casos"][1]["id_caso"] = malo["casos"][0]["id_caso"]
    errores = casos_cubren_qa08(malo, {"analizar": ANALISIS})
    assert any("REG-RF12-99" in e for e in errores)
    assert any("repetido" in e for e in errores)


def test_bloquea_datos_reales_de_qa10():
    malo = copy.deepcopy(COMPLETO)
    malo["casos"][0]["dado"] = "la clienta Mariana Ortega Lugo con CLABE 002180700000000019"
    assert any("qa-10" in e for e in casos_cubren_qa08(malo, {"analizar": ANALISIS}))


def test_entonces_vago_se_rechaza_y_supuesto_se_permite():
    vago = copy.deepcopy(COMPLETO)
    vago["casos"][0]["entonces"] = "todo funciona bien"
    assert any("verificable" in e for e in casos_cubren_qa08(vago, {"analizar": ANALISIS}))
    vago["casos"][0]["entonces"] = "SUPUESTO: falta confirmar el mensaje con el dueño del producto"
    assert not any("verificable" in e for e in casos_cubren_qa08(vago, {"analizar": ANALISIS}))
