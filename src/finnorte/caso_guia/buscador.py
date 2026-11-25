"""Buscador del caso guía con BM25 (palabras clave). No depende de tu A1."""
from __future__ import annotations

from functools import lru_cache

from ..config import RAIZ
from ..retrieval import Resultado, _BM25, cargar_corpus, fragmentar


class BuscadorCasoGuia:
    def __init__(self, carpeta=RAIZ / "corpus" / "comun"):
        self.fragmentos = [f for d in cargar_corpus(carpeta) for f in fragmentar(d)]
        if not self.fragmentos:
            raise ValueError(f"No hay documentos .md en {carpeta}")
        self._bm25 = _BM25([f.texto for f in self.fragmentos])

    def buscar(self, consulta: str, k: int = 4) -> list[Resultado]:
        """Los k fragmentos con mayor puntaje BM25 (> 0). Nunca devuelve documentos confidenciales."""
        puntajes = self._bm25.puntajes(consulta)
        res: list[Resultado] = []
        for i in sorted(range(len(puntajes)), key=lambda i: -puntajes[i]):
            if puntajes[i] <= 0 or len(res) >= k:
                break
            if self.fragmentos[i].clasificacion == "confidencial":
                continue
            res.append(Resultado(self.fragmentos[i], puntajes[i]))
        return res


@lru_cache(maxsize=1)
def buscador() -> BuscadorCasoGuia:
    return BuscadorCasoGuia()
