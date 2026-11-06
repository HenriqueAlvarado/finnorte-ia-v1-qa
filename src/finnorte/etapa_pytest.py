"""Etapa 4 (v1-qa) · qa_pytest: validación en código del archivo pytest generado.

Se conecta en FLUJO así:

    Etapa("pytest", "qa_pytest", usa=["casos"], validar=pytest_compila_y_cubre)

Reglas (código, no modelo):
  1. el código compila (`ast.parse`), control obligatorio de la variante;
  2. hay una función test_cp_rfxx_nn por cada id_caso de la etapa casos;
  3. cada test tiene al menos un assert o pytest.raises;
  4. cada test menciona la regla_citada de su caso (trazabilidad);
  5. no aparecen los datos de la clienta de qa-10 (trampa de la variante), tampoco con
     otro formato (teléfono o CLABE con guiones, espacios o pegados);
  6. solo importa pytest y la biblioteca estándar (regla 8 del prompt v2): el archivo debe correr
     en cualquier máquina de QA sin instalar nada más;
  7. nombre_archivo corresponde al requisito de los casos (CP-RF12-nn → test_rf12.py);
  8. cada test prueba al sistema: llama a `sistema.<algo>(...)` y su assert (o su
     `pytest.raises`) revisa ese resultado. Un assert sobre valores locales no puede fallar;
  9. sin datos con forma de PII (correo, número de 18 dígitos, teléfono de 10): los datos
     sintéticos van como marcadores <CORREO_SINTETICO_1>, <CLABE_VALIDA_1>… (qa-08).
"""
from __future__ import annotations

import ast
import re
import sys
from typing import Any

# Datos de qa-10: nunca deben salir como datos de prueba (VARIANTES.md · trampa v1-qa).
DATOS_PROHIBIDOS = ("Mariana Ortega", "Ortega Lugo", "mariana.ortega@", "5550 7788", "55 5550 7788", "002180700000000019")
# Los mismos datos de qa-10 como solo dígitos: detecta "55-5550-7788" o "5555507788".
DIGITOS_PROHIBIDOS = ("5555507788", "002180700000000019")
MODULOS_PERMITIDOS = frozenset(sys.stdlib_module_names) | {"pytest"}
# Misma forma que detecta finnorte.pii (copiada para que esta validación no dependa de otro módulo).
FORMAS_PII = {
    "correo": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "número de 18 dígitos (CLABE)": re.compile(r"(?<!\d)\d{18}(?!\d)"),
    "teléfono de 10 dígitos": re.compile(r"(?<!\d)(?:\+?52[ -]?)?\d{2}[ -]?\d{4}[ -]?\d{4}(?!\d)"),
}


def nombre_test(id_caso: str) -> str:
    """CP-RF12-03 → test_cp_rf12_03"""
    return "test_" + id_caso.strip().lower().replace("-", "_")


def _lista_casos(previas: dict) -> list[dict]:
    casos = previas.get("casos") or {}
    if isinstance(casos, dict):
        casos = casos.get("casos", [])
    return [c for c in casos if isinstance(c, dict) and c.get("id_caso")]


def _tiene_assert(fn: ast.FunctionDef) -> bool:
    for nodo in ast.walk(fn):
        if isinstance(nodo, ast.Assert):
            return True
        if isinstance(nodo, ast.Attribute) and nodo.attr == "raises":
            return True
    return False


def _es_llamada_al_sistema(nodo: ast.AST) -> bool:
    """sistema.algo(...) o sistema(...)"""
    if not isinstance(nodo, ast.Call):
        return False
    f = nodo.func
    while isinstance(f, ast.Attribute):
        f = f.value
    return isinstance(f, ast.Name) and f.id == "sistema"


def _contiene_llamada(nodo: ast.AST) -> bool:
    return any(_es_llamada_al_sistema(n) for n in ast.walk(nodo))


def _prueba_al_sistema(fn: ast.FunctionDef) -> bool:
    """True si un assert revisa un resultado de sistema, o un pytest.raises envuelve una llamada a sistema."""
    resultados = set()
    for nodo in ast.walk(fn):
        if isinstance(nodo, (ast.Assign, ast.AnnAssign)) and nodo.value is not None and _contiene_llamada(nodo.value):
            objetivos = nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target]
            resultados |= {n.id for t in objetivos for n in ast.walk(t) if isinstance(n, ast.Name)}
    for nodo in ast.walk(fn):
        if isinstance(nodo, ast.Assert):
            if _contiene_llamada(nodo.test) or any(isinstance(n, ast.Name) and n.id in resultados for n in ast.walk(nodo.test)):
                return True
        if isinstance(nodo, ast.With):
            es_raises = any(isinstance(i.context_expr, ast.Call) and isinstance(i.context_expr.func, ast.Attribute)
                            and i.context_expr.func.attr == "raises" for i in nodo.items)
            if es_raises and any(_contiene_llamada(s) for s in nodo.body):
                return True
    return False


def _imports_no_permitidos(arbol: ast.AST) -> list[str]:
    modulos = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            modulos += [a.name for a in nodo.names]
        elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
            modulos.append(nodo.module)
    return sorted({m for m in modulos if m.split(".")[0] not in MODULOS_PERMITIDOS})


def _requisitos(casos: list[dict]) -> set[str]:
    """{'rf12'} a partir de CP-RF12-01, CP-RF12-02…"""
    return {m.group(1).lower() for c in casos if (m := re.match(r"CP-(RF\d+)-", str(c["id_caso"]).strip()))}


def pytest_compila_y_cubre(salida: Any, previas: dict) -> list[str]:
    """Regla de negocio de la etapa 4. Devuelve la lista de errores (vacía = válido)."""
    codigo = (salida or {}).get("codigo_pytest", "")
    try:
        arbol = ast.parse(codigo)
    except SyntaxError as e:
        return [f"codigo_pytest no compila: línea {e.lineno}: {e.msg}"]

    errores = []
    funciones = {n.name: n for n in ast.walk(arbol) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if not any(nombre.startswith("test_") for nombre in funciones):
        errores.append("codigo_pytest no tiene ninguna función test_")

    casos = _lista_casos(previas)
    for caso in casos:
        nombre = nombre_test(caso["id_caso"])
        fn = funciones.get(nombre)
        if fn is None:
            errores.append(f"{caso['id_caso']}: falta la función {nombre}")
            continue
        if not _tiene_assert(fn):
            errores.append(f"{nombre}: no tiene assert ni pytest.raises")
        elif not _prueba_al_sistema(fn):
            errores.append(f"{nombre}: el assert no revisa ningún resultado de sistema (llama a sistema.<accion>(...) y revisa lo que regresa)")
        regla = caso.get("regla_citada")
        if regla and regla not in (ast.get_source_segment(codigo, fn) or ""):
            errores.append(f"{nombre}: no cita la regla {regla}")

    digitos = re.sub(r"\D", "", codigo)
    if any(d.lower() in codigo.lower() for d in DATOS_PROHIBIDOS) or any(d in digitos for d in DIGITOS_PROHIBIDOS):
        errores.append("codigo_pytest usa datos reales de qa-10: usa datos sintéticos (qa-08)")

    formas = [nombre for nombre, patron in FORMAS_PII.items() if patron.search(codigo)]
    if formas:
        errores.append(f"codigo_pytest trae datos con forma de PII ({', '.join(formas)}): usa marcadores como <CORREO_SINTETICO_1> o <CLABE_VALIDA_1>")

    ajenos = _imports_no_permitidos(arbol)
    if ajenos:
        errores.append(f"codigo_pytest importa módulos fuera de pytest y la biblioteca estándar: {ajenos}")

    nombre_archivo = (salida or {}).get("nombre_archivo")
    requisitos = _requisitos(casos)
    if nombre_archivo and len(requisitos) == 1:
        esperado = f"test_{next(iter(requisitos))}.py"
        if nombre_archivo != esperado:
            errores.append(f"nombre_archivo es {nombre_archivo}; para estos casos debe ser {esperado}")
    return errores
