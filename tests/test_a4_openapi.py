"""A4 · v3-soporte: herramienta consultar_openapi y validador del ejemplo (otras variantes: verán SKIP si no lo implementan)."""
from conftest import pendiente

from finnorte import openapi

OK = ('curl -X POST https://api.sandbox.finnorte.mx/v1/transferencias -H "Authorization: Bearer $FINNORTE_TOKEN" '
      '-H "Idempotency-Key: $(uuidgen)" -d \'{"cuenta_origen": "cta_123", "clabe_destino": "646180000000000001", '
      '"monto_centavos": 150000, "concepto": "Pago", "referencia_numerica": "1234567"}\'')


def test_especificacion_es_valida_y_no_usa_api11():
    spec = openapi.cargar_spec()
    assert spec["openapi"].startswith("3.1")
    assert "fn_live" not in str(spec) and "abarrotesnorte" not in str(spec)   # nada de api-11
    assert openapi.buscar_operacion("get", "/v2/cuentas/cta_1/saldo")


@pendiente("A4")
def test_consultar_openapi():
    assert openapi.consultar_openapi("/v2/cuentas/cta_1/saldo", "GET")["existe"]
    r = openapi.consultar_openapi("/v1/saldos", "GET")
    assert not r["existe"] and r["reemplazo"].startswith("GET /v2")
    assert openapi.consultar_openapi("/v1/cuentas/c1", "GET")["deprecado"]


@pendiente("A4")
def test_verificar_ejemplo():
    assert openapi.verificar_ejemplo(OK) == []
    assert any("amount" in e for e in openapi.verificar_ejemplo(OK.replace('"monto_centavos"', '"amount"')))
    assert openapi.verificar_ejemplo(OK.replace("api.sandbox.finnorte.mx", "api.finnorte.mx"))
    assert openapi.verificar_ejemplo('requests.get("https://api.sandbox.finnorte.mx/v2/cuentas/c1", headers={"Authorization": "Bearer eyJabc.def"})')
