"""Avance 1 · Mide cuánto aportan los prompts v2, el contexto (RAG) y los controles en TU variante.

    python guia/av1_configuraciones.py --casos evals/v3-soporte.jsonl --rep 3
    python guia/av1_configuraciones.py --guia --casos evals/comun.jsonl      # caso guía, para comparar

Corre los mismos casos en 4 configuraciones de variante.sistema(entrada, config):
  A  prompts v1, sin RAG, sin controles     (línea base ingenua)
  B  prompts v2, sin RAG, sin controles     (solo mejores prompts)
  C  prompts v2, con RAG, sin controles     (aporte del contexto)
  D  prompts v2, con RAG y controles        (tu motor del Avance 1)

Salida: tabla Markdown contra tu contrato, intervalo bootstrap D − A y archivos en bitacora/av1_<config>.json.
Pega la tabla en la sección «Comparación con y sin contexto» de tu documento.
"""
import argparse
import functools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from finnorte import evaluacion

CONFIGS = {
    "A": ("v1 sin RAG sin controles", dict(version_prompt=1, usar_rag=False, controles=False)),
    "B": ("v2 sin RAG sin controles", dict(version_prompt=2, usar_rag=False, controles=False)),
    "C": ("v2 con RAG sin controles", dict(version_prompt=2, usar_rag=True, controles=False)),
    "D": ("v2 con RAG y controles", dict(version_prompt=2, usar_rag=True, controles=True)),
}

ap = argparse.ArgumentParser()
ap.add_argument("--casos", required=True, help="evals/<tu-variante>.jsonl (tus 20 casos)")
ap.add_argument("--rep", type=int, default=3, help="repeticiones por caso (mínimo 3 para el Avance 1)")
ap.add_argument("--guia", action="store_true", help="usar el caso guía (asistente.py) en lugar de tu variante")
ap.add_argument("--sistema", default="finnorte.variante:sistema", help="módulo:función que acepta (entrada, config)")
ap.add_argument("--contrato", default=None, help="ruta del contrato (por defecto contrato_calidad.yaml)")
a = ap.parse_args()

casos = evaluacion.cargar_casos(a.casos)
contrato = evaluacion.cargar_contrato(a.contrato) if a.contrato else evaluacion.cargar_contrato()
print(f"{len(casos)} casos · {a.rep} repeticiones · contrato: {contrato.get('equipo', '?')}\n")
if len(casos) < 20 and not a.guia:
    print(f"⚠ El Avance 1 pide 20 casos; tienes {len(casos)}.\n")
if not a.guia:
    from collections import Counter
    cuenta = Counter(c.get("tipo", "normal") for c in casos)
    raros = sorted(t for t in cuenta if t not in ("normal", "fuera", "limite", "adversarial"))
    if raros:
        print(f"⚠ Tipos no reconocidos: {raros}. Usa normal, fuera, limite o adversarial (detalle en «subtipo»).")
    print("Casos por tipo:", dict(cuenta), "· pedido: 12 normal, 4 fuera, 4 limite/adversarial\n")


def construir(cfg: dict):
    if a.guia:
        from finnorte.asistente import Asistente
        return Asistente.crear(**cfg).responder
    import importlib
    mod, fn = a.sistema.split(":")
    return functools.partial(getattr(importlib.import_module(mod), fn), config=cfg)


filas, aciertos = [], {}
for clave, (nombre, cfg) in CONFIGS.items():
    try:
        r = evaluacion.evaluar(construir(cfg), casos, repeticiones=a.rep, etiqueta=f"av1-{clave}")
    except NotImplementedError as e:
        sys.exit(f"Tu sistema aún no está implementado: {e}")
    m = r["metricas"]
    if m.get("errores_sistema"):
        print(f"⚠ Config {clave}: {m['errores_sistema']} de {m['ejecuciones']} ejecuciones fallaron. Primer error: {r['errores_sistema'][0]}")
        if m["errores_sistema"] == m["ejecuciones"]:
            sys.exit("✗ Tu sistema falla en TODOS los casos: corrígelo antes de medir (prueba con un solo caso).")
    aciertos[clave] = [d["acierto"] for d in r["detalle"]]
    cumple = all(f["cumple"] for f in evaluacion.revisar_contrato(m, contrato))
    filas.append((clave, nombre, m, cumple))
    evaluacion.guardar_reporte(r, f"bitacora/av1_{clave}.json")

print("| Config | Descripción | Exactitud | Citas ok | Alucinación | Fuga | Abstención ok | Consistencia | p95 ms | US$/resp | Contrato |")
print("|---|---|---|---|---|---|---|---|---|---|---|")
for clave, nombre, m, cumple in filas:
    print(f"| {clave} | {nombre} | {m['exactitud']:.2f} | {m.get('citas_correctas', 0):.2f} | {m['alucinacion']:.2f} | {m['fuga_pii']:.2f} | "
          f"{m['abstencion_correcta']:.2f} | {m.get('consistencia', 0):.2f} | {m['latencia_p95_ms']:.0f} | {m['costo_promedio_usd']:.5f} | {'✅' if cumple else '❌'} |")

for x, y in (("A", "B"), ("B", "C"), ("C", "D"), ("A", "D")):
    ic = evaluacion.bootstrap_diferencia(aciertos[x], aciertos[y])
    print(f"\n{y} − {x} en exactitud: {ic['diferencia']:+.2f} (IC 95 % {ic['ic95']})", end="")
print("\n\nSi un intervalo incluye 0, todavía no puedes afirmar que ese cambio mejoró: dilo así en tu documento.")
