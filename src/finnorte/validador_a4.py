"""Validador tradicional del plan de ejecución de pruebas v1-qa."""
import ast
import re
from pathlib import Path

from .config import RAIZ


GENERADOS = RAIZ / "sandbox" / "generated"


def validar_archivo_v1qa(archivo: str) -> list[str]:
    """Verifica archivo autorizado, sintaxis y presencia de pruebas ejecutables."""
    errores = []

    if not isinstance(archivo, str) or not re.fullmatch(
        r"test_[A-Za-z0-9_]+\.py", archivo
    ):
        return ["Nombre de archivo no permitido"]

    ruta = GENERADOS / archivo

    if ruta.is_symlink() or not ruta.is_file():
        return ["El archivo de pruebas no existe en el directorio autorizado"]

    if ruta.stat().st_size > 256 * 1024:
        return ["Archivo demasiado grande"]

    codigo = ruta.read_text(encoding="utf-8")

    try:
        arbol = ast.parse(codigo)
    except SyntaxError:
        return ["El archivo pytest no compila"]

    tests = [
        n for n in ast.walk(arbol)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name.startswith("test_")
    ]

    if not tests:
        errores.append("No hay funciones test_")

    if "pytest.skip" in codigo or "pytest.skip(" in codigo:
        errores.append("El archivo conserva pruebas omitidas deliberadamente")

    obligatorios = {
        "registro exitoso": ("registro", "registrar"),
        "correo duplicado": ("duplicado", "ya registrado"),
        "contraseña corta": ("menos de 8", "min_length", "longitud"),
        "confirmación": ("confirmacion", "confirmación", "activar"),
    }

    normalizado = codigo.casefold()

    for criterio, alternativas in obligatorios.items():
        if not any(x.casefold() in normalizado for x in alternativas):
            errores.append(f"No se identificó evidencia del criterio: {criterio}")

    return errores


def validar_plan_v1_qa(resultado, propuestas: list[tuple[str, dict]]) -> list[str]:
    """Valida el plan del agente antes de crear una autorización humana."""
    errores = []

    if len(propuestas) > 1:
        errores.append("Solo se permite una ejecución de pytest por solicitud")

    for nombre, argumentos in propuestas:
        if nombre != "ejecutar_pytest":
            errores.append(f"Herramienta no autorizada: {nombre}")
            continue

        if set(argumentos) != {"archivo"}:
            errores.append("Argumentos inválidos para ejecutar_pytest")
            continue

        errores.extend(validar_archivo_v1qa(argumentos["archivo"]))

        pasos = [
            p for p in resultado.pasos
            if p.propuesta.get("herramienta") == nombre
            and p.estado == "sin_confirmar"
        ]

        if not pasos:
            errores.append("La ejecución no quedó pendiente de confirmación humana")

    return errores
