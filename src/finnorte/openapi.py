"""Especificación OpenAPI de la API pública de FinNorte (variante v3-soporte · T7, T10, A4).

El archivo vive en datos/v3-soporte/openapi.json: OpenAPI 3.1, derivado SOLO de la documentación
pública del corpus (api-01 a api-10; nunca de api-11, que es confidencial).

Para qué sirve en el proyecto:
- A4 · herramienta del agente: `consultar_openapi(ruta, metodo)` (solo lectura) y su objeto `HERRAMIENTA`.
- Validador de lógica tradicional: `verificar_ejemplo(codigo)` revisa que un ejemplo curl/Python generado
  por el modelo use rutas, métodos y campos que existen, sin credenciales literales ni producción.
- Control de vigencia: `avisos_deprecacion(texto)` agrega el reemplazo de rutas deprecadas o retiradas.

Ya resuelto (úsalo): cargar_spec, buscar_operacion, campos_cuerpo, extraer_llamadas, campos_enviados,
avisos_deprecacion.  A4 (v3-soporte): implementa consultar_openapi y verificar_ejemplo.
Otras variantes pueden usarlo como ejemplo de herramienta de solo lectura con esquema estricto.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from .config import RAIZ
from .herramientas import Herramienta

SPEC_RUTA = RAIZ / "datos" / "v3-soporte" / "openapi.json"
METODOS = ("get", "post", "put", "patch", "delete")
SECRETOS = [re.compile(p) for p in (r"fn_live_\w+", r"fn_test_\w+", r"Bearer\s+eyJ[\w.\-]+",
                                     r"client_secret\s*=\s*[\"'][^\"'$]{6,}[\"']", r"client_secret=[A-Za-z0-9]{8,}")]
SDK = {  # método del SDK de Python (api-09) → operación HTTP
    r"\.transferencias\.crear\(": ("post", "/v1/transferencias"),
    r"\.transferencias\.obtener\(": ("get", "/v1/transferencias/{id}"),
    r"\.cuentas\.saldo\(": ("get", "/v2/cuentas/{cuenta_id}/saldo"),
    r"\.cuentas\.obtener\(": ("get", "/v2/cuentas/{cuenta_id}"),
    r"\.cuentas\.movimientos\(": ("get", "/v2/cuentas/{cuenta_id}/movimientos"),
}


@lru_cache(maxsize=1)
def cargar_spec(ruta: str | None = None) -> dict:
    return json.loads(Path(ruta or SPEC_RUTA).read_text(encoding="utf-8"))


def _regex(plantilla: str) -> re.Pattern:
    return re.compile("^" + re.sub(r"\{[^}]+\}", r"[^/]+", plantilla.rstrip("/")) + "/?$")


def buscar_operacion(metodo: str, ruta: str) -> tuple[str, dict] | None:
    """Encuentra la operación documentada que corresponde a una ruta concreta (con o sin parámetros)."""
    spec = cargar_spec()
    ruta = ruta.split("?")[0].rstrip("/") or "/"
    for plantilla, ops in spec["paths"].items():
        if (ruta == plantilla or _regex(plantilla).match(ruta)) and metodo.lower() in ops:
            return plantilla, ops[metodo.lower()]
    return None


def _retirado(metodo: str, ruta: str) -> dict | None:
    for r in cargar_spec().get("x-finnorte-retirados", []):
        m, p = r["ruta"].split(" ", 1)
        if m.lower() == metodo.lower() and (_regex(p).match(ruta.split("?")[0]) or p == ruta):
            return r
    return None


def _resolver(esquema: dict) -> dict:
    if "$ref" in esquema:
        nombre = esquema["$ref"].split("/")[-1]
        return cargar_spec()["components"]["schemas"][nombre]
    return esquema


def campos_cuerpo(op: dict) -> set[str]:
    contenido = op.get("requestBody", {}).get("content", {})
    for tipo in ("application/json", "application/x-www-form-urlencoded"):
        if tipo in contenido:
            return set(_resolver(contenido[tipo]["schema"]).get("properties", {}))
    return set()


def consultar_openapi(ruta: str, metodo: str = "GET") -> dict:
    """HERRAMIENTA (A4, solo lectura): qué dice la especificación sobre una ruta y un método.

    Devuelve {"existe": True, "ruta", "metodo", "resumen", "deprecado", "retiro", "reemplazo", "scopes",
    "parametros", "campos_cuerpo", "respuestas", "fuente"} o, si no existe,
    {"existe": False, "retirado", "reemplazo", "fuente"} (rutas retiradas) / {"existe": False, "sugerencias": [...]}.
    """
    # TODO(A4): implementa esta parte (ver docstring y pruebas)
    raise NotImplementedError("Pendiente: A4")


HERRAMIENTA = Herramienta(
    nombre="consultar_openapi",
    descripcion="Consulta la especificación OpenAPI pública de FinNorte: si una ruta y método existen, "
                "si están deprecados, qué scope piden y qué campos acepta el cuerpo. Solo lectura.",
    esquema={"type": "object", "required": ["ruta", "metodo"],
             "properties": {"ruta": {"type": "string", "pattern": "^/", "maxLength": 120},
                            "metodo": {"enum": ["GET", "POST", "PUT", "PATCH", "DELETE"]}},
             "additionalProperties": False},
    funcion=consultar_openapi,
    sensible=False,
)


# ─────────────────────────── validación del ejemplo ───────────────────────────
def extraer_llamadas(codigo: str) -> list[tuple[str, str]]:
    """(método, ruta) de cada llamada: curl, requests/httpx y SDK."""
    llamadas = []
    for linea in re.split(r"\n(?!\s*-)", codigo):           # une continuaciones de curl
        if "curl" in linea:
            m = re.search(r"https?://[^/\s'\"]+(/[^\s'\"\\]*)", linea)
            if m:
                met = re.search(r"-X\s*([A-Z]+)", linea)
                datos = re.search(r"\s(-d|--data|--data-raw|-F)\s", linea)
                llamadas.append(((met.group(1) if met else ("POST" if datos else "GET")).lower(), m.group(1)))
    for m in re.finditer(r"(?:requests|httpx|session|s)\.(get|post|put|patch|delete)\(\s*[f]?[\"']([^\"']+)[\"']", codigo):
        ruta = re.sub(r"^https?://[^/]+", "", m.group(2))
        ruta = re.sub(r"\{[^}]*\}", "x", ruta) if "{" in ruta and m.group(2).startswith(("f", "http")) else ruta
        llamadas.append((m.group(1), ruta if ruta.startswith("/") else "/" + ruta.split("/", 3)[-1]))
    for patron, (met, ruta) in SDK.items():
        if re.search(patron, codigo):
            llamadas.append((met, ruta))
    return llamadas


def campos_enviados(codigo: str) -> set[str]:
    """Claves de cuerpos JSON en -d '{...}', json={...} o argumentos con nombre del SDK de transferencias."""
    campos: set[str] = set()
    for bloque in re.findall(r"(?:-d|--data(?:-raw)?)\s+'(\{.*?\})'", codigo, re.S) + re.findall(r"json\s*=\s*(\{.*?\})", codigo, re.S):
        campos |= set(re.findall(r"[\"'](\w+)[\"']\s*:", bloque))
    m = re.search(r"\.transferencias\.crear\((.*?)\)\s*$", codigo, re.S | re.M)
    if m:
        campos |= set(re.findall(r"(\w+)\s*=", m.group(1))) - {"idempotency_key"}
    return campos


def verificar_ejemplo(codigo: str) -> list[str]:
    """Errores del ejemplo contra la especificación. Lista vacía = se puede mostrar.

    Revisa: credenciales literales (SECRETOS), uso de producción en lugar de sandbox, que haya al menos una
    llamada reconocible, que cada (método, ruta) exista y no esté retirada o deprecada, que los campos del
    cuerpo estén documentados y que POST /v1/transferencias lleve Idempotency-Key.
    """
    # TODO(A4): implementa esta parte (ver docstring y pruebas)
    raise NotImplementedError("Pendiente: A4")


def avisos_deprecacion(texto: str) -> list[str]:
    """Si el texto menciona una ruta deprecada o retirada, devuelve el aviso con su reemplazo (código, no modelo)."""
    avisos = []
    for r in cargar_spec().get("x-finnorte-retirados", []):
        if r["ruta"].split(" ", 1)[1] in texto:
            avisos.append(f"⚠ {r['ruta']} fue retirado el {r['retirado']}. Usa {r['reemplazo']} ({r['fuente']}).")
    for plantilla, ops in cargar_spec()["paths"].items():
        for m, op in ops.items():
            base = plantilla.split("{")[0].rstrip("/")
            if m in METODOS and op.get("deprecated") and base and re.search(re.escape(base) + r"(/|\b)", texto):
                avisos.append(f"⚠ {m.upper()} {plantilla} se retira el {op.get('x-retiro')}. Usa {op.get('x-reemplazo')} (api-08).")
    return list(dict.fromkeys(avisos))
