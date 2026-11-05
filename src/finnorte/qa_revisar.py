"""Etapa 3 (revisar): validación de negocio de la salida de prompts/qa_revisar.v1.md.

    Etapa("revisar", "qa_revisar", usa=["analizar", "casos"], validar=validar_revisar)

El pipeline llama a `validar_revisar(datos, salidas)` solo cuando la salida ya cumple el esquema.
Manda el código: recalcula el conteo desde salidas["casos"] con las MISMAS reglas que el prompt y
devuelve un error por cada diferencia (el pipeline reintenta con ellos). Ningún mensaje de error
incluye el valor sensible detectado: los errores vuelven al modelo y quedan en la bitácora.
"""
from __future__ import annotations

import functools
import json
import re
from typing import Any

from . import pii
from .config import RAIZ

TIPOS = ["positivo", "negativo", "limite", "monto_cero", "monto_negativo",
         "limite_exacto", "un_centavo_arriba", "idempotencia"]
TIPOS_BASICOS = TIPOS[:3]
BLOQUEAN_QA08 = {"datos_reales", "entonces_no_verificable", "id_mal_formado"}   # regla 4.1
CAMPOS_REVISADOS = ("titulo", "dado", "cuando", "entonces")
DOMINIOS_PRUEBA = {"ejemplo.com", "test.com"}     # además, cualquier dominio terminado en .example
TIPOS_SENSIBLES = ("CLABE", "CORREO", "TELEFONO")
QA10 = RAIZ / "corpus" / "v1-qa" / "qa-10-aclaraciones-ejemplo.md"

_RE_REQUISITO = re.compile(r"^RF\d{2}$")
_RE_RF = re.compile(r"RF\d{2}(?!\d)")
_RE_ID_CASO = re.compile(r"^CP-(RF\d{2})-\d{2}$")


# --- detección de datos sensibles -----------------------------------------------------------

def _normalizar(tipo: str, valor: str) -> str:
    if tipo == "CORREO":
        return valor.strip().rstrip(".").lower()
    return re.sub(r"\D", "", valor)


def _candidatos(texto: str) -> list[tuple[str, str]]:
    """(tipo, valor normalizado) de cada valor con forma de CLABE, correo o teléfono."""
    return [(t, _normalizar(t, v)) for t, v in pii.detectar(texto) if t in TIPOS_SENSIBLES]


@functools.cache
def _conocidos_qa10() -> frozenset[str]:
    """Datos de la clienta de qa-10, leídos del corpus (no se copian al código)."""
    if not QA10.exists():
        return frozenset()
    return frozenset(v for _, v in _candidatos(QA10.read_text(encoding="utf-8")))


def _textos(obj: Any):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        yield str(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _textos(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _textos(v)


def _set_datos_prueba(analizar: dict) -> set[str]:
    """Valores sintéticos declarados por la etapa 1, normalizados igual que los candidatos."""
    permitidos: set[str] = set()
    for texto in _textos(analizar.get("datos_prueba")):
        permitidos.add(texto.strip().lower())
        digitos = re.sub(r"\D", "", texto)
        if digitos:
            permitidos.add(digitos)
        permitidos.update(v for _, v in _candidatos(texto))
    return permitidos


def es_dato_real(tipo: str, valor: str, datos_prueba: set[str]) -> bool:
    """Orden acordado (4 pasos). `valor` ya viene normalizado."""
    if valor in _conocidos_qa10():                                   # 1. trampa qa-10: siempre real
        return True
    if tipo == "CORREO":                                             # 2. dominio de prueba exacto
        dominio = valor.rsplit("@", 1)[-1]
        if dominio in DOMINIOS_PRUEBA or dominio.endswith(".example"):
            return False
    if valor in datos_prueba:                                        # 3. declarado por la etapa 1
        return False
    return True                                                      # 4. lo demás es real


# --- lectura de las entradas ----------------------------------------------------------------

def _lista_casos(casos: Any) -> list[dict]:
    if isinstance(casos, dict):
        casos = casos.get("casos", [])
    if not isinstance(casos, list):
        return []
    return [c if isinstance(c, dict) else {} for c in casos]


def caso_id(caso: dict, posicion: int) -> str:
    """id_caso tal cual; si falta o está vacío, SIN-ID-<n> (n empieza en 1)."""
    id_ = caso.get("id_caso")
    return id_ if isinstance(id_, str) and id_.strip() else f"SIN-ID-{posicion}"


def id_mal_formado(cid: str, requisito: str) -> bool:
    """Falta (SIN-ID-<n>), no sigue CP-RFxx-nn, o su RFxx no es el requisito revisado."""
    m = _RE_ID_CASO.match(cid)
    return cid.startswith("SIN-ID-") or not m or m.group(1) != requisito


def tipos_obligatorios(analizar: dict) -> list[str]:
    """3 u 8 tipos; si es_operacion_dinero falta o no es booleano, se asume true."""
    dinero = analizar.get("es_operacion_dinero")
    return TIPOS_BASICOS if dinero is False else TIPOS


# --- validación -----------------------------------------------------------------------------

def validar_revisar(datos: dict, salidas: dict) -> list[str]:
    analizar = salidas.get("analizar")
    analizar = analizar if isinstance(analizar, dict) else {}
    requisito = analizar.get("requisito_id")
    if not (isinstance(requisito, str) and _RE_REQUISITO.match(requisito)):
        return ["analizar no trae un requisito_id con forma RFxx: la entrada no sirve para auditar"]

    errores: list[str] = []

    # 1. Mi propia salida: ningún valor con forma de CLABE, correo o teléfono, sin excepción.
    tipos_en_salida = sorted({t for t, _ in _candidatos(json.dumps(datos, ensure_ascii=False))})
    for t in tipos_en_salida:
        errores.append(f"tu respuesta contiene un valor con forma de {t}: describe el patrón, no copies el valor")

    casos = _lista_casos(salidas.get("casos"))
    ids = [caso_id(c, i) for i, c in enumerate(casos, start=1)]
    hallazgos = datos.get("hallazgos", [])
    reportados = {(h["caso_id"], h["tipo"]) for h in hallazgos}

    # 2. Datos reales detectados por código (4.4b, también en titulo); los no reportados son error.
    datos_prueba = _set_datos_prueba(analizar)
    reales_codigo: set[str] = set()
    for cid, caso in zip(ids, casos):
        for campo in CAMPOS_REVISADOS:
            texto = caso.get(campo)
            if not isinstance(texto, str):
                continue
            for t in sorted({t for t, v in _candidatos(texto) if es_dato_real(t, v, datos_prueba)}):
                reales_codigo.add(cid)
                if (cid, "datos_reales") not in reportados:
                    errores.append(f"el caso {cid} tiene un valor con forma de {t} en el campo {campo} "
                                   f"que no es dato de prueba, y falta su hallazgo datos_reales")

    # 3. Ids mal formados detectados por código; los que el modelo no reportó son error.
    mal_formados_codigo = {cid for cid in ids if id_mal_formado(cid, requisito)}
    for cid in ids:
        if cid in mal_formados_codigo and (cid, "id_mal_formado") not in reportados:
            errores.append(f"el caso {cid} tiene un id_caso que falta, no sigue CP-RFxx-nn o es de otro "
                           f"requisito, y falta su hallazgo id_mal_formado")

    # 4. Todo caso_id de los hallazgos existe en los casos (4.3.4).
    for i, h in enumerate(hallazgos):
        if h["caso_id"] not in ids:
            errores.append(f"hallazgos[{i}].caso_id no corresponde a ningún caso de la entrada "
                           f"(usa el id_caso tal cual o SIN-ID-<n>)")

    # 5. Recuento con las mismas reglas que el prompt.
    reales = reales_codigo | {h["caso_id"] for h in hallazgos if h["tipo"] == "datos_reales"}
    conteo = dict.fromkeys(TIPOS, 0)
    for cid, caso in zip(ids, casos):
        tipo = caso.get("tipo")
        if tipo not in conteo:                               # tipo_invalido: no cuenta
            continue
        rf = _RE_RF.search(cid) if not cid.startswith("SIN-ID-") else None
        if rf and rf.group(0) != requisito:                  # evidencia de otro requisito: no cuenta
            continue
        if cid in reales:                                    # datos reales: no cuenta
            continue
        conteo[tipo] += 1                                    # SUPUESTO y SIN-ID sí cuentan

    for t in TIPOS:
        x = datos["cobertura_tipos"][t]
        if x != conteo[t]:
            errores.append(f"cobertura_tipos.{t} reportado como {x} pero el conteo real en casos es {conteo[t]}")

    # 6. casos_faltantes = obligatorios con conteo 0 (4.3.1 y 4.3.2).
    esperados = {(requisito, t) for t in tipos_obligatorios(analizar) if conteo[t] == 0}
    dados = {(f["requisito"], f["tipo_faltante"]) for f in datos["casos_faltantes"]}
    for req, t in sorted(esperados - dados):
        errores.append(f"casos_faltantes debe incluir {t} para {req}")
    for req, t in sorted(dados - esperados):
        errores.append(f"casos_faltantes no debe incluir {t} para {req}")

    # 7. cumple_qa08 según la regla 4.1 (hallazgos del modelo + lo que detectó el código).
    bloqueos = {h["tipo"] for h in hallazgos if h["tipo"] in BLOQUEAN_QA08}
    if reales_codigo:
        bloqueos.add("datos_reales")
    if mal_formados_codigo:
        bloqueos.add("id_mal_formado")
    esperado = not esperados and not bloqueos
    if datos["cumple_qa08"] != esperado:
        motivo = ("no hay tipos faltantes ni hallazgos que lo bloqueen" if esperado else
                  "hay " + ", ".join((["tipos faltantes"] if esperados else []) + sorted(bloqueos)))
        errores.append(f"cumple_qa08 reportado como {str(datos['cumple_qa08']).lower()} "
                       f"pero debe ser {str(esperado).lower()}: {motivo}")

    return errores
