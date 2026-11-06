import json, re, sys, unicodedata, collections, pathlib, difflib
raiz = pathlib.Path(sys.argv[1]); sys.path.insert(0, str(raiz / "src"))
from finnorte import pii, evaluacion
def norm(t): return "".join(c for c in unicodedata.normalize("NFD", str(t).lower()) if unicodedata.category(c) != "Mn")
corpus = {}
for p in (raiz / "corpus/v1-qa").glob("*.md"):
    txt = p.read_text(encoding="utf-8"); corpus[re.search(r"^id: (\S+)", txt, re.M).group(1)] = txt
todo = norm(" ".join(corpus.values()))
casos = evaluacion.cargar_casos(raiz / "evals/v1-qa.jsonl")
print("Casos:", len(casos), dict(collections.Counter(c["tipo"] for c in casos)))
ids = [c["id"] for c in casos]; print("Ids repetidos:", [i for i, n in collections.Counter(ids).items() if n > 1] or "ninguno")
for c in casos:
    e, avisos = c["esperado"], []
    if "requisito" not in c["entrada"]: avisos.append("entrada sin clave requisito")
    for f in e.get("fuentes", []):
        if f not in corpus: avisos.append(f"fuente {f} no existe")
    for v in e.get("contiene", []):
        if norm(v) not in todo and v not in ("@RF07", "SUPUESTO"):
            avisos.append(f"'{v}' no está literal en el corpus (derivado)")
        elif e.get("fuentes") and v not in ("@RF07", "SUPUESTO") and not any(norm(v) in norm(corpus[f]) for f in e["fuentes"] if f in corpus):
            avisos.append(f"'{v}' no está en sus fuentes {e['fuentes']}")
    for v in e.get("no_contiene", []):
        if norm(v) not in norm(corpus["qa-10"]): avisos.append(f"no_contiene '{v}' no viene de qa-10")
    req = c["entrada"].get("requisito", "")
    largo = max((difflib.SequenceMatcher(None, norm(req), norm(t)).find_longest_match().size for t in corpus.values()), default=0)
    if c["tipo"] == "normal" and largo > 35: avisos.append(f"copia literal del corpus ({largo} caracteres seguidos)")
    print(f"{c['id']:4} {c['tipo']:11} {'OK' if not avisos else '; '.join(avisos)}")
print("\n¿Una respuesta 'perfecta' pero con datos sintéticos realistas reprueba por PII?")
caso = next(c for c in casos if c["id"] == "q01")
for etiqueta, extra in [("sin datos", ""), ("correo sintético", " Dado el correo nuevo.cliente@ejemplo.com"), ("CLABE sintética", " CLABE 646180157000000004"), ("marcador", " Dado el correo <CORREO_SINTETICO_1>")]:
    salida = {"respuesta": " ".join(caso["esperado"]["contiene"]) + extra, "fuentes": caso["esperado"]["fuentes"], "abstuvo": False}
    r = evaluacion.calificar_caso(caso, salida); print(f"  {etiqueta:17} acierto={r.acierto} fuga={r.fuga} {r.motivos}")
contrato = evaluacion.cargar_contrato(raiz / "contrato_calidad.yaml")
print("\nContrato carga:", contrato["variante"], "metas:", len(contrato["metas"]), "| claves desconocidas:", [k for k in contrato["metas"] if k not in evaluacion.REGLAS] or "ninguna")
