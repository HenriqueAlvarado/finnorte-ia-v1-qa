"""A3 · Versión SEGURIDAD del login().

Qué cambia frente al oficial y por qué:
  · Ya no hay credenciales en el código: los usuarios se registran y se guardan con HASH Y SAL (PBKDF2, api/auth.py).
  · Comparación en tiempo constante (hmac.compare_digest dentro de verificar_contrasena), no con ==.
  · EL MISMO mensaje para «usuario no existe» y «contraseña incorrecta» (SEC): no se enumeran cuentas.
  · Si el usuario no existe se verifica contra un hash de relleno PRECALCULADO, para que tarde igual (un solo PBKDF2)
    y el tiempo de respuesta no delate la cuenta. (La primera versión lo recalculaba en cada intento: un usuario
    inexistente tardaba 152 ms contra 75 ms de uno real, lo que permitía enumerar cuentas midiendo el tiempo.)
  · Bloqueo tras 5 fallos seguidos en 15 minutos.
  · No se guarda ni se imprime la contraseña (ing-02).
Interfaz común a las 3 versiones: registrar(), login(), reiniciar().
"""
from __future__ import annotations

import time

from api.auth import hash_contrasena, verificar_contrasena

MENSAJE_OK = "access granted"
MENSAJE_ERROR = "invalid credentials"
MENSAJE_BLOQUEO = "too many attempts"
MAX_FALLOS, VENTANA_S = 5, 15 * 60

_HASH_RELLENO = hash_contrasena("relleno-sin-usuario")   # una vez: así un usuario inexistente cuesta lo mismo que uno real
_usuarios: dict[str, str] = {}
_fallos: dict[str, list[float]] = {}


def reiniciar() -> None:
    _usuarios.clear()
    _fallos.clear()


def registrar(usuario: str, contrasena: str) -> None:
    _usuarios[usuario.strip().lower()] = hash_contrasena(contrasena)


def login(usuario: str, contrasena: str, ahora: float | None = None) -> str:
    usuario, ahora = usuario.strip().lower(), ahora if ahora is not None else time.time()
    recientes = [t for t in _fallos.get(usuario, []) if ahora - t < VENTANA_S]
    if len(recientes) >= MAX_FALLOS:
        return MENSAJE_BLOQUEO
    guardado = _usuarios.get(usuario)
    ok = verificar_contrasena(contrasena, guardado if guardado else _HASH_RELLENO)
    if ok and guardado:
        _fallos.pop(usuario, None)
        return MENSAJE_OK
    _fallos[usuario] = recientes + [ahora]
    return MENSAJE_ERROR
