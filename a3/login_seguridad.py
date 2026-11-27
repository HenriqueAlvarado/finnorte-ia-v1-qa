"""Versión SEGURIDAD de login() (A3 · paso 4).

Qué cambié y por qué (evidencia en analisis_login.md, filas P1, P2, P3, P5):
  - P1 Mismo mensaje para usuario inexistente y contraseña incorrecta: ya no se puede
    enumerar cuentas probando correos/usuarios al azar.
  - P2 La contraseña nunca se compara ni se guarda en texto plano: se compara contra un
    hash PBKDF2-HMAC-SHA256 con sal (200 000 iteraciones, igual que api/auth.py).
  - P3 Comparación en TIEMPO CONSTANTE (hmac.compare_digest) y trabajo constante también
    cuando el usuario no existe (se usa un hash "señuelo" de 32 bytes): así el tiempo de
    respuesta no delata si el usuario existe ni cuántos caracteres de la contraseña acertaste.
  - P5 Ya no regresa "user not found " con espacio final (bug menor pero real: rompe
    cualquier comparación exacta aguas abajo).

Lo que NO ataca a propósito (queda para login_eficiencia.py y login_mantenible.py, y se
discute en comparacion.md): el almacén de usuarios sigue siendo un dict fijo en memoria, no
hay bloqueo por intentos (eso ya vive en api/auth.py:Autenticador.login) y PBKDF2 es más lento
que una comparación de cadenas — aquí la prioridad es seguridad, no velocidad.
"""
from __future__ import annotations

import hashlib
import hmac
import os

ITERACIONES = 200_000
MENSAJE_CREDENCIALES = "Usuario o contraseña incorrectos"

# Sal fija SOLO para que este ejemplo sea reproducible en las pruebas; en un sistema real
# cada usuario tiene su propia sal aleatoria guardada junto al hash (ver api/auth.py).
_SAL_DEMO = b"sal-fija-para-el-ejemplo-de-a3!!"


def _hash(password: str, sal: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), sal, ITERACIONES)


# "Base de datos" de usuarios de este ejemplo: email/usuario -> hash de su contraseña.
_USUARIOS: dict[str, bytes] = {"admin": _hash("1234", _SAL_DEMO)}

# Hash señuelo: mismo tamaño (32 bytes) que un hash real, para que verificar un usuario que
# NO existe cueste el mismo trabajo (una PBKDF2 + una comparación) que uno que sí existe.
_HASH_SENUELO = os.urandom(32)


def login(user: str, password: str) -> str:
    """Devuelve "access granted" o el MISMO mensaje de error para cualquier otra causa."""
    hash_guardado = _USUARIOS.get(user, _HASH_SENUELO)
    calculado = _hash(password, _SAL_DEMO)
    coincide = hmac.compare_digest(calculado, hash_guardado) and user in _USUARIOS
    return "access granted" if coincide else MENSAJE_CREDENCIALES
