"""A3 · Versión EFICIENCIA del login().

Mantiene todas las garantías de seguridad y quita trabajo innecesario:
  · El hash de relleno (para usuarios inexistentes) se calcula UNA vez al importar el módulo: un solo PBKDF2 por
    intento, exista o no el usuario (mismo costo y sin delatar cuentas por tiempo).
  · El bloqueo se revisa ANTES de hacer cualquier hash: quien ya está bloqueado no gasta CPU del servidor
    (un atacante no puede usar el login para agotar la CPU).
  · Los fallos se guardan en una deque por usuario y se descartan los vencidos desde la izquierda: O(1) amortizado
    en lugar de reconstruir una lista nueva en cada intento (lo que hacen las otras dos versiones).
  · Búsqueda del usuario en un diccionario: O(1) (con una lista sería O(n)).
Interfaz común a las 3 versiones: registrar(), login(), reiniciar().
"""
from __future__ import annotations

import time
from collections import deque

from api.auth import hash_contrasena, verificar_contrasena

MENSAJE_OK = "access granted"
MENSAJE_ERROR = "invalid credentials"
MENSAJE_BLOQUEO = "too many attempts"
MAX_FALLOS, VENTANA_S = 5, 15 * 60

_HASH_RELLENO = hash_contrasena("relleno-sin-usuario")  # una sola vez
_usuarios: dict[str, str] = {}
_fallos: dict[str, deque[float]] = {}


def reiniciar() -> None:
    _usuarios.clear()
    _fallos.clear()


def registrar(usuario: str, contrasena: str) -> None:
    _usuarios[usuario.strip().lower()] = hash_contrasena(contrasena)


def login(usuario: str, contrasena: str, ahora: float | None = None) -> str:
    usuario, ahora = usuario.strip().lower(), ahora if ahora is not None else time.time()
    fallos = _fallos.setdefault(usuario, deque())
    while fallos and ahora - fallos[0] >= VENTANA_S:
        fallos.popleft()
    if len(fallos) >= MAX_FALLOS:
        return MENSAJE_BLOQUEO          # sin hashear: no cuesta CPU
    guardado = _usuarios.get(usuario)
    ok = verificar_contrasena(contrasena, guardado or _HASH_RELLENO) and guardado is not None
    if ok:
        fallos.clear()
        return MENSAJE_OK
    fallos.append(ahora)
    return MENSAJE_ERROR
