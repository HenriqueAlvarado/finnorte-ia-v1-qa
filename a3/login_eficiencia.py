"""Versión enfocada en eficiencia.

Cambios:
- Normaliza el identificador una sola vez.
- Realiza una sola consulta al diccionario.
- Ejecuta una sola verificación PBKDF2 por solicitud.
- Conserva la comparación segura y el mensaje uniforme.
"""
from collections.abc import Mapping

from api.auth import hash_contrasena, verificar_contrasena

MENSAJE_ERROR = "Correo o contraseña incorrectos"
_DUMMY_HASH = hash_contrasena("clave-dummy-no-valida-2026")


def login(user: str, password: str, usuarios: Mapping[str, str]) -> str:
    if not isinstance(user, str) or not isinstance(password, str):
        return MENSAJE_ERROR

    if not user or len(password) > 128:
        return MENSAJE_ERROR

    clave = user.strip().lower()
    guardado = usuarios.get(clave)

    hash_objetivo = guardado if isinstance(guardado, str) else _DUMMY_HASH

    try:
        valido = verificar_contrasena(password, hash_objetivo)
    except (ValueError, TypeError):
        valido = False

    return (
        "access granted"
        if isinstance(guardado, str) and valido
        else MENSAJE_ERROR
    )
