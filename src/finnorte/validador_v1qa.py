"""A4 · paso 4: validador de lógica tradicional para v1-qa.

Corre en CADA respuesta de `variante.sistema()` — se muestra en la interfaz
(app/app_variante.py) junto con la respuesta, no solo al final. Comprueba (tabla de
variantes, columna v1-qa):

  1. Para el requisito base de registro, los casos generados cubren los 4 escenarios
     obligatorios: registro exitoso, correo duplicado, contraseña de menos de 8
     caracteres y mensaje de confirmación.
  2. El pytest generado compila (`ast.parse`) — de forma independiente de si el flujo ya
     llegó a la etapa "pytest": el validador no confía en que el flujo haya ido bien, lo
     revisa de nuevo con su propia regla de negocio.
  3. La respuesta no trae información que no venga de la entrada o del corpus (regla
     general de la A4: "sin información externa"); se apoya en `errores_citas`, que ya
     calcula `variante.sistema()` al verificar cada cita contra lo recuperado.

No reemplaza la validación de `etapa_pytest.pytest_compila_y_cubre` (esa corre DENTRO del
flujo, caso por caso, y bloquea una etapa que no pasa); este validador corre AFUERA, sobre
la salida final que ve la persona, con la regla de negocio específica del requisito base.
"""
from __future__ import annotations

import ast
import re

ESCENARIOS_REGISTRO = {
    "registro_exitoso": re.compile(
        r"registro.{0,20}(exitos|correcto|complet|creado)|(exitos|correcto).{0,20}registro", re.I),
    "correo_duplicado": re.compile(
        r"correo.{0,15}duplicad|duplicad.{0,15}correo|correo.{0,15}ya.{0,15}registrad", re.I),
    "contrasena_corta": re.compile(
        r"contrase.a.{0,30}(menos de 8|corta|8 caracteres|< ?8)|al menos 8 caracteres", re.I),
    "mensaje_confirmacion": re.compile(
        r"mensaje de confirmaci|confirmaci[oó]n.{0,20}(correo|registro|cuenta)", re.I),
}


def _texto_casos(artefacto: dict) -> str:
    casos = (artefacto.get("casos") or {}).get("casos") or []
    piezas: list[str] = []
    for c in casos:
        if isinstance(c, dict):
            piezas += [str(c.get(k, "")) for k in ("titulo", "dado", "cuando", "entonces")]
    return "\n".join(piezas)


def _pytest_compila(artefacto: dict) -> tuple[bool, str]:
    codigo = (artefacto.get("pytest") or {}).get("codigo_pytest", "")
    if not codigo:
        return False, "no hay codigo_pytest en el artefacto"
    try:
        ast.parse(codigo)
        return True, "compila"
    except SyntaxError as e:
        return False, f"no compila: línea {e.lineno}: {e.msg}"


def validar_variante_v1qa(salida: dict) -> dict:
    """`salida` es el dict completo que regresa variante.sistema() (respuesta, fuentes,
    abstuvo, errores_citas, artefacto, ...). Puede llamarse sobre cualquier respuesta; si la
    entrada no era el requisito base de registro, los 4 escenarios simplemente no aparecen y
    el validador lo reporta como incompleto — no es un fallo del validador en sí."""
    artefacto = salida.get("artefacto") or {}
    texto = _texto_casos(artefacto)
    escenarios = {nombre: bool(patron.search(texto)) for nombre, patron in ESCENARIOS_REGISTRO.items()}
    pytest_ok, pytest_detalle = _pytest_compila(artefacto)
    sin_info_externa = not any("no recuperada" in e for e in (salida.get("errores_citas") or []))
    return {
        "escenarios_registro": escenarios,
        "cubre_los_4_escenarios": all(escenarios.values()),
        "pytest_compila": pytest_ok,
        "pytest_detalle": pytest_detalle,
        "sin_informacion_externa": sin_info_externa,
        "ok": all(escenarios.values()) and pytest_ok and sin_info_externa,
    }
