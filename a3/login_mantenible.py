"""Versión MANTENIBLE de login() (A3 · paso 4).

Qué cambié y por qué (evidencia en analisis_login.md, filas P1, P5, P6, P7):
  - P6 El original regresa cadenas sueltas ("access granted", "wrong password",
    "user not found "): quien lo llama tiene que acordarse de esos literales exactos (y el
    espacio final de P5 los rompe en silencio). Aquí login() regresa un ResultadoLogin
    (dataclass) con un booleano `ok` y un `mensaje` para mostrar — el código que llama revisa
    `.ok`, no compara cadenas mágicas.
  - P7 Los usuarios ya no están escritos a mano dentro de la función: viven en un
    AlmacenUsuarios inyectable (un diccionario por defecto, pero se puede pasar otro en
    pruebas o cambiar por una base de datos real sin tocar login()). Agregar un usuario es
    una llamada a `registrar_usuario(...)`, no editar un if.
  - P1 Mismo mensaje para usuario inexistente y contraseña incorrecta (se reutiliza la
    MISMA constante en los dos casos, así no se puede que un cambio futuro los desalinee).
  - Tipos y docstrings explícitos en cada función: cualquiera que lea el módulo entiende el
    contrato sin tener que ejecutarlo.

No es la versión más rápida (login_eficiencia.py) ni la más endurecida en criptografía
(login_seguridad.py a propósito): el objetivo aquí es que agregar un requisito nuevo (otro
campo, otra regla de negocio) cueste cambiar una función, no reescribir todo el módulo.
"""
from __future__ import annotations

from dataclasses import dataclass, field

MENSAJE_CREDENCIALES = "Usuario o contraseña incorrectos"
MENSAJE_EXITO = "access granted"


@dataclass(frozen=True)
class ResultadoLogin:
    """Lo que login() regresa: un booleano para decidir, un mensaje para mostrar."""
    ok: bool
    mensaje: str


@dataclass
class AlmacenUsuarios:
    """Quien use login() puede pasar su propio almacén (otra fuente, o uno vacío en pruebas)."""
    credenciales: dict[str, str] = field(default_factory=lambda: {"admin": "1234"})

    def contrasena_de(self, usuario: str) -> str | None:
        return self.credenciales.get(usuario)

    def registrar_usuario(self, usuario: str, contrasena: str) -> None:
        self.credenciales[usuario] = contrasena


_ALMACEN_POR_DEFECTO = AlmacenUsuarios()


def login(user: str, password: str, almacen: AlmacenUsuarios = _ALMACEN_POR_DEFECTO) -> ResultadoLogin:
    """Valida user/password contra `almacen`. Mismo mensaje para cualquier credencial inválida."""
    esperada = almacen.contrasena_de(user)
    if esperada is not None and password == esperada:
        return ResultadoLogin(True, MENSAJE_EXITO)
    return ResultadoLogin(False, MENSAJE_CREDENCIALES)
