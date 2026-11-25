"""Autenticación del servicio (Laboratorio A3+A4 · caso guía).

Registro, login y token, sin librerías externas. Requisitos mínimos de la A3:
  1. Contraseñas con hash y sal (PBKDF2-HMAC-SHA256), nunca texto plano ni MD5.
  2. Token con expiración de 15 minutos o menos.
  3. El MISMO mensaje para usuario inexistente y contraseña incorrecta.
  4. Comparación en tiempo constante (hmac.compare_digest).
  5. Bloqueo temporal tras intentos fallidos.
  6. La bitácora de intentos NO guarda la contraseña.

Las piezas marcadas TODO(LAB) las completamos juntos en el laboratorio con ayuda del asistente de IA.
El secreto para firmar tokens se lee de TOKEN_SECRET en .env (nunca en el código).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
from dataclasses import dataclass

ITERACIONES = 200_000
VIGENCIA_S = int(os.getenv("TOKEN_VIGENCIA_S", str(15 * 60)))
MAX_FALLOS, VENTANA_FALLOS_S = 5, 15 * 60
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MENSAJE_CREDENCIALES = "Correo o contraseña incorrectos"


def _secreto() -> bytes:
    s = os.getenv("TOKEN_SECRET", "")
    if len(s) < 32:
        raise RuntimeError("Define TOKEN_SECRET en .env con al menos 32 caracteres (python -c \"import secrets;print(secrets.token_hex(32))\")")
    return s.encode()


class ErrorAuth(Exception):
    def __init__(self, status: int, mensaje: str):
        super().__init__(mensaje)
        self.status = status


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def hash_contrasena(contrasena: str, sal: bytes | None = None) -> str:
    """Devuelve 'pbkdf2$<iteraciones>$<sal>$<hash>' (todo en base64url)."""
    # TODO(LAB): usa hashlib.pbkdf2_hmac("sha256", ...) con sal de os.urandom(16) e ITERACIONES
    sal = sal if sal is not None else os.urandom(16)
    derivado = hashlib.pbkdf2_hmac("sha256", contrasena.encode(), sal, ITERACIONES)
    return f"pbkdf2${ITERACIONES}${_b64(sal)}${_b64(derivado)}"


def verificar_contrasena(contrasena: str, guardado: str) -> bool:
    """Recalcula el hash con la misma sal y compara en TIEMPO CONSTANTE."""
    # TODO(LAB): separa el texto guardado por "$", recalcula con la misma sal y compara con hmac.compare_digest
    try:
        _, iteraciones_str, sal_b64, hash_b64 = guardado.split("$")
    except ValueError:
        return False
    iteraciones = int(iteraciones_str)
    sal = _unb64(sal_b64)
    derivado = hashlib.pbkdf2_hmac("sha256", contrasena.encode(), sal, iteraciones)
    return hmac.compare_digest(_b64(derivado), hash_b64)


def emitir_token(usuario: str, ahora: float | None = None) -> str:
    """Token 'payload.firma': payload = {sub, iat, exp} en base64url; firma = HMAC-SHA256 con TOKEN_SECRET."""
    # TODO(LAB): payload = _b64(json {sub, iat, exp}); firma = _b64(hmac.new(_secreto(), payload, sha256)); devuelve "payload.firma"
    ahora = ahora or time.time()
    payload = {"sub": usuario, "iat": ahora, "exp": ahora + VIGENCIA_S}
    payload_b64 = _b64(json.dumps(payload).encode())
    firma = _b64(hmac.new(_secreto(), payload_b64.encode(), hashlib.sha256).digest())
    return f"{payload_b64}.{firma}"


def validar_token(token: str, ahora: float | None = None) -> str:
    """Devuelve el usuario si el token es válido; si no, ErrorAuth(401). Revisa formato, firma y expiración."""
    # TODO(LAB): separa payload y firma, recalcula la firma, compara en tiempo constante y revisa exp; si algo falla: ErrorAuth(401, ...)
    ahora = ahora or time.time()
    try:
        payload_b64, firma = token.split(".")
    except ValueError:
        raise ErrorAuth(401, "Token con formato invalido")
    firma_esperada = _b64(hmac.new(_secreto(), payload_b64.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(firma, firma_esperada):
        raise ErrorAuth(401, "Token con firma invalida")
    try:
        payload = json.loads(_unb64(payload_b64))
    except (ValueError, UnicodeDecodeError):
        raise ErrorAuth(401, "Token con formato invalido")
    if ahora > payload.get("exp", 0):
        raise ErrorAuth(401, "Token expirado")
    return payload["sub"]


@dataclass
class Autenticador:
    ruta_db: str = ":memory:"

    def __post_init__(self):
        self.db = sqlite3.connect(self.ruta_db, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS usuarios (email TEXT PRIMARY KEY, hash TEXT NOT NULL)")
        # Bitácora de intentos: correo, hora y resultado. NUNCA la contraseña.
        self.db.execute("CREATE TABLE IF NOT EXISTS intentos (email TEXT, ts REAL, ok INTEGER)")

    def registrar(self, email: str, contrasena: str) -> None:
        email = email.strip().lower()
        if not EMAIL.match(email):
            raise ErrorAuth(422, "Correo inválido")
        if len(contrasena) < 8:
            raise ErrorAuth(422, "La contraseña debe tener al menos 8 caracteres")
        try:
            with self.db:
                self.db.execute("INSERT INTO usuarios VALUES (?, ?)", (email, hash_contrasena(contrasena)))
        except sqlite3.IntegrityError:
            raise ErrorAuth(409, "El correo ya está registrado")

    def login(self, email: str, contrasena: str, ahora: float | None = None) -> str:
        email, ahora = email.strip().lower(), ahora or time.time()
        # TODO(LAB): cuenta fallos recientes (bloqueo 429), busca el hash, verifica, registra el intento SIN contraseña y usa MENSAJE_CREDENCIALES
        desde = ahora - VENTANA_FALLOS_S
        fallos = self.db.execute(
            "SELECT COUNT(*) FROM intentos WHERE email = ? AND ok = 0 AND ts > ?",
            (email, desde),
        ).fetchone()[0]
        if fallos >= MAX_FALLOS:
            raise ErrorAuth(429, "Demasiados intentos fallidos. Intenta de nuevo mas tarde.")
        fila = self.db.execute(
            "SELECT hash FROM usuarios WHERE email = ?", (email,)
        ).fetchone()
        ok = fila is not None and verificar_contrasena(contrasena, fila[0])
        with self.db:
            self.db.execute(
                "INSERT INTO intentos VALUES (?, ?, ?)", (email, ahora, 1 if ok else 0)
            )
        if not ok:
            raise ErrorAuth(401, MENSAJE_CREDENCIALES)
        return emitir_token(email, ahora)
