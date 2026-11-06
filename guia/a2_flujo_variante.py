"""A2 · Flujo completo de la variante v1-qa: requisito → analizar → casos → revisar → pytest.

    python guia/a2_flujo_variante.py --rep 3                 # 3 repeticiones de RF12 (por defecto)
    python guia/a2_flujo_variante.py --requisito RF07 --rep 1
    python guia/a2_flujo_variante.py --version 1            # usa FLUJO_V1 (todos los prompts en v1)
    python guia/a2_flujo_variante.py --sin-contexto         # sin RAG, para aislar el efecto del corpus
    python guia/a2_flujo_variante.py --rep 2 --agregar      # agrega 2 repeticiones a la matriz que ya existe
    LLM_PROVIDER=fake python guia/a2_flujo_variante.py      # sin red: solo prueba la plomería

Qué hace
  1. Corre FLUJO (las 4 etapas del equipo, con su validar= real) sobre un requisito de
     datos/v1-qa/requisitos/, repitiéndolo --rep veces para ver la consistencia.
  2. Cada etapa se valida contra su esquema y su regla de negocio; si falla, reintenta con
     los errores y, si sigue mal, el flujo se detiene ahí (detener_en_error).
  3. Escribe la matriz de trazabilidad en bitacora/a2_matriz.md e imprime el resumen.

Con LLM_PROVIDER=fake corre de punta a punta pero los números no valen.
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finnorte.config import RAIZ, config
from finnorte.retrieval import Indice, contexto_para_prompt
from finnorte.variante import FLUJO, FLUJO_V1, VARIANTE


def _arg(nombre: str, defecto: str) -> str:
    return sys.argv[sys.argv.index(nombre) + 1] if nombre in sys.argv[:-1] else defecto


REQUISITO = _arg("--requisito", "RF12")
REPETICIONES = int(_arg("--rep", "3"))
USAR_CONTEXTO = "--sin-contexto" not in sys.argv
VERSION = _arg("--version", "")
FLUJO_USADO = FLUJO_V1 if (VERSION == "1" and FLUJO_V1) else FLUJO
SALIDA = RAIZ / "bitacora" / "a2_matriz.md"
AGREGAR = "--agregar" in sys.argv     # conserva las repeticiones completas de la matriz anterior
K = 4


def modelo() -> str:
    c = config()
    return f"{c.llm_proveedor}/{c.llm_modelo}"


def ruta_requisito(rf: str) -> Path:
    coincidencias = sorted((RAIZ / "datos" / VARIANTE / "requisitos").glob(f"{rf}-*.md"))
    if not coincidencias:
        disponibles = [p.name.split("-")[0] for p in sorted((RAIZ / "datos" / VARIANTE / "requisitos").glob("*.md"))]
        raise SystemExit(f"No hay requisito {rf} en datos/{VARIANTE}/requisitos/. Hay: {', '.join(disponibles)}")
    return coincidencias[0]


def contexto_de(texto: str) -> str:
    if not USAR_CONTEXTO:
        return "(sin contexto)"
    indice = Indice.desde_carpeta(RAIZ / "corpus" / VARIANTE)
    return contexto_para_prompt(indice.buscar(texto, k=K)) or "(sin contexto)"


def corta(t, n: int = 150) -> str:
    return str(t).replace("|", "/").replace("\n", " ")[:n]


def resumen_artefacto(etapa: str, salida) -> str:
    """Una línea por etapa: lo mínimo para rastrear el artefacto sin volcar el JSON."""
    if not isinstance(salida, dict):
        return "—"
    if etapa == "analizar":
        return (f"{salida.get('requisito_id')} · dinero={salida.get('es_operacion_dinero')} · "
                f"{len(salida.get('reglas_negocio') or [])} reglas · {len(salida.get('ambiguedades') or [])} ambigüedades")
    if etapa == "casos":
        casos = salida.get("casos") or []
        return f"{len(casos)} casos · tipos: {len({c.get('tipo') for c in casos})}"
    if etapa == "revisar":
        return (f"cumple_qa08={salida.get('cumple_qa08')} · {len(salida.get('casos_faltantes') or [])} faltantes · "
                f"{len(salida.get('hallazgos') or [])} hallazgos")
    if etapa == "pytest":
        codigo = salida.get("codigo_pytest") or ""
        return (f"{salida.get('nombre_archivo')} · {codigo.count('def test_')} tests · "
                f"{len(codigo.splitlines())} lineas")
    return corta(salida, 60)


def escribir_matriz(corridas: list[dict], ruta_req: Path) -> Path:
    c = [f"# Matriz del flujo completo · {VARIANTE}", "",
         f"Modelo: {modelo()} · entrada: `{ruta_req.relative_to(RAIZ).as_posix()}` · "
         f"repeticiones: {len(corridas)} · contexto (RAG): {'sí, k=' + str(K) if USAR_CONTEXTO else 'no'} · "
         f"flujo: {FLUJO_USADO.nombre}", "",
         "Cada etapa valida contra su esquema y su `validar=`. Si falla tras el reintento, el flujo se detiene ahí.", "",
         "| Rep | Etapa | Prompt | Artefacto | Válida | Intentos | ms | USD | Errores |",
         "|---|---|---|---|---|---|---|---|---|"]
    for corrida in corridas:
        if corrida.get("error_proveedor"):
            c.append(f"| {corrida['rep']} | — | — | — | error del proveedor | — | — | — | "
                     f"{corta(corrida['error_proveedor'])} |")
            continue
        for e in corrida["etapas"]:
            c.append(f"| {corrida['rep']} | {e['etapa']} | {e['prompt']} | {e['artefacto']} | "
                     f"{'✓' if e['ok'] else '✗'} | {e['intentos']} | {e['latencia_ms']:.0f} | "
                     f"{e['costo_usd']:.6f} | {corta('; '.join(e['errores']) or '—')} |")
        c.append(f"| {corrida['rep']} | **total** | | | {'✓' if corrida['ok'] else '✗'} | | "
                 f"{corrida['latencia_ms']:.0f} | {corrida['costo_usd']:.6f} | |")

    hechas = [x for x in corridas if not x.get("error_proveedor")]
    c += ["", "## Consistencia entre repeticiones", ""]
    for etapa in [e.nombre for e in FLUJO_USADO.etapas]:
        vistas = [next((e for e in x["etapas"] if e["etapa"] == etapa), None) for x in hechas]
        c.append(f"- **{etapa}**: " + " · ".join(
            f"rep {x['rep']}: {'✓' if v and v['ok'] else ('✗' if v else 'no llegó')}"
            + (f" ({v['artefacto']})" if v else "") for x, v in zip(hechas, vistas)))
    c += ["", f"Flujos completos: {sum(x['ok'] for x in hechas)}/{len(corridas)} intentadas · "
              f"errores del proveedor: {len(corridas) - len(hechas)} · "
              f"costo total: {sum(x.get('costo_usd', 0.0) for x in corridas):.6f} USD"]
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text("\n".join(c) + "\n", encoding="utf-8")
    return SALIDA


def leer_matriz(ruta: Path, ruta_req: Path) -> list[dict]:
    """Repeticiones de una matriz anterior (para --agregar). Las que fallaron por el proveedor se descartan:
    son justo las que se vuelven a correr. Se niega a mezclar corridas de otro modelo, entrada o flujo."""
    if not ruta.exists():
        return []
    texto = ruta.read_text(encoding="utf-8")
    esperado = {"Modelo": modelo(), "entrada": f"`{ruta_req.relative_to(RAIZ).as_posix()}`",
                "flujo": FLUJO_USADO.nombre}
    for campo, valor in esperado.items():
        m = re.search(rf"{campo}: ([^·\n]+)", texto)
        if not m or m.group(1).strip() != valor:
            raise SystemExit(f"La matriz anterior tiene otro {campo} ({m.group(1).strip() if m else '?'}; "
                             f"ahora {valor}): no se pueden mezclar. Corre sin --agregar.")
    corridas: dict[int, dict] = {}
    for linea in texto.splitlines():
        if not re.match(r"^\| \d+ \|", linea):
            continue
        c = [x.strip() for x in linea.strip().strip("|").split("|")]
        if c[4] == "error del proveedor":
            continue
        x = corridas.setdefault(int(c[0]), {"rep": int(c[0]), "etapas": []})
        if c[1] == "**total**":
            x.update(ok=c[4] == "✓", latencia_ms=float(c[6]), costo_usd=float(c[7]))
        else:
            x["etapas"].append({"etapa": c[1], "prompt": c[2], "artefacto": c[3], "ok": c[4] == "✓",
                                "intentos": int(c[5]), "latencia_ms": float(c[6]), "costo_usd": float(c[7]),
                                "errores": [] if c[8] == "—" else c[8].split("; ")})
    return [x for x in corridas.values() if "ok" in x]


def main() -> None:
    ruta_req = ruta_requisito(REQUISITO)
    texto = ruta_req.read_text(encoding="utf-8")
    contexto = contexto_de(texto)
    print(f"flujo {FLUJO_USADO.nombre} | modelo {modelo()} | entrada {ruta_req.name} | "
          f"{REPETICIONES} repeticiones | contexto {'si' if USAR_CONTEXTO else 'no'}")
    print("etapas: " + " -> ".join(f"{e.nombre}({e.prompt}{'.v' + str(e.version) if e.version else ''})"
                                  for e in FLUJO_USADO.etapas))

    corridas: list[dict] = leer_matriz(SALIDA, ruta_req) if AGREGAR else []
    if AGREGAR:
        print(f"--agregar: conservo {len(corridas)} repeticiones completas de {SALIDA.name}")
    inicio = max((x["rep"] for x in corridas), default=0) + 1
    for rep in range(inicio, inicio + REPETICIONES):
        t0 = time.perf_counter()
        try:
            r = FLUJO_USADO.ejecutar({"entrada": texto, "contexto": contexto})
        except Exception as exc:          # 429/503 del proveedor: se registra y se sigue
            corridas.append({"rep": rep, "error_proveedor": f"{type(exc).__name__}: {exc}"[:300]})
            print(f"  rep {rep}: error del proveedor | {str(exc)[:200]}")
            continue
        etapas = [{"etapa": e.nombre, "prompt": e.prompt, "ok": e.ok, "intentos": e.intentos,
                   "errores": e.errores, "latencia_ms": e.latencia_ms, "costo_usd": e.costo_usd,
                   "artefacto": resumen_artefacto(e.nombre, e.salida)} for e in r.etapas]
        corridas.append({"rep": rep, "ok": r.ok, "etapas": etapas, "costo_usd": r.costo_usd,
                         "latencia_ms": (time.perf_counter() - t0) * 1000})
        print(f"  rep {rep}: {'completo' if r.ok else 'SE DETUVO en ' + r.etapas[-1].nombre} | "
              f"{len(r.etapas)}/{len(FLUJO_USADO.etapas)} etapas | {r.costo_usd:.6f} USD")
        for e in etapas:
            print(f"      {e['etapa']:9} {'ok ' if e['ok'] else 'FALLA'} intentos={e['intentos']} "
                  f"{e['artefacto']}" + (f"\n          errores: {'; '.join(e['errores'])[:300]}" if e["errores"] else ""))

    ruta = escribir_matriz(corridas, ruta_req)
    hechas = [x for x in corridas if not x.get("error_proveedor")]
    print(f"\nflujos completos: {sum(x['ok'] for x in hechas)}/{len(corridas)} intentadas | "
          f"costo total: {sum(x.get('costo_usd', 0.0) for x in corridas):.6f} USD")
    print(f"matriz: {ruta.relative_to(RAIZ).as_posix()}")


if __name__ == "__main__":
    main()
