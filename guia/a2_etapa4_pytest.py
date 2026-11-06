"""A2 · Etapa 4 (qa_pytest): mide la v1 contra la v2 con LOS MISMOS casos de entrada.

    python guia/a2_etapa4_pytest.py            # mide la v1 y la v2 (usa los casos congelados si existen)
    python guia/a2_etapa4_pytest.py --nuevos   # vuelve a generar los casos con las etapas 1 y 2
    python guia/a2_etapa4_pytest.py --sin-contexto

Paso 1 · Corre analizar → casos (etapas 1 y 2 del equipo, sin cambiarlas) para 3 requisitos y
         congela la salida en bitacora/luis/a2_casos_entrada.json.
Paso 2 · Corre SOLO la etapa 4 con qa_pytest v1 y con v2 sobre esos casos. RF12 se repite 3 veces
         (consistencia). La validación es la misma en las dos versiones: pytest_compila_y_cubre.
Salida: bitacora/luis/a2_matriz_pytest_v1.md, a2_matriz_pytest_v2.md y a2_pytest_v1_v2.json.

Por qué congelar los casos: si cada versión recibe casos distintos (el modelo varía en las etapas
1 y 2), la diferencia entre v1 y v2 no se puede atribuir a mi prompt.
Con LLM_PROVIDER=fake corre de punta a punta para probar la plomería; los números no valen.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finnorte import llm, prompts, trazas
from finnorte.config import RAIZ, config
from finnorte.etapa_analizar import validar_analizar
from finnorte.etapa_casos import casos_cubren_qa08
from finnorte.etapa_pytest import nombre_test, pytest_compila_y_cubre
from finnorte.pipeline import Etapa, Pipeline, validar_esquema

SALIDA = RAIZ / "bitacora" / "luis"
CASOS_CONGELADOS = SALIDA / "a2_casos_entrada.json"
ENTRADAS = {
    "RF07": "datos/v1-qa/requisitos/RF07-registro.md",
    "RF12": "datos/v1-qa/requisitos/RF12-transferencia.md",
    "RF15": "datos/v1-qa/requisitos/RF15-limite-diario.md",
}
REPETICIONES = {"RF07": 1, "RF12": 3, "RF15": 1}
REINTENTOS = 1        # igual que el valor por defecto de Etapa
TEMPERATURA = 0.2

ARRIBA = Pipeline([
    Etapa("analizar", "qa_analizar", validar=validar_analizar),
    Etapa("casos", "qa_casos", usa=["analizar"], validar=casos_cubren_qa08),
], nombre="v1-qa")


def contexto_de(texto: str, usar: bool) -> str:
    if not usar:
        return "(sin contexto)"
    from finnorte.retrieval import Indice, contexto_para_prompt
    indice = Indice.desde_carpeta(RAIZ / "corpus" / "v1-qa")
    return contexto_para_prompt(indice.buscar(texto, k=4)) or "(sin contexto)"


def generar_casos(usar_contexto: bool) -> dict:
    congelados = {}
    for rf, ruta in ENTRADAS.items():
        texto = (RAIZ / ruta).read_text(encoding="utf-8")
        try:
            r = ARRIBA.ejecutar({"entrada": texto, "contexto": contexto_de(texto, usar_contexto)})
        except Exception as e:  # 429/503 del proveedor: se registra y se sigue
            congelados[rf] = {"ok": False, "error_proveedor": f"{type(e).__name__}: {e}"[:300]}
            continue
        congelados[rf] = {"ok": r.ok, "casos": r.salidas.get("casos"),
                          "etapas": [{"etapa": e.nombre, "prompt": e.prompt, "ok": e.ok, "intentos": e.intentos,
                                      "errores": e.errores[:3]} for e in r.etapas]}
    SALIDA.mkdir(parents=True, exist_ok=True)
    CASOS_CONGELADOS.write_text(json.dumps({"modelo": modelo(), "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                            "contexto": usar_contexto, "entradas": congelados},
                                           ensure_ascii=False, indent=2), encoding="utf-8")
    return congelados


def modelo() -> str:
    c = config()
    return f"{c.llm_proveedor} / {c.llm_modelo}"


def correr_etapa4(version: int, casos: dict) -> dict:
    """Mismo ciclo que Pipeline.ejecutar (esquema → validar= → reintento con los errores), solo para mi etapa."""
    p = prompts.cargar("qa_pytest", version)
    sistema, usuario = p.render(casos=json.dumps(casos, ensure_ascii=False, indent=2))
    previas = {"casos": casos}
    errores: list[str] = []
    errores_primer_intento: list[str] = []
    datos, t0 = None, time.perf_counter()
    for intento in range(1, REINTENTOS + 2):
        consulta = usuario if intento == 1 else (usuario + "\n\nTu respuesta anterior no cumplió el formato. Errores:\n"
                                                 + "; ".join(errores[:5]) + "\n\nDevuelve SOLO el JSON corregido.")
        r = llm.generar(consulta, sistema, json=p.salida_json, temperatura=TEMPERATURA,
                        etiqueta=f"v1-qa/pytest/{p.nombre}")
        datos = r.datos
        errores = validar_esquema(datos, p.esquema)
        if not errores:
            errores = pytest_compila_y_cubre(datos, previas)
        if intento == 1:
            errores_primer_intento = list(errores)
        if not errores:
            break
    trazas.registrar("etapa", flujo="v1-qa", etapa="pytest", prompt=p.nombre, ok=not errores, errores=errores,
                     intentos=intento, latencia_ms=round((time.perf_counter() - t0) * 1000, 1))
    codigo = (datos or {}).get("codigo_pytest", "") if isinstance(datos, dict) else ""
    tests = sorted(set(re.findall(r"def (test_\w+)\s*\(", codigo)))
    esperados = sorted(nombre_test(c["id_caso"]) for c in casos.get("casos", []))
    return {"prompt": p.nombre, "valida": not errores, "intentos": intento,
            "valida_primer_intento": not errores_primer_intento, "errores_primer_intento": errores_primer_intento[:5],
            "errores_final": errores[:5], "nombre_archivo": (datos or {}).get("nombre_archivo") if isinstance(datos, dict) else None,
            "tests": len(tests), "casos": len(esperados), "tests_esperados_presentes": sum(t in tests for t in esperados)}


def corta(t: str, n: int = 90) -> str:
    return str(t).replace("|", "/").replace("\n", " ")[:n]


def escribir_matriz(version: int, filas: list[dict]) -> Path:
    lineas = [f"# Matriz de la etapa 4 · qa_pytest v{version}", "",
              f"Modelo: {modelo()} · casos de entrada: `{CASOS_CONGELADOS.name}` (los mismos para v1 y v2)", "",
              "| Entrada | Rep | Prompt | Artefacto | Válida | Intentos | 1.er intento | Errores (1.er intento) |",
              "|---|---|---|---|---|---|---|---|"]
    for f in filas:
        if "error_proveedor" in f:
            lineas.append(f"| {f['entrada']} | {f['rep']} | qa_pytest.v{version} | — | error del proveedor | — | — | {corta(f['error_proveedor'])} |")
            continue
        artefacto = f"{f['nombre_archivo']} · {f['tests_esperados_presentes']}/{f['casos']} casos con su test"
        lineas.append(f"| {f['entrada']} | {f['rep']} | {f['prompt']} | {artefacto} | {'✓' if f['valida'] else '✗'} | "
                      f"{f['intentos']} | {'✓' if f['valida_primer_intento'] else '✗'} | {corta('; '.join(f['errores_primer_intento']) or '—', 160)} |")
    rf12 = [f for f in filas if f["entrada"] == "RF12" and "error_proveedor" not in f]
    lineas += ["", f"Consistencia (RF12 × {len(rf12)}): "
               + str([(f["valida_primer_intento"], f["tests_esperados_presentes"], f["nombre_archivo"]) for f in rf12])
               + "  ← (válida al 1.er intento, casos con test, nombre_archivo)"]
    ruta = SALIDA / f"a2_matriz_pytest_v{version}.md"
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return ruta


def resumen(filas: list[dict]) -> dict:
    ok = [f for f in filas if "error_proveedor" not in f]
    return {"ejecuciones": len(filas), "errores_proveedor": len(filas) - len(ok),
            "validas_primer_intento": sum(f["valida_primer_intento"] for f in ok),
            "validas_final": sum(f["valida"] for f in ok),
            "reglas_disparadas_primer_intento": sum(len(f["errores_primer_intento"]) for f in ok)}


def main() -> None:
    usar_contexto = "--sin-contexto" not in sys.argv
    if "--nuevos" in sys.argv or not CASOS_CONGELADOS.exists():
        print("Paso 1 · generando casos con analizar → casos…")
        entradas = generar_casos(usar_contexto)
    else:
        entradas = json.loads(CASOS_CONGELADOS.read_text(encoding="utf-8"))["entradas"]
        print(f"Paso 1 · uso los casos congelados de {CASOS_CONGELADOS.name} (--nuevos para regenerarlos)")
    for rf, e in entradas.items():
        n = len((e.get("casos") or {}).get("casos", [])) if e.get("ok") else 0
        print(f"  {rf}: {'ok' if e.get('ok') else 'falló'} · {n} casos {e.get('error_proveedor', '')[:80]}")

    reporte = {"modelo": modelo(), "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "versiones": {}}
    for version in (1, 2):
        filas = []
        for rf, e in entradas.items():
            if not e.get("ok"):
                continue
            for rep in range(1, REPETICIONES[rf] + 1):
                try:
                    filas.append({"entrada": rf, "rep": rep, **correr_etapa4(version, e["casos"])})
                except Exception as ex:
                    filas.append({"entrada": rf, "rep": rep, "error_proveedor": f"{type(ex).__name__}: {ex}"[:300]})
        ruta = escribir_matriz(version, filas)
        reporte["versiones"][f"v{version}"] = {"resumen": resumen(filas), "filas": filas}
        print(f"\nv{version}: {resumen(filas)}  →  {ruta.relative_to(RAIZ)}")
    (SALIDA / "a2_pytest_v1_v2.json").write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDetalle: {(SALIDA / 'a2_pytest_v1_v2.json').relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
