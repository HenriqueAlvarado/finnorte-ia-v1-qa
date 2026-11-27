"""Versión EFICIENCIA de login() (A3 · paso 4).

Qué cambié y por qué (evidencia en analisis_login.md, filas P2 [parcial], P4, P5, P7):
  - P7 El original solo "escala" a un usuario porque está escrito como if/elif anidados: con
    N usuarios eso sería O(N) comparaciones de cadenas en el peor caso. Aquí la "base de
    datos" es un dict, así que buscar un usuario es O(1) sin importar cuántos haya.
  - P4/P2 (compromiso consciente): se compara la contraseña con `==` en vez de
    hmac.compare_digest. `==` de str en CPython corta en el primer carácter distinto, así que
    es más rápido que una comparación en tiempo constante — a cambio, reintroduce el canal
    lateral de tiempo que login_seguridad.py sí cierra. Es records el trade-off que pide la
    comparación (paso 6): esta versión gana velocidad y pierde esa protección puntual.
  - P5 Se quita el espacio final de "user not found ".
  - No se tocó el mensaje de error distinto para "no existe" vs "contraseña mala" (P1): esta
    versión no busca arreglar eso, lo arregla login_seguridad.py.

No usa hash ni sal: mantiene el mismo modelo de datos simple del original (contraseña en
texto plano en el dict) porque el objetivo de esta versión es la velocidad de la búsqueda y
la comparación, no el almacenamiento seguro — eso es exactamente lo que mide la tabla de
comparación (paso 6) en la columna "seguridad" de esta versión.
"""
from __future__ import annotations

# dict en vez de if/elif: tiempo de búsqueda O(1) promedio, no importa cuántos usuarios haya.
_USUARIOS: dict[str, str] = {"admin": "1234"}


def login(user: str, password: str) -> str:
    """Búsqueda O(1) + comparación corta-circuito; prioriza velocidad sobre tiempo constante."""
    clave = _USUARIOS.get(user)
    if clave is None:
        return "user not found"
    if password == clave:
        return "access granted"
    return "wrong password"
