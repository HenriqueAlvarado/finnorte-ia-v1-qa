"""A1 · Compara búsqueda semántica contra palabras clave (BM25) en el corpus de TU variante.

Antes de correrlo:
  1. Implementa normalizar, coseno y buscar en src/finnorte/retrieval.py (pytest tests/test_a1_vectores.py en verde).
  2. Cambia VARIANTE en src/finnorte/variante.py (ej. "v3-soporte").
  3. Copia evals/a1_plantilla.jsonl como evals/a1_<tu-variante>.jsonl y escribe tus 10 preguntas.

Uso:
  python guia/a1_comparar_variante.py                 # usa la VARIANTE de variante.py
  python guia/a1_comparar_variante.py v3-soporte      # o indícala aquí

Salida: tabla en pantalla y bitacora/a1_comparacion.json (es parte de tu entrega).
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))


def _aviso_pendiente(tipo, valor, tb):
    """Si falta implementar una función del laboratorio, muestra un aviso claro en lugar del error largo."""
    if issubclass(tipo, NotImplementedError):
        print(f"\n✗ Falta implementar una función: {valor}.\n  Revisa el manual del laboratorio y corre las pruebas (pytest -q) antes de este script.")
        return
    sys.__excepthook__(tipo, valor, tb)


sys.excepthook = _aviso_pendiente

from finnorte.config import config
from finnorte.retrieval import Indice, cargar_corpus, guardar_resultados

if len(sys.argv) > 1:
    variante = sys.argv[1]
else:
    from finnorte.variante import VARIANTE as variante
if variante.startswith("v?"):
    sys.exit("✗ Primero cambia VARIANTE en src/finnorte/variante.py (o pásala como argumento).")

carpeta = RAIZ / "corpus" / variante
casos_path = RAIZ / "evals" / f"a1_{variante}.jsonl"
if not carpeta.exists():
    sys.exit(f"✗ No existe {carpeta}. Revisa el nombre de tu variante.")
if not casos_path.exists():
    sys.exit(f"✗ No existe {casos_path}. Copia evals/a1_plantilla.jsonl con ese nombre y escribe tus preguntas.")

casos = [json.loads(l) for l in casos_path.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("//")]
ids = {d.id for d in cargar_corpus(carpeta)}
for c in casos:
    if c["esperado"] not in ids:
        sys.exit(f"✗ '{c['esperado']}' no es un documento de {variante}. Opciones: {sorted(ids)}")

print(f"Variante: {variante} · {len(casos)} preguntas · embeddings '{config().emb_proveedor}'\n")
ind = Indice.desde_carpeta(carpeta)
filas, ac = [], {"vector": [0, 0], "palabras": [0, 0]}
for c in casos:
    q, esp = c["pregunta"], c["esperado"]
    v = [r.fragmento.doc_id for r in ind.buscar(q, k=3)]
    p = [r.fragmento.doc_id for r in ind.buscar_palabras(q, k=3)]
    for modo, lst in (("vector", v), ("palabras", p)):
        ac[modo][0] += lst[:1] == [esp]
        ac[modo][1] += esp in lst
    filas.append({"pregunta": q, "tipo": c.get("tipo", "normal"), "esperado": esp, "vector_top3": v, "palabras_top3": p})
    print(f"{'✓' if v[:1] == [esp] else '✗'} vec  {'✓' if p[:1] == [esp] else '✗'} pal  [{c.get('tipo','normal'):8s}] {q}")

n = len(casos)
print("\nMétodo     acierto@1   acierto@3")
for modo, (a1, a3) in ac.items():
    print(f"{modo:9s}  {a1:>2}/{n}       {a3:>2}/{n}")
filas.append({"resumen": {m: {"acierto@1": a, "acierto@3": b, "n": n} for m, (a, b) in ac.items()},
              "variante": variante, "embeddings": config().emb_proveedor})
print("\nGuardado en", guardar_resultados("a1_comparacion", filas))
