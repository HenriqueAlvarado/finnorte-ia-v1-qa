"""Versión enfocada en seguridad.

Cambios:
- Usa hashes PBKDF2 existentes, nunca contraseñas en texto plano.
- Utiliza un hash ficticio cuando el usuario no existe para reducir
  diferencias de tiempo entre ambos escenarios.
- Devuelve el mismo mensaje para cualquier credencial incorrecta.
- Limita el tipo y longitud de las entradas.
"""
from collections.abc import Mapping

from api.auth import hash_contrasena, verificar_contrasena

MENSAJE_ERROR = "Correo o contraseña incorrectos"
_DUMMY_HASH = hash_contrasena("clave-dummy-no-valida-2026")


def login(user: str, password: str, usuarios: Mapping[str, str]) -> str:
    clave = user.strip().lower() if isinstance(user, str) else ""
    contrasena = password if isinstance(password, str) else ""

    if len(contrasena) > 128:
        contrasena = ""

    guardado = usuarios.get(clave)
    hash_objetivo = guardado if isinstance(guardado, str) else _DUMMY_HASH

    try:
        valido = verificar_contrasena(contrasena, hash_objetivo)
    except (ValueError, TypeError):
        valido = verificar_contrasena(contrasena, _DUMMY_HASH)

    if isinstance(guardado, str) and valido:
        return "access granted"

    return MENSAJE_ERROR
