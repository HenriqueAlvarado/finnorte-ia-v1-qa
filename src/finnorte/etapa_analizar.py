"""Etapa 1 de QA: validaciones de negocio para analizar requisitos."""

from __future__ import annotations

import re
from typing import Any


def validar_analizar(datos: Any, salidas: dict) -> list[str]:
    """Valida las reglas de negocio producidas por qa_analizar.

    Devuelve una lista vacia cuando la salida es correcta.
    """
    errores: list[str] = []

    if not isinstance(datos, dict):
        return ["El analisis debe ser un objeto JSON"]

    requisito = datos.get("requisito_id", "")
    reglas = datos.get("reglas_negocio", [])

    if not re.fullmatch(r"RF[0-9]{2,}", requisito):
        errores.append("requisito_id debe tener formato RFxx")
        return errores

    if not isinstance(reglas, list):
        return ["reglas_negocio debe ser una lista"]

    vistos: set[str] = set()

    for numero, regla in enumerate(reglas, start=1):
        if not isinstance(regla, dict):
            errores.append(f"Regla {numero}: debe ser un objeto")
            continue

        identificador = regla.get("id", "")
        esperado = f"REG-{requisito}-{numero:02d}"

        if identificador != esperado:
            errores.append(
                f"Regla {numero}: identificador {identificador!r}; "
                f"se esperaba {esperado}"
            )

        if identificador in vistos:
            errores.append(f"Identificador repetido: {identificador}")

        vistos.add(identificador)

        if not str(regla.get("texto", "")).strip():
            errores.append(f"{identificador}: falta el texto de la regla")

    return errores
