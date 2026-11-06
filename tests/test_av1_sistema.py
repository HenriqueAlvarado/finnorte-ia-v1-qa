"""Pruebas de variante.sistema() (Avance 1) sin red: el buscador y el flujo se reemplazan por dobles."""
import pytest

from finnorte import controles, variante
from finnorte.pipeline import ResultadoEtapa, ResultadoFlujo
from finnorte.retrieval import Fragmento, Resultado

ENTRADA = {"requisito": "RF12 · Transferencia SPEI\nRF12.4 Una solicitud repetida no deberá generar un doble cargo."}

SALIDAS = {
    "analizar": {"requisito_id": "RF12", "es_operacion_dinero": True, "reglas_negocio": [], "datos_prueba": [],
                 "ambiguedades": []},
    "casos": {"casos": [
        {"id_caso": "CP-RF12-01", "titulo": "Límite exacto", "tipo": "limite_exacto", "dado": "una cuenta nivel 2",
         "cuando": "transfiere 50,000.00 MXN", "entonces": "se acepta la transferencia", "regla_citada": "REG-RF12-01",
         "fuente": "qa-02"},
        {"id_caso": "CP-RF12-02", "titulo": "Repetición", "tipo": "idempotencia", "dado": "una transferencia aceptada",
         "cuando": "se repite con la misma Idempotency-Key", "entonces": "no se genera un segundo cargo",
         "regla_citada": "REG-RF12-02", "fuente": "qa-02"},
    ]},
    "revisar": {"cobertura_tipos": {}, "casos_faltantes": [{"requisito": "RF12", "tipo_faltante": "positivo"}],
                "cumple_qa08": False, "hallazgos": []},
    "pytest": {"nombre_archivo": "test_rf12.py", "codigo_pytest": "def test_a():\n    pass\ndef test_b():\n    pass\n"},
}


def _res(id_, puntaje=0.8):
    return Resultado(Fragmento(id_, id_.split("#")[0], "t", "texto", {}), puntaje)


class _Indice:
    def __init__(self, resultados):
        self.resultados, self.consultas = resultados, []

    def buscar(self, consulta, k=4, umbral=0.0):
        self.consultas.append(consulta)
        return self.resultados[:k]


@pytest.fixture
def entorno(monkeypatch):
    """Devuelve un dict para ajustar lo recuperado y lo que contesta el flujo; registra qué flujo se llamó."""
    estado = {"recuperados": [_res("qa-02#0"), _res("qa-08#0")], "salidas": SALIDAS, "ok": True, "llamadas": []}
    monkeypatch.setattr(variante, "indice", lambda: _Indice(estado["recuperados"]))

    def ejecutar_falso(nombre):
        def ejecutar(entrada, detener_en_error=True):
            estado["llamadas"].append((nombre, entrada))
            etapas = [ResultadoEtapa(n, f"qa_{n}", estado["ok"] or n != "casos", s, [], 1, 1.0, 0.001)
                      for n, s in estado["salidas"].items()]
            return ResultadoFlujo(entrada, estado["salidas"], etapas)
        return ejecutar

    monkeypatch.setattr(variante.FLUJO, "ejecutar", ejecutar_falso("v2"))
    monkeypatch.setattr(variante.FLUJO_V1, "ejecutar", ejecutar_falso("v1"))
    return estado


def test_se_abstiene_sin_contexto_suficiente_y_no_llama_al_flujo(entorno):
    entorno["recuperados"] = [_res("qa-02#0", 0.1)]
    out = variante.sistema(ENTRADA)
    assert out["abstuvo"] and out["respuesta"] == controles.RESPUESTA_ABSTENCION
    assert entorno["llamadas"] == []


def test_respuesta_en_gherkin_con_etiqueta_y_fuentes_del_modelo(entorno):
    out = variante.sistema(ENTRADA)
    assert not out["abstuvo"] and out["errores_citas"] == []
    assert out["fuentes"] == ["qa-02"]
    for texto in ("@RF12", "Escenario: CP-RF12-01", "Dado una cuenta nivel 2", "Cuando transfiere 50,000.00 MXN",
                  "Entonces se acepta la transferencia", "Idempotency-Key", "NO cumple", "positivo",
                  "test_rf12.py (2 tests)"):
        assert texto in out["respuesta"], texto
    assert out["artefacto"]["flujo_ok"] and out["costo_usd"] == pytest.approx(0.004)


def test_el_contexto_llega_al_flujo_con_las_marcas_doc(entorno):
    variante.sistema(ENTRADA)
    _, entrada = entorno["llamadas"][0]
    assert "[doc:qa-02#0]" in entrada["contexto"] and entrada["entrada"].startswith("RF12")


def test_cita_no_recuperada_con_controles_se_abstiene(entorno):
    entorno["recuperados"] = [_res("qa-08#0")]                 # qa-02 no se recuperó
    out = variante.sistema(ENTRADA)
    assert out["abstuvo"] and out["fuentes"] == []
    assert any("no recuperada" in e for e in out["errores_citas"])


def test_cita_no_recuperada_sin_controles_se_muestra_pero_queda_registrada(entorno):
    entorno["recuperados"] = [_res("qa-08#0")]
    out = variante.sistema(ENTRADA, config={"controles": False})
    assert not out["abstuvo"] and out["fuentes"] == ["qa-02"]
    assert any("no recuperada" in e for e in out["errores_citas"])


def test_sin_rag_no_busca_y_manda_sin_contexto(entorno, monkeypatch):
    monkeypatch.setattr(variante, "indice", lambda: pytest.fail("no debía buscar"))
    out = variante.sistema(ENTRADA, config={"usar_rag": False, "controles": False})
    assert entorno["llamadas"][0][1]["contexto"] == "(sin contexto)"
    assert any("no recuperada" in e for e in out["errores_citas"])   # sin RAG, nada citado está recuperado


def test_version_1_usa_flujo_v1(entorno):
    variante.sistema(ENTRADA, config={"version_prompt": 1})
    assert entorno["llamadas"][0][0] == "v1"
    variante.sistema(ENTRADA)
    assert entorno["llamadas"][1][0] == "v2"


def test_flujo_sin_validar_con_controles_no_muestra_lo_rechazado(entorno):
    # Caso real de la medición del Avance 1 (q20): la etapa casos detectó un dato de qa-10 y rechazó su salida;
    # con controles, eso no debe llegar ni a la respuesta ni al artefacto.
    entorno["ok"] = False
    out = variante.sistema(ENTRADA)
    assert "no pasó su validación" in out["respuesta"] and "«casos»" in out["respuesta"]
    assert "Escenario" not in out["respuesta"] and "50,000" not in out["respuesta"]
    assert "casos" not in out["artefacto"] and not out["artefacto"]["flujo_ok"]
    assert all("errores" not in e for e in out["artefacto"]["etapas"])
    assert not out["abstuvo"] and out["fuentes"] == []


def test_flujo_sin_validar_sin_controles_se_muestra_con_aviso(entorno):
    entorno["ok"] = False                                     # línea base (configs A a C): se mide lo que pasa sin controles
    out = variante.sistema(ENTRADA, config={"controles": False})
    assert "se detuvo en la etapa «casos»" in out["respuesta"] and "Escenario" in out["respuesta"]


def test_sin_fuentes_es_error_pero_no_alucinacion(entorno):
    entorno["salidas"] = {**SALIDAS, "casos": {"casos": [{k: v for k, v in c.items() if k != "fuente"}
                                                          for c in SALIDAS["casos"]["casos"]]}}
    out = variante.sistema(ENTRADA)
    assert not out["abstuvo"] and out["errores_citas"] == ["no citó ninguna fuente"]
