"""A4 · v1-qa: mi herramienta del agente — `ejecutar_pytest(archivo)` (tabla de variantes).

Control de la tabla de variantes para v1-qa: "Sandbox, tiempo máximo de 30 s, solo el
archivo generado". Eso se traduce en tres reglas que hace cumplir el CÓDIGO, no el modelo:

  1. Sandbox: el archivo se busca y se ejecuta SOLO dentro de SANDBOX_DIR (nunca una ruta
     arbitraria del sistema; se resuelve la ruta y se verifica que siga dentro del sandbox).
  2. Tiempo máximo de 30 s: `subprocess.run(..., timeout=30)`.
  3. Solo el archivo generado: el nombre debe cumplir el mismo patrón que exige
     `etapa_pytest.nombre_test`/`pytest_compila_y_cubre` (test_rfNN.py) y debe haberlo escrito
     antes `guardar_pytest_generado` (lo llama api/producto.py cuando /v1/qa corre con éxito
     la etapa "pytest" del flujo) — así el agente no puede inventar ni pedir que se corra
     cualquier archivo .py que exista en el servidor.

Es una herramienta SENSIBLE: ejecuta código (aunque sea el pytest ya validado por
`pytest_compila_y_cubre`), así que igual que `crear_ticket_cambio` en el caso guía, pide
confirmación humana antes de correr.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from .config import RAIZ
from .herramientas import Herramienta

SANDBOX_DIR = RAIZ / "bitacora" / "pytest_sandbox"
NOMBRE_VALIDO = re.compile(r"^test_rf\d+\.py$")
TIMEOUT_S = 30


def guardar_pytest_generado(nombre_archivo: str, codigo_pytest: str) -> Path | None:
    """Escribe al sandbox el pytest que acaba de generar variante.sistema(), para que el
    agente lo pueda correr después. Si el nombre no sigue el patrón esperado, no escribe
    nada (devuelve None) en vez de fallar la respuesta de /v1/qa."""
    if not nombre_archivo or not NOMBRE_VALIDO.match(nombre_archivo):
        return None
    SANDBOX_DIR.mkdir(parents=True, exist_ok=True)
    destino = SANDBOX_DIR / nombre_archivo
    destino.write_text(codigo_pytest or "", encoding="utf-8")
    return destino


def _ruta_en_sandbox(archivo: str) -> Path | None:
    if not archivo or not NOMBRE_VALIDO.match(archivo):
        return None
    ruta = (SANDBOX_DIR / archivo).resolve()
    sandbox = SANDBOX_DIR.resolve()
    if sandbox not in ruta.parents or not ruta.is_file():
        return None
    return ruta


def ejecutar_pytest(archivo: str) -> dict:
    """Corre, en sandbox y con tope de 30 s, el pytest que ya se generó (y solo ese)."""
    ruta = _ruta_en_sandbox(archivo)
    if ruta is None:
        return {"ok": False, "error": f"'{archivo}' no es un pytest generado disponible en el sandbox"}
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", str(ruta), "-q"], cwd=SANDBOX_DIR,
                          capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"tiempo máximo de {TIMEOUT_S} s excedido"}
    salida = (r.stdout + r.stderr)[-4000:]
    return {"ok": r.returncode == 0, "codigo_salida": r.returncode, "salida": salida}


def herramientas_v1qa() -> list[Herramienta]:
    return [
        Herramienta(
            "ejecutar_pytest",
            "Corre, en un sandbox con tiempo máximo de 30 s, el archivo pytest que ya generó "
            "tu variante (nombre test_rfNN.py); no acepta rutas ni nombres fuera de ese patrón.",
            {"type": "object", "required": ["archivo"], "additionalProperties": False,
             "properties": {"archivo": {"type": "string", "pattern": r"^test_rf\d+\.py$"}}},
            ejecutar_pytest,
            sensible=True,
        ),
    ]


def validar_plan_v1qa(resultado, propuestas: list[tuple[str, dict]]) -> list[str]:
    """Validador de lógica tradicional ANTES de ofrecer confirmación (lo pasa agente_servicio
    como `validador=`): solo se ofrece ejecutar_pytest si el archivo pedido ya existe de
    verdad en el sandbox (es decir, ya lo generó /v1/qa en una corrida anterior). Bloquea que
    el modelo "invente" un nombre de archivo y lo ofrezca para confirmación."""
    hallazgos = []
    for nombre, args in propuestas:
        if nombre != "ejecutar_pytest":
            continue
        archivo = args.get("archivo")
        if _ruta_en_sandbox(archivo) is None:
            hallazgos.append(f"ejecutar_pytest({archivo!r}) no corresponde a ningún pytest ya generado en el sandbox")
    return hallazgos
