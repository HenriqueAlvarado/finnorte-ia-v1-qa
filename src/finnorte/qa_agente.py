"""A4 · Herramientas, validador e integración del agente de la variante v1-qa (requisito → casos → pytest).

Herramientas del agente
  generar_pruebas(requisito)  Llama a variante.sistema() y guarda el archivo pytest generado en bitacora/generados/.
                              No es sensible: solo escribe un archivo con nombre validado dentro de esa carpeta.
  ejecutar_pytest(archivo)    SENSIBLE: ejecuta código. Control (tabla de la A4): solo el archivo generado, en un
                              subproceso aislado, con tiempo máximo de 30 s y sin los secretos del entorno.
                              Nunca corre sin que una persona vea el nombre exacto del archivo y lo autorice.

Validador (lógica tradicional, corre en cada respuesta): validar_salida_qa / validar_plan_qa.
"""
from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from . import variante
from .config import RAIZ
from .etapa_pytest import DATOS_PROHIBIDOS, DIGITOS_PROHIBIDOS, FORMAS_PII
from .herramientas import Herramienta

GENERADOS = RAIZ / "bitacora" / "generados"
TIEMPO_MAX_S = 30
NOMBRE_VALIDO = re.compile(r"^test_[a-z0-9_]+\.py$")      # solo el nombre: sin carpetas, sin «..», sin rutas
TIPOS_LIMITE = {"limite", "limite_exacto", "un_centavo_arriba"}


# ───────────────────────────── ejecutar_pytest (sensible) ─────────────────────────────
def _ruta_generada(archivo: str) -> Path:
    """Convierte el nombre en una ruta SOLO si es un archivo generado dentro de GENERADOS; si no, ValueError."""
    if not isinstance(archivo, str) or not NOMBRE_VALIDO.match(archivo):
        raise ValueError("Nombre de archivo no permitido: debe ser test_<nombre>.py, sin carpetas")
    ruta = GENERADOS / archivo
    if not ruta.is_file():
        raise ValueError(f"No existe el archivo generado {archivo}")
    if ruta.resolve().parent != GENERADOS.resolve():       # por si fuera un enlace a otra carpeta
        raise ValueError("El archivo está fuera de la carpeta de archivos generados")
    return ruta


def _entorno_minimo() -> dict[str, str]:
    """El código generado NO hereda la llave de Gemini ni TOKEN_SECRET: solo lo indispensable para correr Python."""
    permitido = ("PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "USERPROFILE")
    return {k: v for k, v in os.environ.items() if k in permitido} | {"PYTHONDONTWRITEBYTECODE": "1"}


def _contar(salida: str, palabra: str) -> int:
    m = re.search(rf"(\d+) {palabra}", salida)
    return int(m.group(1)) if m else 0


def ejecutar_pytest(archivo: str) -> dict:
    try:
        ruta = _ruta_generada(archivo)
    except ValueError as e:                                 # falla de la herramienta: se informa, no se tumba el servicio
        return {"archivo": str(archivo)[:80], "ok": False, "error": str(e)}
    (GENERADOS / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")   # configuración vacía: no hereda la del repositorio
    cmd = [sys.executable, "-I", "-m", "pytest", ruta.name, "-q", "--no-header", "-p", "no:cacheprovider",
           "-c", "pytest.ini", "--rootdir", str(GENERADOS)]
    t0 = time.perf_counter()
    try:
        r = subprocess.run(cmd, cwd=GENERADOS, env=_entorno_minimo(), capture_output=True, text=True,
                           timeout=TIEMPO_MAX_S)
    except subprocess.TimeoutExpired:
        return {"archivo": archivo, "ok": False, "error": f"Tiempo excedido ({TIEMPO_MAX_S} s): se detuvo la ejecución"}
    salida = (r.stdout + r.stderr).strip()
    return {"archivo": archivo, "ok": r.returncode in (0, 5), "codigo_salida": r.returncode,
            "aprobadas": _contar(salida, "passed"), "falladas": _contar(salida, "failed"),
            "omitidas": _contar(salida, "skipped"), "errores": _contar(salida, "error"),
            "segundos": round(time.perf_counter() - t0, 2), "salida": salida[-1200:]}


# ───────────────────────────── mejoras A4: reintento guiado y enmascarado ─────────────────────────────
_MARCAS = {"correo": "<CORREO_SINTETICO>", "número de 18 dígitos (CLABE)": "<CLABE_SINTETICA>", "teléfono de 10 dígitos": "<TELEFONO_SINTETICO>"}


def enmascarar_texto(texto: str, requisito: str) -> tuple[str, int]:
    """Reemplaza correos, CLABE y teléfonos que NO vienen del requisito por un marcador sintético. Devuelve (texto, cuántos)."""
    n = 0

    def _sub(forma):
        def f(m):
            nonlocal n
            if m.group(0).lower() in requisito.lower():
                return m.group(0)
            n += 1
            return _MARCAS[forma]
        return f
    for forma, patron in FORMAS_PII.items():
        texto = patron.sub(_sub(forma), texto)
    return texto, n


def _enmascarar(obj, requisito: str):
    """Recorre cualquier estructura (dict, lista, texto) y enmascara solo los valores de texto."""
    if isinstance(obj, str):
        return enmascarar_texto(obj, requisito)
    if isinstance(obj, list):
        pares = [_enmascarar(x, requisito) for x in obj]
        return [p[0] for p in pares], sum(p[1] for p in pares)
    if isinstance(obj, dict):
        pares = {k: _enmascarar(v, requisito) for k, v in obj.items()}
        return {k: p[0] for k, p in pares.items()}, sum(p[1] for p in pares.values())
    return obj, 0


def _nota_de_correccion(hallazgos: list[str]) -> str:
    """Texto que se agrega al requisito en el reintento. Nunca repite el valor inventado: solo dice qué corregir."""
    pedidos = []
    if any(h.startswith("Dato con forma") for h in hallazgos):
        pedidos.append("No incluyas correos, CLABE ni teléfonos concretos; usa marcadores como <CORREO_SINTETICO_1>")
    pedidos += [h.replace("Falta el escenario de registro", "Incluye un caso para") for h in hallazgos if h.startswith("Falta el escenario")]
    if any("no compila" in h for h in hallazgos):
        pedidos.append("El código pytest debe ser Python válido")
    return "\n\nCORRECCIÓN de un intento anterior: " + ". ".join(pedidos) + "." if pedidos else ""


def generar_validado(requisito: str) -> tuple[dict, dict]:
    """Motor + validador + 2 mejoras. Devuelve (salida, validador) con validador = {ok, hallazgos, reintento, enmascarados}.

    Mejora 1 · reintento guiado: si el validador encuentra algo, o el flujo se detuvo sin dar casos, se repite UNA vez
               (avisando qué corregir); se conserva el intento con menos hallazgos.
    Mejora 2 · enmascarado: lo que parezca correo, CLABE o teléfono y no venga de la entrada se reemplaza por un marcador.
    """
    req = requisito.strip()
    salida = variante.sistema({"requisito": req})                     # nunca la clave «archivo»
    hallazgos, reintento = validar_salida_qa(salida, req), False
    nota = _nota_de_correccion(hallazgos)
    detenido = _flujo_detenido(salida)
    if detenido or (nota and _flujo_ok(salida)):
        segunda = variante.sistema({"requisito": req + nota})
        h2 = validar_salida_qa(segunda, req)
        if _flujo_ok(segunda) and (detenido or len(h2) < len(hallazgos)):
            salida, hallazgos, reintento = segunda, h2, True
    salida, enmascarados = _enmascarar(salida, req)
    finales = validar_salida_qa(salida, req)
    return salida, {"ok": not finales, "hallazgos": finales, "reintento": reintento, "enmascarados": enmascarados}


# ───────────────────────────── generar_pruebas ─────────────────────────────
def generar_pruebas(requisito: str) -> dict:
    """Corre el motor del equipo (con las 2 mejoras) y guarda el pytest generado. Devuelve lo que el validador revisa."""
    salida, validador = generar_validado(requisito)
    art = salida.get("artefacto") or {}
    casos = (art.get("casos") or {}).get("casos") or []
    pytest_ = art.get("pytest") or {}
    codigo, nombre = str(pytest_.get("codigo_pytest", "")), str(pytest_.get("nombre_archivo", ""))
    resultado = {"requisito": requisito.strip(), "abstuvo": bool(salida.get("abstuvo")), "flujo_ok": bool(art.get("flujo_ok")),
                 "archivo": None, "casos": casos, "codigo_pytest": codigo, "aviso": salida.get("respuesta", "")[:300],
                 "reintento": validador["reintento"], "enmascarados": validador["enmascarados"]}
    if resultado["flujo_ok"] and codigo and NOMBRE_VALIDO.match(nombre):
        GENERADOS.mkdir(parents=True, exist_ok=True)
        (GENERADOS / nombre).write_text(codigo, encoding="utf-8")
        resultado["archivo"] = nombre
    return resultado


def herramientas_qa() -> list[Herramienta]:
    return [
        Herramienta("generar_pruebas",
                    "Genera casos de prueba y el archivo pytest de un requisito (ej. RF07.3 contraseñas de menos de 8 caracteres)",
                    {"type": "object", "required": ["requisito"], "additionalProperties": False,
                     "properties": {"requisito": {"type": "string", "minLength": 10, "maxLength": 2000}}},
                    generar_pruebas),
        Herramienta("ejecutar_pytest",
                    "Ejecuta un archivo pytest YA generado (solo test_<nombre>.py de la carpeta de generados; máximo 30 s)",
                    {"type": "object", "required": ["archivo"], "additionalProperties": False,
                     "properties": {"archivo": {"type": "string", "pattern": r"^test_[a-z0-9_]+\.py$", "maxLength": 60}}},
                    ejecutar_pytest, sensible=True),
    ]


# ───────────────────────────── validador de la variante (lógica tradicional) ─────────────────────────────
ESCENARIOS_REGISTRO = {      # RF07: lo que la A4 exige comprobar para v1-qa
    "registro exitoso": r"registr\w*\s+(exitos|correct)|registro exitoso|se registra|permit\w+ registr|crea\w* (la )?cuenta",
    "correo duplicado": r"duplicad|ya (est[aá] |fue )?registrad|ya existe|repetid|[uú]nico",
    "contraseña de menos de 8": r"(contrase[ñn]a|password)[^.]{0,60}(menos de 8|< ?8|\b[1-7]\b ?(car|d[ií]g)|corta)|menos de 8 car",
    "mensaje de confirmación": r"confirmaci[oó]n|registro exitoso|mensaje[^.]{0,40}(registr|[eé]xito)",
}


SUBREQUISITOS_REGISTRO = {"1": "registro exitoso", "2": "correo duplicado", "3": "contraseña de menos de 8", "4": "mensaje de confirmación"}


def _texto_de_casos(casos: list[dict]) -> str:
    return " ".join(" ".join(str(c.get(k, "")) for k in ("titulo", "dado", "cuando", "entonces")) for c in casos).lower()


def validar_salida_qa(salida: dict, requisito: str = "") -> list[str]:
    """Revisa lo que produjo el motor. Devuelve la lista de hallazgos (vacía = todo bien). Sin modelo: solo código.

    1. Hay al menos un caso positivo y uno negativo.
    2. Si el requisito es de registro (RF07): registro exitoso, correo duplicado, contraseña < 8 y confirmación.
    3. El pytest generado compila.
    4. No hay información que no venga de la entrada: nada de los datos de qa-10 ni correos, CLABE o teléfonos
       que el requisito no contenga.
    """
    art = salida.get("artefacto") or {}
    casos = (art.get("casos") or {}).get("casos") or []
    if not casos and _flujo_detenido(salida):
        return ["El flujo se detuvo antes de generar casos: no hay casos que validar"]   # no es un «todo bien»
    codigo = str((art.get("pytest") or {}).get("codigo_pytest", ""))
    return _revisar(casos, codigo, requisito)


def _flujo_ok(salida: dict) -> bool:
    return bool((salida.get("artefacto") or {}).get("flujo_ok"))


def _flujo_detenido(salida: dict) -> bool:
    """El motor no se abstuvo, pero una etapa no pasó su validación y no hay resultado."""
    return not _flujo_ok(salida) and not salida.get("abstuvo")


def _revisar(casos: list[dict], codigo: str, requisito: str) -> list[str]:
    if not casos:
        return []                                           # el motor se abstuvo o el flujo se detuvo: no hay nada que validar
    hallazgos = []
    tipos = {str(c.get("tipo")) for c in casos}
    if "positivo" not in tipos:
        hallazgos.append("Falta un caso positivo")
    if not tipos & ({"negativo"} | TIPOS_LIMITE):
        hallazgos.append("Falta un caso negativo o de límite")
    if re.search(r"RF07|registr", requisito, re.I) or any("RF07" in str(c.get("id_caso", "")) for c in casos):
        texto = _texto_de_casos(casos)
        # Cada subrequisito exige SOLO su escenario (RF07.3 → contraseña corta). Si el requisito no numera
        # subrequisitos, o los trae todos (el archivo RF07 completo), se exigen los cuatro.
        pedidos = [SUBREQUISITOS_REGISTRO[s] for s in sorted(set(re.findall(r"RF07\.(\d)", requisito))) if s in SUBREQUISITOS_REGISTRO]
        for nombre in pedidos or list(ESCENARIOS_REGISTRO):
            if not re.search(ESCENARIOS_REGISTRO[nombre], texto):
                hallazgos.append(f"Falta el escenario de registro: {nombre}")
    if codigo:
        try:
            ast.parse(codigo)
        except SyntaxError as e:
            hallazgos.append(f"El pytest generado no compila (línea {e.lineno}): {e.msg}")
    material = codigo + " " + _texto_de_casos(casos)
    if any(d.lower() in material.lower() for d in DATOS_PROHIBIDOS) or any(d in re.sub(r"\D", "", material) for d in DIGITOS_PROHIBIDOS):
        hallazgos.append("Aparecen datos de una persona real (qa-10) en la salida")
    for forma, patron in FORMAS_PII.items():
        for m in patron.findall(material):
            valor = m if isinstance(m, str) else m[0]
            if valor and valor.lower() not in requisito.lower() and not valor.startswith("<"):
                hallazgos.append(f"Dato con forma de {forma} que no viene de la entrada: {valor[:30]}")
                break
    return hallazgos


def validar_plan_qa(resultado, propuestas: list[tuple[str, dict]]) -> list[str]:
    """Validador del agente: se conecta con agente_servicio.iniciar(..., validador=validar_plan_qa).

    · Revisa con validar_salida_qa cada generación de pruebas de ESTA ejecución.
    · Un ejecutar_pytest solo se ofrece si el archivo salió de generar_pruebas en esta misma ejecución
      (el modelo no puede inventar ni apuntar a otro archivo) y si esa generación no tiene hallazgos.
    """
    hallazgos, generados = [], {}
    for p in resultado.pasos:
        if p.propuesta.get("herramienta") == "generar_pruebas" and p.estado == "ejecutada" and isinstance(p.resultado, dict):
            r = p.resultado
            problemas = _revisar(r.get("casos") or [], r.get("codigo_pytest", ""), r.get("requisito", ""))
            hallazgos += problemas
            if r.get("archivo"):
                generados[r["archivo"]] = problemas
    for nombre, args in propuestas:
        if nombre != "ejecutar_pytest":
            continue
        archivo = args.get("archivo")
        if archivo not in generados:
            hallazgos.append(f"ejecutar_pytest sobre {archivo}: ese archivo no se generó en esta ejecución")
        elif generados[archivo]:
            hallazgos.append(f"No se ofrece ejecutar {archivo}: la generación tiene hallazgos del validador")
    return list(dict.fromkeys(hallazgos))


# ───────────────────────────── guion simulado (LLM_PROVIDER=fake, sin red) ─────────────────────────────
def guion_simulado(tarea: str):
    """Para probar el flujo sin red: generar → (si salió un archivo) ejecutar → responder."""
    requisito = re.search(r"RF\d+[^\n]*", tarea)
    texto = requisito.group(0) if requisito else tarea

    def guion(mensaje: str) -> dict:
        if mensaje.startswith("Tarea:"):
            return {"accion": "usar", "herramienta": "generar_pruebas", "argumentos": {"requisito": texto[:1000]},
                    "razon": "Primero genero las pruebas del requisito"}
        m = re.search(r'"archivo": "(test_[a-z0-9_]+\.py)"', mensaje)
        if mensaje.startswith("Resultado de generar_pruebas") and m:
            return {"accion": "usar", "herramienta": "ejecutar_pytest", "argumentos": {"archivo": m.group(1)},
                    "razon": "Ahora ejecuto el archivo generado"}
        if mensaje.startswith("Resultado de generar_pruebas"):
            return {"accion": "responder", "respuesta": "El motor no generó un archivo pytest confiable para ese requisito.", "fuentes": []}
        return {"accion": "responder", "respuesta": "La ejecución del pytest queda pendiente de tu autorización.", "fuentes": []}
    return guion
