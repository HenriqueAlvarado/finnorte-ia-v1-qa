"""A4 · Pruebas de v1-qa: herramienta ejecutar_pytest (sandbox), validador, ejecutor propio y flujo con confirmación.
Todas corren sin red: el motor de la variante se sustituye por una salida fija (monkeypatch)."""
import json

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from finnorte import herramientas, llm, qa_agente  # noqa: E402
from finnorte.herramientas import Herramienta, ejecutar_agente  # noqa: E402

CRED = {"email": "qa@finnorte.mx", "contrasena": "segura123"}
REQ_RF07 = "RF07.3 El sistema deberá rechazar contraseñas de menos de 8 caracteres"

CODIGO_OK = '''import pytest

@pytest.fixture
def sistema():
    pytest.skip("Conectar con el sistema bajo prueba")

def test_cp_rf07_01(sistema):
    assert sistema.registrar("<CORREO_SINTETICO_1>", "clave1234").mensaje == "Registro exitoso"

def test_cp_rf07_02(sistema):
    assert sistema.registrar("<CORREO_SINTETICO_1>", "clave1234").error == "duplicado"
'''


def _caso(id_, tipo, titulo, dado, cuando, entonces):
    return {"id_caso": id_, "titulo": titulo, "tipo": tipo, "dado": dado, "cuando": cuando, "entonces": entonces,
            "regla_citada": "REG-RF07-01", "fuente": "qa-08"}


CASOS_RF07 = [
    _caso("CP-RF07-01", "positivo", "Registro exitoso", "un correo nuevo", "se registra con contraseña válida", "se muestra el mensaje de confirmación"),
    _caso("CP-RF07-02", "negativo", "Correo duplicado", "un correo ya registrado", "intenta registrarse otra vez", "se rechaza el registro"),
    _caso("CP-RF07-03", "limite", "Contraseña de 7 caracteres", "un correo nuevo", "usa una contraseña de menos de 8 caracteres", "se rechaza"),
]


def salida_motor(casos=None, codigo=CODIGO_OK, flujo_ok=True):
    return {"respuesta": "ok", "fuentes": ["qa-08"], "abstuvo": False, "errores_citas": [], "costo_usd": 0, "latencia_ms": 1,
            "artefacto": {"flujo_ok": flujo_ok, "casos": {"casos": CASOS_RF07 if casos is None else casos},
                          "pytest": {"nombre_archivo": "test_rf07.py", "codigo_pytest": codigo}}}


@pytest.fixture
def generados(monkeypatch, tmp_path):
    monkeypatch.setattr(qa_agente, "GENERADOS", tmp_path / "generados")
    (tmp_path / "generados").mkdir()
    return tmp_path / "generados"


# ───────────── herramienta ejecutar_pytest: control y sandbox ─────────────
def test_ejecuta_solo_el_archivo_generado(generados):
    (generados / "test_rf07.py").write_text(CODIGO_OK, encoding="utf-8")
    r = qa_agente.ejecutar_pytest("test_rf07.py")
    assert r["ok"] and r["omitidas"] == 2 and r["falladas"] == 0


@pytest.mark.parametrize("nombre", ["../secreto.py", "..\\x.py", "carpeta/test_a.py", "TEST_A.py", "test_a.txt", "", "test_a.py; ls"])
def test_rechaza_nombres_fuera_de_la_carpeta(generados, nombre):
    r = qa_agente.ejecutar_pytest(nombre)
    assert r["ok"] is False and "error" in r


def test_archivo_inexistente_es_un_error_claro_no_una_excepcion(generados):
    r = qa_agente.ejecutar_pytest("test_no_existe.py")
    assert r["ok"] is False and "No existe" in r["error"]


def test_tiempo_maximo(generados, monkeypatch):
    (generados / "test_lento.py").write_text("import time\ndef test_x():\n    time.sleep(10)\n", encoding="utf-8")
    monkeypatch.setattr(qa_agente, "TIEMPO_MAX_S", 1)
    r = qa_agente.ejecutar_pytest("test_lento.py")
    assert r["ok"] is False and "Tiempo excedido" in r["error"]


def test_el_codigo_generado_no_ve_los_secretos(generados, monkeypatch):
    monkeypatch.setenv("TOKEN_SECRET", "no-debe-verse")
    monkeypatch.setenv("GEMINI_API_KEY", "no-debe-verse")
    (generados / "test_env.py").write_text(
        "import os\ndef test_sin_secretos():\n    assert 'TOKEN_SECRET' not in os.environ and 'GEMINI_API_KEY' not in os.environ\n", encoding="utf-8")
    r = qa_agente.ejecutar_pytest("test_env.py")
    assert r["ok"] and r["aprobadas"] == 1


def test_esquema_de_ejecutar_pytest_es_estricto_y_sensible():
    h = {x.nombre: x for x in qa_agente.herramientas_qa()}["ejecutar_pytest"]
    assert h.sensible and h.esquema["additionalProperties"] is False
    assert herramientas._errores_de_esquema(h, {"archivo": "../x.py"})
    assert herramientas._errores_de_esquema(h, {"archivo": "test_ok.py", "extra": 1})
    assert not herramientas._errores_de_esquema(h, {"archivo": "test_ok.py"})


# ───────────── validador de v1-qa ─────────────
def test_validador_acepta_la_salida_completa_de_registro():
    assert qa_agente.validar_salida_qa(salida_motor(), REQ_RF07) == []


REQ_RF07_COMPLETO = ("RF07.1 El sistema deberá permitir registrarse con correo y contraseña. RF07.2 El sistema deberá validar que el correo sea único. "
                     "RF07.3 El sistema deberá rechazar contraseñas de menos de 8 caracteres. RF07.4 El sistema deberá mostrar un mensaje de confirmación.")


@pytest.mark.parametrize("quitar,mensaje", [("duplicado", "correo duplicado"), ("7 caracteres", "contraseña de menos de 8")])
def test_validador_detecta_un_escenario_de_registro_faltante(quitar, mensaje):
    casos = [c for c in CASOS_RF07 if quitar not in c["titulo"].lower()]
    assert any(mensaje in h for h in qa_agente.validar_salida_qa(salida_motor(casos), REQ_RF07_COMPLETO))


def test_un_subrequisito_exige_solo_su_escenario():
    """RF07.3 (contraseña corta) no debe exigir el escenario de correo duplicado."""
    casos = [c for c in CASOS_RF07 if "duplicado" not in c["titulo"].lower()]
    assert qa_agente.validar_salida_qa(salida_motor(casos), REQ_RF07) == []


def test_validador_detecta_pytest_que_no_compila():
    h = qa_agente.validar_salida_qa(salida_motor(codigo="def test_x(:\n    pass"), REQ_RF07)
    assert any("no compila" in x for x in h)


def test_validador_detecta_datos_de_qa10_y_pii_que_no_vienen_de_la_entrada():
    assert any("qa-10" in x for x in qa_agente.validar_salida_qa(salida_motor(codigo=CODIGO_OK + "# Mariana Ortega\n"), REQ_RF07))
    assert any("correo" in x for x in qa_agente.validar_salida_qa(salida_motor(codigo=CODIGO_OK + "# ana@banco.com\n"), REQ_RF07))


def test_validador_no_opina_si_el_motor_se_abstuvo():
    assert qa_agente.validar_salida_qa({"abstuvo": True, "artefacto": {}}, REQ_RF07) == []


# ───────────── ejecutor propio ─────────────
def _guion(*respuestas):
    it = iter(respuestas)
    return lambda p, s: json.dumps(next(it))


BORRAR = Herramienta("borrar_rama", "Borra una rama", {"type": "object", "required": ["rama"], "additionalProperties": False,
                     "properties": {"rama": {"type": "string"}}}, lambda rama: "borrada", sensible=True)


def test_confirmar_none_deja_pendiente_y_no_ejecuta():
    ejecutadas = []
    h = Herramienta("borrar_rama", "x", BORRAR.esquema, lambda rama: ejecutadas.append(rama), sensible=True)
    llm.fake.responder = _guion({"accion": "usar", "herramienta": "borrar_rama", "argumentos": {"rama": "main"}},
                                {"accion": "responder", "respuesta": "pendiente", "fuentes": []})
    r = ejecutar_agente("Borra main", [h], confirmar=lambda h, a: None)
    assert ejecutadas == [] and r.pasos[0].estado == "pendiente"


def test_sensible_sin_funcion_de_confirmacion_nunca_se_ejecuta():
    ejecutadas = []
    h = Herramienta("borrar_rama", "x", BORRAR.esquema, lambda rama: ejecutadas.append(rama), sensible=True)
    llm.fake.responder = _guion({"accion": "usar", "herramienta": "borrar_rama", "argumentos": {"rama": "main"}},
                                {"accion": "responder", "respuesta": "no", "fuentes": []})
    r = ejecutar_agente("Borra main", [h])
    assert ejecutadas == [] and r.pasos[0].estado == "rechazada"


def test_confirmacion_que_falla_cuenta_como_rechazo():
    ejecutadas = []
    h = Herramienta("borrar_rama", "x", BORRAR.esquema, lambda rama: ejecutadas.append(rama), sensible=True)

    def rota(h, a):
        raise RuntimeError("falló la confirmación")
    llm.fake.responder = _guion({"accion": "usar", "herramienta": "borrar_rama", "argumentos": {"rama": "main"}},
                                {"accion": "responder", "respuesta": "no", "fuentes": []})
    r = ejecutar_agente("Borra main", [h], confirmar=rota)
    assert ejecutadas == [] and r.pasos[0].estado == "rechazada"


def test_argumentos_con_campos_extra_son_invalidos_y_no_se_ejecutan():
    ejecutadas = []
    h = Herramienta("borrar_rama", "x", BORRAR.esquema, lambda rama: ejecutadas.append(rama), sensible=True)
    llm.fake.responder = _guion({"accion": "usar", "herramienta": "borrar_rama", "argumentos": {"rama": "x", "forzar": True}},
                                {"accion": "responder", "respuesta": "ok", "fuentes": []})
    r = ejecutar_agente("x", [h], confirmar=lambda h, a: True)
    assert ejecutadas == [] and r.pasos[0].estado == "invalida"


def test_repeticion_exacta_se_detecta():
    cuenta = []
    h = Herramienta("contar", "x", {"type": "object", "properties": {}}, lambda: cuenta.append(1) or len(cuenta))
    uso = {"accion": "usar", "herramienta": "contar", "argumentos": {}}
    llm.fake.responder = _guion(uso, uso, {"accion": "responder", "respuesta": "listo", "fuentes": []})
    r = ejecutar_agente("x", [h])
    assert cuenta == [1] and [p.estado for p in r.pasos] == ["ejecutada", "repetida", "respuesta"]


def test_falla_de_herramienta_vuelve_como_observacion_y_no_tumba_el_agente():
    def rota():
        raise FileNotFoundError("no existe test_x.py")
    h = Herramienta("rota", "x", {"type": "object", "properties": {}}, rota)
    llm.fake.responder = _guion({"accion": "usar", "herramienta": "rota", "argumentos": {}},
                                {"accion": "responder", "respuesta": "la herramienta falló", "fuentes": []})
    r = ejecutar_agente("x", [h])
    assert r.pasos[0].resultado.startswith("ERROR: FileNotFoundError") and r.respuesta == "la herramienta falló"


# ───────────── flujo completo por la API: generar → pendiente → rechazar / autorizar ─────────────
@pytest.fixture
def cliente(monkeypatch, tmp_path, generados):
    monkeypatch.setenv("TOKEN_SECRET", "x" * 40)
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setattr(llm.fake, "responder", None)
    monkeypatch.setattr(qa_agente.variante, "sistema", lambda entrada, config=None: salida_motor())
    import api.producto as m
    m.auth = m.Autenticador(str(tmp_path / "u.db"))
    m._ventanas.clear()
    return TestClient(m.app)


def _h(c):
    c.post("/auth/registro", json=CRED)
    return {"Authorization": "Bearer " + c.post("/auth/login", json=CRED).json()["token"]}


def test_qa_muestra_el_validador_en_cada_respuesta(cliente):
    r = cliente.post("/v1/qa", json={"requisito": REQ_RF07}, headers=_h(cliente))
    v = r.json()["validador"]
    assert r.status_code == 200 and v["ok"] and v["hallazgos"] == [] and v["reintento"] is False and v["enmascarados"] == 0


# ───────────── las 2 mejoras de la A4: enmascarado y reintento guiado ─────────────
def test_mejora_2_enmascara_correo_clabe_y_telefono_que_no_vienen_de_la_entrada():
    texto = "Con ana@banco.com, CLABE 002180700000000019 y tel 55 1234 5678; el requisito pide x@y.mx"
    nuevo, n = qa_agente.enmascarar_texto(texto, "El requisito pide x@y.mx")
    assert n == 3 and "ana@banco.com" not in nuevo and "x@y.mx" in nuevo and "<CORREO_SINTETICO>" in nuevo


def test_mejora_2_el_enmascarado_se_informa_y_deja_pasar_al_validador(monkeypatch):
    sucio = salida_motor(codigo=CODIGO_OK + "# ana@banco.com\n")
    monkeypatch.setattr(qa_agente.variante, "sistema", lambda entrada, config=None: sucio)
    salida, validador = qa_agente.generar_validado(REQ_RF07)
    assert validador["enmascarados"] >= 1 and validador["ok"]
    assert "ana@banco.com" not in salida["artefacto"]["pytest"]["codigo_pytest"]


def test_mejora_1_reintento_guiado_conserva_el_intento_con_menos_hallazgos(monkeypatch):
    sin_exitoso = [c for c in CASOS_RF07 if "exitoso" not in c["titulo"].lower() and "confirmaci" not in c["entonces"].lower()]
    entradas = []

    def motor(entrada, config=None):
        entradas.append(entrada["requisito"])
        return salida_motor(sin_exitoso if len(entradas) == 1 else CASOS_RF07)
    monkeypatch.setattr(qa_agente.variante, "sistema", motor)
    salida, validador = qa_agente.generar_validado(REQ_RF07_COMPLETO)
    assert len(entradas) == 2 and "CORRECCIÓN" in entradas[1] and "Falta" not in entradas[1]
    assert validador["reintento"] is True and validador["ok"]


def test_validador_no_dice_ok_si_el_flujo_se_detuvo_sin_casos():
    detenido = salida_motor(casos=[], flujo_ok=False)
    assert any("se detuvo" in h for h in qa_agente.validar_salida_qa(detenido, REQ_RF07))


def test_mejora_1_si_el_flujo_se_detiene_se_reintenta_una_vez(monkeypatch):
    llamadas = []

    def motor(entrada, config=None):
        llamadas.append(1)
        return salida_motor(casos=[], flujo_ok=False) if len(llamadas) == 1 else salida_motor()
    monkeypatch.setattr(qa_agente.variante, "sistema", motor)
    _, validador = qa_agente.generar_validado(REQ_RF07)
    assert len(llamadas) == 2 and validador["reintento"] is True and validador["ok"]


def test_si_el_flujo_se_detiene_dos_veces_el_validador_lo_dice(monkeypatch):
    monkeypatch.setattr(qa_agente.variante, "sistema", lambda e, config=None: salida_motor(casos=[], flujo_ok=False))
    _, validador = qa_agente.generar_validado(REQ_RF07)
    assert validador["ok"] is False and validador["reintento"] is False


def test_mejora_1_sin_hallazgos_no_hay_reintento(monkeypatch):
    llamadas = []
    monkeypatch.setattr(qa_agente.variante, "sistema", lambda e, config=None: llamadas.append(1) or salida_motor())
    _, validador = qa_agente.generar_validado(REQ_RF07)
    assert len(llamadas) == 1 and validador["reintento"] is False


def test_la_nota_de_correccion_no_repite_el_dato_inventado():
    nota = qa_agente._nota_de_correccion(["Dato con forma de correo que no viene de la entrada: ana@banco.com"])
    assert "ana@banco.com" not in nota and "marcadores" in nota


def test_agente_genera_y_deja_pendiente_la_ejecucion(cliente, generados):
    out = cliente.post("/v1/agente", json={"tarea": f"Genera las pruebas de {REQ_RF07} y ejecútalas"}, headers=_h(cliente)).json()
    assert out["validador"]["ok"] and len(out["pendientes"]) == 1
    p = out["pendientes"][0]
    assert p["herramienta"] == "ejecutar_pytest" and p["argumentos"] == {"archivo": "test_rf07.py"}
    assert (generados / "test_rf07.py").is_file()


def test_confirmacion_rechazada_no_ejecuta_nada(cliente, generados, monkeypatch):
    llamadas = []
    monkeypatch.setattr(qa_agente, "ejecutar_pytest", lambda archivo: llamadas.append(archivo) or {})
    h = _h(cliente)
    p = cliente.post("/v1/agente", json={"tarea": f"Genera las pruebas de {REQ_RF07}"}, headers=h).json()["pendientes"][0]
    r = cliente.post(f"/v1/agente/confirmar/{p['id']}", json={"aprobar": False}, headers=h).json()
    assert r["estado"] == "rechazada" and llamadas == []


def test_confirmacion_aprobada_ejecuta_exactamente_el_archivo_visto(cliente):
    h = _h(cliente)
    p = cliente.post("/v1/agente", json={"tarea": f"Genera las pruebas de {REQ_RF07}"}, headers=h).json()["pendientes"][0]
    r = cliente.post(f"/v1/agente/confirmar/{p['id']}", json={"aprobar": True}, headers=h).json()
    assert r["estado"] == "ejecutada" and r["resultado"]["ok"] and r["resultado"]["archivo"] == "test_rf07.py"
    assert cliente.post(f"/v1/agente/confirmar/{p['id']}", json={"aprobar": True}, headers=h).status_code == 404


def test_validador_bloquea_ejecutar_un_archivo_que_no_se_genero(cliente):
    llm.fake.responder = _guion({"accion": "usar", "herramienta": "ejecutar_pytest", "argumentos": {"archivo": "test_inventado.py"}},
                                {"accion": "responder", "respuesta": "pendiente", "fuentes": []})
    out = cliente.post("/v1/agente", json={"tarea": "Ejecuta test_inventado.py ahora"}, headers=_h(cliente)).json()
    assert not out["validador"]["ok"] and out["pendientes"] == []
    assert "no se generó en esta ejecución" in out["validador"]["hallazgos"][0]


def test_validador_bloquea_ofrecer_la_ejecucion_si_la_generacion_tiene_hallazgos(cliente, monkeypatch):
    sin_contrasena_corta = [c for c in CASOS_RF07 if "7 caracteres" not in c["titulo"].lower()]
    monkeypatch.setattr(qa_agente.variante, "sistema", lambda entrada, config=None: salida_motor(sin_contrasena_corta))
    out = cliente.post("/v1/agente", json={"tarea": f"Genera las pruebas de {REQ_RF07}"}, headers=_h(cliente)).json()
    assert not out["validador"]["ok"] and out["pendientes"] == []
