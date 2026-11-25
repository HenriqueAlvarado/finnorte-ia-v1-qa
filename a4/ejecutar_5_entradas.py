"""A4 · Corrida de 5 entradas reales de v1-qa: motor + validador + (si hay archivo) ejecutar_pytest.

    python a4/ejecutar_5_entradas.py primera     → bitacora/monsecode/a4_primera.json
    python a4/ejecutar_5_entradas.py segunda     → bitacora/monsecode/a4_segunda.json   (las MISMAS 5, tras las 2 mejoras)

Guarda, por entrada: hallazgos del validador, tipos de casos, si el flujo terminó, latencia, costo y el resultado
del pytest. Es la evidencia de «primera ejecución», «errores clasificados» y «las mismas 5 entradas otra vez».
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / "src"), str(RAIZ)]

from finnorte import llm, qa_agente  # noqa: E402

ENTRADAS = ["RF07-registro", "RF12-transferencia", "RF15-limite-diario", "RF18-bloqueo-tarjeta", "RF21-comisiones"]


def correr(nombre: str) -> dict:
    texto = (RAIZ / "datos" / "v1-qa" / "requisitos" / f"{nombre}.md").read_text(encoding="utf-8")[:2000]
    fila = {"entrada": nombre, "requisito_chars": len(texto)}
    try:
        r = qa_agente.generar_pruebas(texto)
    except llm.LLMError as e:
        return {**fila, "error_modelo": str(e)[:200]}
    hallazgos = qa_agente._revisar(r["casos"], r["codigo_pytest"], texto)
    fila |= {"flujo_ok": r["flujo_ok"], "abstuvo": r["abstuvo"], "n_casos": len(r["casos"]),
             "tipos": sorted({str(c.get("tipo")) for c in r["casos"]}), "archivo": r["archivo"],
             "hallazgos_validador": hallazgos, "aviso": r["aviso"] if not r["flujo_ok"] else ""}
    if r["archivo"]:
        e = qa_agente.ejecutar_pytest(r["archivo"])
        fila["pytest"] = {k: e.get(k) for k in ("ok", "aprobadas", "falladas", "omitidas", "errores", "segundos")}
    return fila


if __name__ == "__main__":
    etiqueta = sys.argv[1] if len(sys.argv) > 1 else "primera"
    filas = []
    for nombre in ENTRADAS:
        print(f"-> {nombre} ...", flush=True)
        filas.append(correr(nombre))
        print("  ", {k: v for k, v in filas[-1].items() if k in ("flujo_ok", "n_casos", "hallazgos_validador", "error_modelo")}, flush=True)
    salida = RAIZ / "bitacora" / "monsecode" / f"a4_{etiqueta}.json"
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")
    con_hallazgos = sum(1 for f in filas if f.get("hallazgos_validador"))
    print(f"\nGuardado en {salida.relative_to(RAIZ)} · {len(filas)} entradas · {con_hallazgos} con hallazgos del validador")
