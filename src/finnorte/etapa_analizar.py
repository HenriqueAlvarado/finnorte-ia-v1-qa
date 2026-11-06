"""Etapa 1 de QA: validaciones de negocio para analizar requisitos."""

from __future__ import annotations

import re
from typing import Any

from . import pii
from .etapa_casos import DATOS_PROHIBIDOS


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


    # Seguridad: la etapa analizar tampoco debe aceptar datos personales
    # como datos de prueba. No reproducir valores en mensajes de error.
    datos_prueba = datos.get("datos_prueba", [])

    if isinstance(datos_prueba, list):
        for indice, elemento in enumerate(datos_prueba, start=1):
            contenido = str(elemento)

            # Detector general: CLABE, correo, telefono, etc.
            tiene_pii = pii.contiene_pii(contenido)

            # Proteccion especifica del corpus qa-10, incluida la
            # comparacion de identificadores numericos con separadores.
            contenido_normalizado = contenido.casefold()
            digitos = re.sub(r"\D", "", contenido)

            contiene_qa10 = any(
                prohibido.casefold() in contenido_normalizado
                or (
                    len(re.sub(r"\D", "", prohibido)) >= 10
                    and re.sub(r"\D", "", prohibido) in digitos
                )
                for prohibido in DATOS_PROHIBIDOS
            )

            if tiene_pii or contiene_qa10:
                errores.append(
                    f"datos_prueba[{indice}]: contiene datos personales "
                    "o datos reales de qa-10; utiliza datos sinteticos "
                    "o marcadores simbolicos"
                )

    return errores
