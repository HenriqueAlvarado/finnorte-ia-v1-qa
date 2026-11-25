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
    """Genera un hash PBKDF2-HMAC-SHA256 con sal aleatoria."""
    if not isinstance(contrasena, str):
        raise TypeError("La contraseña debe ser texto")

    if sal is None:
        sal = os.urandom(16)

    if not isinstance(sal, bytes) or len(sal) != 16:
        raise ValueError("La sal debe contener exactamente 16 bytes")

    derivado = hashlib.pbkdf2_hmac(
        "sha256",
        contrasena.encode("utf-8"),
        sal,
        ITERACIONES
    )

    return f"pbkdf2${ITERACIONES}${_b64(sal)}${_b64(derivado)}"


def verificar_contrasena(contrasena: str, guardado: str) -> bool:
    """Verifica un hash PBKDF2 utilizando comparación en tiempo constante."""
    try:
        algoritmo, iteraciones_txt, sal_txt, hash_txt = guardado.split("$")

        if algoritmo != "pbkdf2":
            return False

        iteraciones = int(iteraciones_txt)

        # Solo se aceptan los parámetros definidos por el laboratorio.
        if iteraciones != ITERACIONES:
            return False

        sal = _unb64(sal_txt)
        hash_guardado = _unb64(hash_txt)

        if len(sal) != 16 or len(hash_guardado) != 32:
            return False

        calculado = hashlib.pbkdf2_hmac(
            "sha256",
            contrasena.encode("utf-8"),
            sal,
            iteraciones
        )

        return hmac.compare_digest(calculado, hash_guardado)

    except (ValueError, TypeError, AttributeError):
        return False


def emitir_token(usuario: str, ahora: float | None = None) -> str:
    """Emite un token firmado HMAC-SHA256 con expiración limitada."""
    if not isinstance(usuario, str) or not usuario.strip():
        raise ValueError("El usuario no puede estar vacío")

    if not 1 <= VIGENCIA_S <= 900:
        raise ValueError("La vigencia del token debe ser de 1 a 900 segundos")

    instante = time.time() if ahora is None else float(ahora)

    payload = {
        "sub": usuario,
        "iat": int(instante),
        "exp": int(instante + VIGENCIA_S)
    }

    contenido = _b64(
        json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True
        ).encode("utf-8")
    )

    firma = _b64(
        hmac.new(
            _secreto(),
            contenido.encode("ascii"),
            hashlib.sha256
        ).digest()
    )

    return f"{contenido}.{firma}"


def validar_token(token: str, ahora: float | None = None) -> str:
    """Valida formato, firma y expiración; devuelve el usuario autenticado."""
    try:
        if not isinstance(token, str):
            raise ValueError("Formato inválido")

        partes = token.split(".")

        if len(partes) != 2 or not all(partes):
            raise ValueError("Formato inválido")

        contenido, firma = partes

        patron = r"^[A-Za-z0-9_-]+$"

        if not re.fullmatch(patron, contenido):
            raise ValueError("Payload inválido")

        if not re.fullmatch(patron, firma):
            raise ValueError("Firma inválida")

        firma_esperada = _b64(
            hmac.new(
                _secreto(),
                contenido.encode("ascii"),
                hashlib.sha256
            ).digest()
        )

        if not hmac.compare_digest(firma_esperada, firma):
            raise ValueError("Firma incorrecta")

        datos = json.loads(_unb64(contenido).decode("utf-8"))

        if not isinstance(datos, dict):
            raise ValueError("Payload inválido")

        usuario = datos.get("sub")
        emision = datos.get("iat")
        expiracion = datos.get("exp")

        if not isinstance(usuario, str) or not usuario.strip():
            raise ValueError("Usuario inválido")

        if type(emision) not in (int, float):
            raise ValueError("Fecha de emisión inválida")

        if type(expiracion) not in (int, float):
            raise ValueError("Expiración inválida")

        if expiracion <= emision:
            raise ValueError("Intervalo de vigencia inválido")

        instante = time.time() if ahora is None else float(ahora)

        if expiracion <= instante:
            raise ErrorAuth(401, "Token expirado")

        return usuario

    except ErrorAuth:
        raise
    except (ValueError, TypeError, UnicodeError, KeyError, OverflowError):
        raise ErrorAuth(401, "Token inválido")
    except Exception:
        raise ErrorAuth(401, "Token inválido")


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
        """Autentica al usuario, registra el intento y aplica bloqueo temporal."""
        email = email.strip().lower() if isinstance(email, str) else ""
        instante = time.time() if ahora is None else float(ahora)

        # 1. Contar fallos dentro de la ventana de 15 minutos.
        desde = instante - VENTANA_FALLOS_S

        fila_fallos = self.db.execute(
            "SELECT COUNT(*) FROM intentos "
            "WHERE email = ? AND ts >= ? AND ok = 0",
            (email, desde)
        ).fetchone()

        fallos = fila_fallos[0]

        # 2. Bloquear antes de permitir otro intento.
        if fallos >= MAX_FALLOS:
            raise ErrorAuth(429, "Demasiados intentos. Intenta más tarde.")

        # 3. Buscar al usuario y verificar la contraseña.
        usuario = self.db.execute(
            "SELECT hash FROM usuarios WHERE email = ?",
            (email,)
        ).fetchone()

        valido = (
            usuario is not None
            and isinstance(contrasena, str)
            and verificar_contrasena(contrasena, usuario[0])
        )

        # 4. Registrar el intento. Nunca almacenar la contraseña.
        with self.db:
            self.db.execute(
                "INSERT INTO intentos (email, ts, ok) VALUES (?, ?, ?)",
                (email, instante, int(valido))
            )

        # 5. Utilizar el mismo mensaje ante ambas causas de rechazo.
        if not valido:
            raise ErrorAuth(401, MENSAJE_CREDENCIALES)

        # 6. Emitir token solamente después de autenticar correctamente.
        return emitir_token(email, ahora=instante)
