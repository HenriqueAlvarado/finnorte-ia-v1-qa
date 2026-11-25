"""Motor de DEMOSTRACIÓN para /v1/variante (base del laboratorio, NO es tu motor).

/v1/variante llama primero a TU variante.sistema() (Avance 1). Solo si todavía lanza
NotImplementedError usa este demo, y la respuesta lo dice con "motor": "demo".
En la A3 conectas tu motor real y creas tu propio endpoint POST /v1/<tu-variante>.
"""
from __future__ import annotations


def sistema(entrada: dict) -> dict:
    textos = [str(v) for v in entrada.values() if isinstance(v, str) and v.strip()]
    if not textos:
        raise ValueError("La entrada debe traer al menos un campo de texto, por ejemplo {\"pregunta\": \"...\"}")
    return {
        "motor": "demo",
        "aviso": "Respuesta de DEMOSTRACIÓN: tu variante.sistema() (Avance 1) aún no está implementado. En la A3 conectas tu motor real.",
        "entrada_recibida": entrada,
        "salida": {"resumen": textos[0][:200], "campos": sorted(entrada)},
    }
