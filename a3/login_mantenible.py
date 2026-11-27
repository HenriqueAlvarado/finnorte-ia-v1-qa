"""Versión enfocada en mantenibilidad.

Cambios:
- Separa normalización, búsqueda, verificación y respuesta.
- Usa anotaciones de tipos.
- Centraliza el mensaje de error.
- Facilita probar cada parte de forma independiente.
"""
from collections.abc import Mapping

from api.auth import hash_contrasena, verificar_contrasena

MENSAJE_ERROR = "Correo o contraseña incorrectos"
_DUMMY_HASH = hash_contrasena("clave-dummy-no-valida-2026")


def _normalizar_usuario(user: str) -> str:
    return user.strip().lower() if isinstance(user, str) else ""


def _obtener_hash(usuario: str, usuarios: Mapping[str, str]) -> str:
    guardado = usuarios.get(usuario)
    return guardado if isinstance(guardado, str) else _DUMMY_HASH


def _credenciales_validas(
    password: str,
    hash_guardado: str,
    usuario_existe: bool
) -> bool:
    try:
        coincide = verificar_contrasena(password, hash_guardado)
        return usuario_existe and coincide
    except (ValueError, TypeError):
        return False


def login(user: str, password: str, usuarios: Mapping[str, str]) -> str:
    usuario = _normalizar_usuario(user)
    contrasena = password if isinstance(password, str) else ""

    if len(contrasena) > 128:
        return MENSAJE_ERROR

    guardado = usuarios.get(usuario)
    hash_guardado = _obtener_hash(usuario, usuarios)

    if _credenciales_validas(
        contrasena,
        hash_guardado,
        isinstance(guardado, str)
    ):
        return "access granted"

    return MENSAJE_ERROR
