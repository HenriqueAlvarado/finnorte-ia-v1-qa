"""Avance 1 · Revisa las mediciones A–D contra el contrato sin llamar al modelo.

    python guia/av1_contrato.py                                  # contrato_calidad.yaml
    python guia/av1_contrato.py --contrato otro_contrato.yaml    # para comparar dos contratos

Lee bitacora/av1_A.json … av1_D.json, aplica evaluacion.revisar_contrato a cada una y escribe
la tabla meta por meta en bitacora/av1_contrato.md. Sirve para ver qué metas se cumplen y
cuáles no después de cambiar el contrato, sin gastar cuota de Gemini.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from finnorte import evaluacion
from finnorte.config import RAIZ

CONFIGS = {"A": "v1 sin RAG sin controles", "B": "v2 sin RAG sin controles",
           "C": "v2 con RAG sin controles", "D": "v2 con RAG y controles"}


def main() -> None:
    ruta = Path(sys.argv[sys.argv.index("--contrato") + 1]) if "--contrato" in sys.argv[:-1] else RAIZ / "contrato_calidad.yaml"
    contrato = evaluacion.cargar_contrato(ruta)
    revisiones = {}
    for c in CONFIGS:
        archivo = RAIZ / "bitacora" / f"av1_{c}.json"
        if not archivo.exists():
            raise SystemExit(f"Falta {archivo.relative_to(RAIZ)}: corre primero guia/av1_configuraciones.py")
        metricas = json.loads(archivo.read_text(encoding="utf-8"))["metricas"]
        revisiones[c] = evaluacion.revisar_contrato(metricas, contrato)

    metas = [f["meta"] for f in revisiones["A"]]
    lineas = [f"# Mediciones A–D contra `{ruta.name}`", "",
              f"Contrato: {contrato.get('equipo', '?')} · {contrato.get('variante', '?')} · fecha {contrato.get('fecha', '?')}.",
              "Datos: `bitacora/av1_A.json` … `av1_D.json` (gemini-3.1-flash-lite, 20 casos × 3 repeticiones).", "",
              "| Meta | Objetivo | " + " | ".join(CONFIGS) + " |",
              "|---|---|" + "---|" * len(CONFIGS)]
    for i, meta in enumerate(metas):
        celdas = []
        for c in CONFIGS:
            f = revisiones[c][i]
            valor = "—" if f["valor"] is None else (f"{f['valor']:.0f}" if f["valor"] >= 100 else f"{f['valor']:.3g}")
            celdas.append(f"{valor} {'✓' if f['cumple'] else '✗'}")
        lineas.append(f"| {meta} | {revisiones['A'][i]['objetivo']} | " + " | ".join(celdas) + " |")
    lineas += ["", "Metas cumplidas por configuración: " +
               " · ".join(f"{c} {sum(f['cumple'] for f in revisiones[c])}/{len(metas)}" for c in CONFIGS)]

    salida = RAIZ / "bitacora" / "av1_contrato.md"
    salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))
    print(f"\nGuardado en {salida.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
