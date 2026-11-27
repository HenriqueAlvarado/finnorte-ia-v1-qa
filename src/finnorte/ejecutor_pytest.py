"""Ejecutor de pytest en un contenedor Docker restringido."""
from __future__ import annotations

import re
import subprocess
import threading
import time
import uuid
from pathlib import Path

from . import trazas
from .config import RAIZ

DIRECTORIO = RAIZ / "sandbox" / "generated"
IMAGEN = "finnorte-pytest-sandbox:1.0"
TIMEOUT_S = 30
MAX_ARCHIVO = 256 * 1024
MAX_SALIDA = 64 * 1024


def _contar(patron: str, salida: str) -> int:
    coincidencia = re.search(patron, salida)
    return int(coincidencia.group(1)) if coincidencia else 0


def _validar_archivo(archivo: str) -> Path:
    if not isinstance(archivo, str) or not archivo:
        raise ValueError("Debes indicar un archivo de pruebas")

    if Path(archivo).name != archivo or archivo in {".", ".."}:
        raise ValueError("Solo se admite el nombre del archivo, sin rutas")

    if not archivo.endswith(".py"):
        raise ValueError("El archivo debe tener extensión .py")

    DIRECTORIO.mkdir(parents=True, exist_ok=True)
    raiz = DIRECTORIO.resolve(strict=True)
    ruta = DIRECTORIO / archivo

    if ruta.is_symlink() or not ruta.is_file():
        raise ValueError("El archivo no existe o no es un archivo regular")

    real = ruta.resolve(strict=True)

    if real.parent != raiz:
        raise ValueError("El archivo está fuera del directorio autorizado")

    if real.stat().st_size > MAX_ARCHIVO:
        raise ValueError("El archivo supera el tamaño máximo de 256 KB")

    return real


def ejecutar_pytest(archivo: str) -> dict:
    """Ejecuta únicamente un archivo autorizado dentro del sandbox Docker.

    No monta el repositorio, archivos .env, sockets ni volúmenes del host.
    """
    ruta = _validar_archivo(archivo)
    nombre = f"finnorte-pytest-{uuid.uuid4().hex[:12]}"

    comando = [
        "docker", "run",
        "--name", nombre,
        "--pull=never",
        "--network", "none",
        "--ipc", "none",
        "--read-only",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges:true",
        "--memory", "256m",
        "--memory-swap", "256m",
        "--cpus", "1",
        "--pids-limit", "64",
        "--user", "65534:65534",
        "--tmpfs", "/tmp:rw,nosuid,nodev,noexec,size=32m",
        "--mount",
        f"type=bind,src={ruta},dst=/workspace/test_target.py,readonly",
        "--workdir", "/workspace",
        "--env", "HOME=/tmp",
        "--env", "PYTHONDONTWRITEBYTECODE=1",
        "--env", "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
        "--entrypoint", "python",
        IMAGEN,
        "-I", "-m", "pytest",
        "-p", "no:cacheprovider",
        "-q",
        "/workspace/test_target.py",
    ]

    inicio = time.monotonic()
    partes: list[bytes] = []
    total_capturado = 0

    try:
        proceso = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
        )

        def leer_salida():
            nonlocal total_capturado
            while True:
                bloque = proceso.stdout.read(8192)
                if not bloque:
                    break
                restante = MAX_SALIDA - total_capturado
                if restante > 0:
                    partes.append(bloque[:restante])
                    total_capturado += min(len(bloque), restante)

        lector = threading.Thread(target=leer_salida, daemon=True)
        lector.start()

        expirado = False

        try:
            codigo = proceso.wait(timeout=TIMEOUT_S)
        except subprocess.TimeoutExpired:
            expirado = True
            try:
                subprocess.run(
                    ["docker", "kill", nombre],
                    capture_output=True,
                    timeout=4,
                    check=False,
                )
            except (subprocess.TimeoutExpired, OSError):
                pass

            try:
                codigo = proceso.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proceso.kill()
                codigo = proceso.wait()

        lector.join(timeout=3)
        salida = b"".join(partes).decode("utf-8", errors="replace")

    except OSError as exc:
        raise RuntimeError(
            f"No fue posible iniciar Docker: {type(exc).__name__}"
        ) from exc

    finally:
        try:
            subprocess.run(
                ["docker", "rm", "--force", nombre],
                capture_output=True,
                timeout=4,
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            pass

    duracion = round((time.monotonic() - inicio) * 1000, 1)

    aprobadas = _contar(r"(\d+)\s+passed", salida)
    fallidas = _contar(r"(\d+)\s+failed", salida)
    omitidas = _contar(r"(\d+)\s+skipped", salida)
    errores = _contar(r"(\d+)\s+error", salida)

    correcto = (
        not expirado
        and codigo == 0
        and aprobadas > 0
        and fallidas == 0
        and omitidas == 0
        and errores == 0
    )

    resultado = {
        "archivo": ruta.name,
        "ok": correcto,
        "timeout": expirado,
        "codigo_salida": codigo,
        "aprobadas": aprobadas,
        "fallidas": fallidas,
        "omitidas": omitidas,
        "errores": errores,
        "duracion_ms": duracion,
        "salida_truncada": len(salida.encode("utf-8")) >= MAX_SALIDA,
        "resumen": salida[-4000:],
    }

    trazas.registrar(
        "ejecutor_pytest",
        archivo=ruta.name,
        ok=correcto,
        timeout=expirado,
        aprobadas=aprobadas,
        fallidas=fallidas,
        omitidas=omitidas,
        errores=errores,
        duracion_ms=duracion,
    )

    return resultado
