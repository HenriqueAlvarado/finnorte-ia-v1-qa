"""A3 · Versión MANTENIBLE del login().

Misma seguridad, organizada para que se entienda y se cambie sin romper nada:
  · Una clase con responsabilidades pequeñas (_bloqueado, _verificar, _anotar_fallo) en lugar de ifs anidados.
  · Resultados con nombre (Enum) en lugar de textos sueltos: el código decide con Resultado, y los mensajes
    para el usuario viven en un solo diccionario (cambiar un texto no toca la lógica).
  · Política (intentos, ventana) en un dataclass inmutable: se cambia en un solo lugar y se prueba con otra política.
  · Reloj inyectable (parámetro `ahora`): las pruebas de bloqueo no necesitan esperar 15 minutos.
  · Anotaciones de tipo y docstrings.
Interfaz común a las 3 versiones: registrar(), login(), reiniciar().
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

from api.auth import hash_contrasena, verificar_contrasena


class Resultado(Enum):
    ACCESO = "acceso"
    CREDENCIALES_INVALIDAS = "credenciales_invalidas"
    BLOQUEADO = "bloqueado"


_HASH_RELLENO = hash_contrasena("relleno-sin-usuario")   # una vez: un usuario inexistente cuesta lo mismo que uno real

MENSAJES = {
    Resultado.ACCESO: "access granted",
    Resultado.CREDENCIALES_INVALIDAS: "invalid credentials",  # el mismo para usuario inexistente y contraseña mala
    Resultado.BLOQUEADO: "too many attempts",
}


@dataclass(frozen=True)
class Politica:
    max_fallos: int = 5
    ventana_s: int = 15 * 60


@dataclass
class Autenticador:
    politica: Politica = field(default_factory=Politica)
    _usuarios: dict[str, str] = field(default_factory=dict)
    _fallos: dict[str, list[float]] = field(default_factory=dict)

    @staticmethod
    def _normalizar(usuario: str) -> str:
        return usuario.strip().lower()

    def registrar(self, usuario: str, contrasena: str) -> None:
        self._usuarios[self._normalizar(usuario)] = hash_contrasena(contrasena)

    def _fallos_recientes(self, usuario: str, ahora: float) -> list[float]:
        return [t for t in self._fallos.get(usuario, []) if ahora - t < self.politica.ventana_s]

    def _bloqueado(self, usuario: str, ahora: float) -> bool:
        return len(self._fallos_recientes(usuario, ahora)) >= self.politica.max_fallos

    def _verificar(self, usuario: str, contrasena: str) -> bool:
        guardado = self._usuarios.get(usuario)
        coincide = verificar_contrasena(contrasena, guardado or _HASH_RELLENO)
        return coincide and guardado is not None

    def _anotar_fallo(self, usuario: str, ahora: float) -> None:
        self._fallos[usuario] = self._fallos_recientes(usuario, ahora) + [ahora]

    def intentar(self, usuario: str, contrasena: str, ahora: float | None = None) -> Resultado:
        usuario, ahora = self._normalizar(usuario), ahora if ahora is not None else time.time()
        if self._bloqueado(usuario, ahora):
            return Resultado.BLOQUEADO
        if self._verificar(usuario, contrasena):
            self._fallos.pop(usuario, None)
            return Resultado.ACCESO
        self._anotar_fallo(usuario, ahora)
        return Resultado.CREDENCIALES_INVALIDAS


_defecto = Autenticador()


def reiniciar() -> None:
    global _defecto
    _defecto = Autenticador()


def registrar(usuario: str, contrasena: str) -> None:
    _defecto.registrar(usuario, contrasena)


def login(usuario: str, contrasena: str, ahora: float | None = None) -> str:
    return MENSAJES[_defecto.intentar(usuario, contrasena, ahora)]
