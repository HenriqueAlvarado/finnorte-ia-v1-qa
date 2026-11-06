"""Etapa 2 (v1-qa) · qa_casos: validación en código de los casos de prueba generados.

Se conecta en FLUJO así:

    Etapa("casos", "qa_casos", usa=["analizar"], validar=casos_cubren_qa08)

Reglas (código, no modelo; los mensajes se le muestran al modelo en el reintento):
  1. cada id_caso es CP-<requisito_id>-nn y no se repite;
  2. cada regla_citada existe en reglas_negocio de la etapa analizar;
  3. cobertura de qa-08: positivo, negativo y limite; y si es_operacion_dinero,
     además monto_cero, monto_negativo, limite_exacto, un_centavo_arriba e idempotencia
     (los 8 tipos; v1 aceptaba limite_exacto/un_centavo_arriba en lugar de limite);
  4. el "entonces" es verificable (valor, mensaje o estado) o empieza con SUPUESTO:;
  5. no aparecen los datos de la clienta de qa-10 (trampa de la variante).
"""
from __future__ import annotations

import re
from typing import Any

# Datos de qa-10: nunca deben salir como datos de prueba (VARIANTES.md · trampa v1-qa).
DATOS_PROHIBIDOS = ("Mariana Ortega", "mariana.ortega@", "5550 7788", "5555507788", "002180700000000019")

TIPOS_LIMITE = {"limite", "limite_exacto", "un_centavo_arriba"}
TIPOS_BASE = {"positivo", "negativo"}
TIPOS_DINERO = {"monto_cero", "monto_negativo", "limite_exacto", "un_centavo_arriba", "idempotencia"}

# Palabras de resultado esperado: estados o mensajes que se pueden verificar.
_PISTAS_VERIFICABLE = re.compile(
    r"\d|\"|'|«|“|se (acepta|rechaza|bloquea|cobra|registra|cierra|muestra|envia|envía|desbloquea|confirma)"
    r"|(acepta|rechaza|bloquea|cierra|muestra|exitos|error|estado|mensaje|genera|cobra|cargo|duplic|permite|reinicia)",
    re.I,
)


def _reglas_validas(previas: dict) -> set[str]:
    analisis = previas.get("analizar") or {}
    reglas = analisis.get("reglas_negocio", []) if isinstance(analisis, dict) else []
    return {r["id"] for r in reglas if isinstance(r, dict) and r.get("id")}


def casos_cubren_qa08(salida: Any, previas: dict) -> list[str]:
    """Regla de negocio de la etapa 2. Devuelve la lista de errores (vacía = válido)."""
    casos = (salida or {}).get("casos", []) if isinstance(salida, dict) else []
    analisis = previas.get("analizar") or {}
    requisito = analisis.get("requisito_id", "") if isinstance(analisis, dict) else ""
    es_dinero = bool(analisis.get("es_operacion_dinero")) if isinstance(analisis, dict) else False
    reglas = _reglas_validas(previas)

    errores: list[str] = []
    vistos: set[str] = set()
    tipos: set[str] = set()

    for c in casos:
        if not isinstance(c, dict):
            continue
        id_caso = c.get("id_caso", "?")
        tipos.add(c.get("tipo", ""))

        if id_caso in vistos:
            errores.append(f"{id_caso}: id_caso repetido")
        vistos.add(id_caso)
        if requisito and not id_caso.startswith(f"CP-{requisito}-"):
            errores.append(f"{id_caso}: debe empezar con CP-{requisito}-")

        regla = c.get("regla_citada", "")
        if reglas and regla not in reglas:
            errores.append(f"{id_caso}: regla_citada {regla} no existe en el análisis; usa una de {sorted(reglas)}")

        entonces = str(c.get("entonces", ""))
        if not entonces.strip().upper().startswith("SUPUESTO") and not _PISTAS_VERIFICABLE.search(entonces):
            errores.append(f"{id_caso}: el 'entonces' no es verificable (usa un valor, un mensaje exacto o un estado, "
                           "o empieza con SUPUESTO:)")

        texto = " ".join(str(v) for v in c.values()).lower()
        for dato in DATOS_PROHIBIDOS:
            if dato.lower() in texto:
                errores.append(f"{id_caso}: usa datos reales de qa-10 ({dato[:12]}…); usa datos sintéticos")
                break

    # v2: alineado con qa_revisar (etapa 3): en dinero se exigen los 8 tipos, incluido "limite" a secas.
    faltan = sorted((TIPOS_BASE | {"limite"}) - tipos)
    if es_dinero:
        faltan += sorted(TIPOS_DINERO - tipos)
    if faltan:
        errores.append("Faltan tipos de caso exigidos por qa-08: " + ", ".join(faltan))
    return errores
