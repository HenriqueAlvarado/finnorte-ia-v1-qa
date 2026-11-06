"""A2 · Etapa 3 (qa_revisar): mide la v1 contra la v2 con LAS MISMAS entradas.

    python guia/a2_etapa3_revisar.py --congelar     # crea las entradas congeladas desde bitacora/av1_*.json
    python guia/a2_etapa3_revisar.py                # mide v1 y v2 con el modelo del .env (o LLM_MODEL)
    LLM_PROVIDER=fake python guia/a2_etapa3_revisar.py   # sin red: prueba la plomería (los números no valen)
    python guia/a2_etapa3_revisar.py --pausa 13     # espera entre llamadas (p. ej. límite de 5 por minuto)
    python guia/a2_etapa3_revisar.py --continuar    # retoma una medición cortada sin repetir los pares ya medidos

Entradas: 8 pares (análisis, casos) de la medición del Avance 1 en los que la etapa `casos` pasó su validación
y `revisar` v1 falló o necesitó reintento con gemini-3.1-flash-lite. Se congelan en
bitacora/henrique/a2_revisar_entradas.json para que v1 y v2 reciban exactamente lo mismo.

Métrica: salida válida AL PRIMER INTENTO (esquema + validar_revisar), sin reintentos: 1 llamada por par y versión.
El orden v1/v2 se alterna por par para no favorecer a una versión con la hora de la llamada.
Salida: bitacora/henrique/a2_revisar_v1_v2_<modelo>.json y .md.
"""
from __future__ import annotations

import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finnorte import llm, prompts
from finnorte.config import RAIZ, config
from finnorte.pipeline import validar_esquema
from finnorte.qa_revisar import validar_revisar

DESTINO = RAIZ / "bitacora" / "henrique"
ENTRADAS = DESTINO / "a2_revisar_entradas.json"
# (configuración del Avance 1, posición en el detalle): 6 donde revisar v1 falló y 2 donde necesitó reintento.
ELEGIDOS = [("C", 0), ("C", 9), ("C", 11), ("C", 28), ("C", 41), ("B", 6), ("C", 3), ("D", 23)]
VERSIONES = (1, 2)
PAUSA = float(sys.argv[sys.argv.index("--pausa") + 1]) if "--pausa" in sys.argv[:-1] else 0.0


class CuotaAgotada(Exception):
    pass


def modelo() -> str:
    c = config()
    return f"{c.llm_proveedor}/{c.llm_modelo}"


def congelar() -> None:
    pares = []
    for clave, i in ELEGIDOS:
        d = json.loads((RAIZ / "bitacora" / f"av1_{clave}.json").read_text(encoding="utf-8"))
        x = d["detalle"][i]
        a = x["salida"]["artefacto"]
        revisar = next(e for e in a["etapas"] if e["etapa"] == "revisar")
        pares.append({"par": len(pares) + 1, "origen": f"av1_{clave}.json · detalle[{i}] · {x['id']}",
                      "v1_en_avance1": "falló" if not revisar["ok"] else f"válida al intento {revisar['intentos']}",
                      "analizar": a["analizar"], "casos": a["casos"]})
    texto = json.dumps({"modelo_de_origen": d.get("modelo"), "pares": pares}, ensure_ascii=False, indent=2)
    assert "[dato real de qa-10]" not in texto
    DESTINO.mkdir(parents=True, exist_ok=True)
    ENTRADAS.write_text(texto, encoding="utf-8")
    print(f"{len(pares)} pares congelados en {ENTRADAS.relative_to(RAIZ).as_posix()}")


def categoria(error: str) -> str:
    """Categoría de un error de validar_revisar (los de esquema se marcan aparte, en medir_par)."""
    if error.startswith("cobertura_tipos.") or error.startswith("casos_faltantes"):
        return "conteo o faltantes"
    if error.startswith("cumple_qa08"):
        return "cumple_qa08 incoherente"
    if "falta su hallazgo" in error:
        return "hallazgo no reportado"
    return "otro"


def medir_par(par: dict, version: int) -> dict:
    p = prompts.cargar("qa_revisar", version)
    previas = {"analizar": par["analizar"], "casos": par["casos"]}
    sistema, usuario = p.render(**{k: json.dumps(v, ensure_ascii=False, indent=2) for k, v in previas.items()})
    time.sleep(PAUSA)
    try:
        r = llm.generar(usuario, sistema, json=True, temperatura=0.2, etiqueta=f"a2-revisar/{p.nombre}")
    except llm.LLMError as e:
        if "429" in str(e):
            raise CuotaAgotada(f"cuota agotada (429) en el par {par['par']} v{version}")
        return {"version": version, "error_proveedor": str(e).split("\n")[0][:150]}
    errores_esquema = validar_esquema(r.datos, p.esquema)
    errores = errores_esquema or validar_revisar(r.datos, previas)   # como el pipeline: validar= solo si pasa el esquema
    categorias = ["esquema"] if errores_esquema else sorted({categoria(e) for e in errores})
    return {"version": version, "valida": not errores, "errores": errores[:5], "categorias": categorias,
            "salida": r.datos,   # para revisar después por qué falló (la regla 4 del prompt prohíbe datos sensibles)
            "latencia_ms": r.latencia_ms, "costo_usd": r.costo_usd, "tokens": [r.tokens_entrada, r.tokens_salida]}


def main() -> None:
    if "--congelar" in sys.argv or not ENTRADAS.exists():
        congelar()
        if "--congelar" in sys.argv:
            return
    pares = json.loads(ENTRADAS.read_text(encoding="utf-8"))["pares"]
    print(f"Modelo {modelo()} · {len(pares)} pares · v1 contra v2 · 1 llamada por par y versión")
    nombre = re.sub(r"[^\w.-]+", "_", config().llm_modelo)
    ruta = DESTINO / f"a2_revisar_v1_v2_{nombre}.json"
    filas = []
    if "--continuar" in sys.argv and ruta.exists():
        previo = json.loads(ruta.read_text(encoding="utf-8"))
        if previo["modelo"] != modelo():
            sys.exit(f"✗ {ruta.name} se midió con {previo['modelo']}, no con {modelo()}.")
        filas = previo["filas"]
        print(f"--continuar: {len(filas)} pares ya medidos; sigo con los demás")
    hechos = {f["par"] for f in filas}
    try:
        for par in pares:
            if par["par"] in hechos:
                continue
            orden = VERSIONES if par["par"] % 2 else VERSIONES[::-1]
            res = {v: medir_par(par, v) for v in orden}
            filas.append({"par": par["par"], "origen": par["origen"], "v1_en_avance1": par["v1_en_avance1"],
                          **{f"v{v}": res[v] for v in VERSIONES}})
            print(f"  par {par['par']} ({par['origen']}): " + " · ".join(
                f"v{v} {'válida' if res[v].get('valida') else 'ERROR PROVEEDOR' if 'error_proveedor' in res[v] else 'inválida'}"
                for v in VERSIONES))
            guardar(filas, nombre, completo=len(filas) == len(pares))
    except CuotaAgotada as e:
        guardar(filas, nombre, completo=False)
        sys.exit(f"✗ {e}. Se guardaron {len(filas)} pares completos; retoma con --continuar (y --pausa si es por minuto).")
    print(f"\nGuardado en bitacora/henrique/a2_revisar_v1_v2_{nombre}.json y .md")


def guardar(filas: list[dict], nombre: str, completo: bool) -> None:
    filas = sorted(filas, key=lambda f: f["par"])
    resumen = {}
    for v in VERSIONES:
        rs = [f[f"v{v}"] for f in filas if "error_proveedor" not in f[f"v{v}"]]
        resumen[f"v{v}"] = {"medidos": len(rs), "validas_primer_intento": sum(r["valida"] for r in rs),
                            "categorias_de_error": dict(Counter(c for r in rs for c in r["categorias"])),
                            "errores_proveedor": len(filas) - len(rs)}
    salida = {"modelo": modelo(), "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "completo": completo,
              "resumen": resumen, "filas": filas}
    DESTINO.mkdir(parents=True, exist_ok=True)
    (DESTINO / f"a2_revisar_v1_v2_{nombre}.json").write_text(json.dumps(salida, ensure_ascii=False, indent=2),
                                                             encoding="utf-8")
    md = [f"# Etapa 3 · qa_revisar v1 contra v2 · {modelo()}", ""]
    if not completo:
        md += [f"**INCOMPLETA:** solo {len(filas)} pares medidos.", ""]
    md += [f"{len(filas)} pares congelados (`{ENTRADAS.name}`), 1 llamada por par y versión, válida = esquema + "
           "`validar_revisar` al primer intento, sin reintentos.", "",
           "| Par | Origen | v1 en el Avance 1 | v1 | v2 | Errores v1 | Errores v2 |", "|---|---|---|---|---|---|---|"]
    def celda(r):
        return "error del proveedor" if "error_proveedor" in r else ("✓" if r["valida"] else "✗")
    for f in filas:
        md.append(f"| {f['par']} | {f['origen']} | {f['v1_en_avance1']} | {celda(f['v1'])} | {celda(f['v2'])} | "
                  f"{', '.join(f['v1'].get('categorias', [])) or '—'} | {', '.join(f['v2'].get('categorias', [])) or '—'} |")
    md += ["", "| Versión | Válidas al 1.er intento | Errores por categoría | Errores del proveedor |", "|---|---|---|---|"]
    for v in VERSIONES:
        r = resumen[f"v{v}"]
        md.append(f"| v{v} | {r['validas_primer_intento']}/{r['medidos']} | {r['categorias_de_error'] or '—'} | "
                  f"{r['errores_proveedor']} |")
    (DESTINO / f"a2_revisar_v1_v2_{nombre}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    if completo:
        print("\n" + "\n".join(md[-4:]))


if __name__ == "__main__":
    main()
