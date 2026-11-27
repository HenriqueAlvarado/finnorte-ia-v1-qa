"""A3 · paso 5: pruebas de las 3 versiones del login() (más las 3 mínimas del texto oficial
corren una vez por versión) y de la matriz problema→versión de analisis_login.md.
"""
import time

import pytest

from a3 import login_eficiencia, login_mantenible, login_original, login_seguridad


# ---------- las 3 mínimas del texto oficial, repetidas en cada versión mejorada ----------
@pytest.mark.parametrize("mod", [login_seguridad, login_eficiencia])
def test_login_exitoso(mod):
    assert mod.login("admin", "1234") == "access granted"


def test_login_exitoso_mantenible():
    assert login_mantenible.login("admin", "1234").ok


@pytest.mark.parametrize("mod", [login_seguridad, login_eficiencia])
def test_contrasena_incorrecta(mod):
    assert mod.login("admin", "mala") != "access granted"


def test_contrasena_incorrecta_mantenible():
    assert not login_mantenible.login("admin", "mala").ok


@pytest.mark.parametrize("mod", [login_seguridad, login_eficiencia])
def test_usuario_inexistente(mod):
    assert mod.login("nadie", "1234") != "access granted"


def test_usuario_inexistente_mantenible():
    assert not login_mantenible.login("nadie", "1234").ok


# ---------- P5: ya no hay espacio final en el mensaje de usuario inexistente ----------
def test_original_tiene_el_bug_del_espacio():
    """Documenta el bug P5 en el original (para que la prueba de P5 abajo tenga sentido)."""
    assert login_original.login("nadie", "x") == "user not found "  # bug real, a propósito


@pytest.mark.parametrize("mod,resultado", [
    (login_seguridad, "Usuario o contraseña incorrectos"),
    (login_eficiencia, "user not found"),
])
def test_p5_sin_espacio_final(mod, resultado):
    assert mod.login("nadie", "x") == resultado
    assert not resultado.endswith(" ")


def test_p5_sin_espacio_final_mantenible():
    assert login_mantenible.login("nadie", "x").mensaje == "Usuario o contraseña incorrectos"


# ---------- P1: mismo mensaje para usuario inexistente y contraseña incorrecta ----------
def test_p1_mismo_mensaje_seguridad():
    a = login_seguridad.login("admin", "mala")
    b = login_seguridad.login("nadie", "1234")
    assert a == b == login_seguridad.MENSAJE_CREDENCIALES


def test_p1_mismo_mensaje_mantenible():
    a = login_mantenible.login("admin", "mala")
    b = login_mantenible.login("nadie", "1234")
    assert a.mensaje == b.mensaje == login_mantenible.MENSAJE_CREDENCIALES


def test_p1_eficiencia_no_lo_corrige_a_proposito():
    """login_eficiencia.py deja P1 sin corregir (documentado en su docstring)."""
    assert login_eficiencia.login("admin", "mala") == "wrong password"
    assert login_eficiencia.login("nadie", "1234") == "user not found"


# ---------- P2/P3: login_seguridad.py no guarda ni compara en texto plano ----------
def test_p2_p3_seguridad_no_expone_la_contrasena_en_el_modulo():
    import inspect
    fuente = inspect.getsource(login_seguridad)
    assert '"1234"' not in fuente.split("_hash(")[0]  # la contraseña real solo aparece al hashearse, no suelta
    assert "pbkdf2_hmac" in fuente and "compare_digest" in fuente


# ---------- P4: el trade-off seguridad vs. velocidad es medible, no solo narrado ----------
def test_seguridad_tarda_mas_que_eficiencia_por_el_costo_de_pbkdf2():
    t0 = time.perf_counter()
    for _ in range(20):
        login_seguridad.login("admin", "1234")
    t_seguridad = time.perf_counter() - t0

    t0 = time.perf_counter()
    for _ in range(20):
        login_eficiencia.login("admin", "1234")
    t_eficiencia = time.perf_counter() - t0

    assert t_seguridad > t_eficiencia  # PBKDF2 (200k iteraciones) es deliberadamente más caro


# ---------- P7: escalabilidad / extensibilidad ----------
def test_p7_eficiencia_escala_a_muchos_usuarios_sin_tocar_la_funcion():
    login_eficiencia._USUARIOS.update({f"user{i}": f"clave{i}" for i in range(1000)})
    assert login_eficiencia.login("user999", "clave999") == "access granted"
    assert login_eficiencia.login("user999", "mala") == "wrong password"


def test_p7_mantenible_registrar_usuario_nuevo_sin_tocar_login():
    almacen = login_mantenible.AlmacenUsuarios(credenciales={})
    almacen.registrar_usuario("nuevo", "clave-nueva")
    assert login_mantenible.login("nuevo", "clave-nueva", almacen).ok
    assert not login_mantenible.login("otro", "x", almacen).ok


# ---------- P6: contrato de salida tipado en la versión mantenible ----------
def test_p6_mantenible_regresa_un_resultado_tipado_no_una_cadena_suelta():
    r = login_mantenible.login("admin", "1234")
    assert isinstance(r, login_mantenible.ResultadoLogin)
    assert hasattr(r, "ok") and hasattr(r, "mensaje")
