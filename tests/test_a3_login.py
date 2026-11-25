"""A3 · Pruebas de las 3 versiones del login() (seguridad, eficiencia, mantenible). Sin red.

Las 3 pruebas OFICIALES (login exitoso, contraseña incorrecta, usuario inexistente) corren contra cada versión.
Las PROPIAS cubren lo que el oficial nunca probó: mismo mensaje, bloqueo y expiración del bloqueo.
Además se demuestra, contra el login() oficial, por qué se reemplaza.
"""
import pytest

from a3 import login_eficiencia, login_mantenible, login_oficial, login_seguridad

VERSIONES = [login_seguridad, login_eficiencia, login_mantenible]
IDS = ["seguridad", "eficiencia", "mantenible"]
USUARIO, CLAVE = "admin", "Clave-Larga-123"


@pytest.fixture(params=VERSIONES, ids=IDS)
def v(request):
    mod = request.param
    mod.reiniciar()
    mod.registrar(USUARIO, CLAVE)
    return mod


# ── 3 oficiales ──
def test_oficial_login_exitoso(v):
    assert v.login(USUARIO, CLAVE) == "access granted"


def test_oficial_contrasena_incorrecta(v):
    assert v.login(USUARIO, "otra-clave-mala") == "invalid credentials"


def test_oficial_usuario_inexistente(v):
    assert v.login("nadie", CLAVE) == "invalid credentials"


# ── propias ──
def test_mismo_mensaje_usuario_inexistente_y_contrasena_mala(v):
    assert v.login("nadie", "x" * 10) == v.login(USUARIO, "x" * 10)


def test_bloqueo_tras_5_fallos_aun_con_la_clave_correcta(v):
    for _ in range(5):
        assert v.login(USUARIO, "mala-mala-mala") == "invalid credentials"
    assert v.login(USUARIO, CLAVE) == "too many attempts"


def test_el_bloqueo_expira_a_los_15_minutos(v):
    t0 = 1_000_000.0
    for _ in range(5):
        v.login(USUARIO, "mala-mala-mala", ahora=t0)
    assert v.login(USUARIO, CLAVE, ahora=t0 + 60) == "too many attempts"
    assert v.login(USUARIO, CLAVE, ahora=t0 + 15 * 60 + 1) == "access granted"


def test_usuario_con_espacios_y_mayusculas_se_normaliza(v):
    assert v.login("  ADMIN ", CLAVE) == "access granted"


def test_los_fallos_de_un_usuario_no_bloquean_a_otro(v):
    v.registrar("ana", CLAVE)
    for _ in range(5):
        v.login(USUARIO, "mala-mala-mala")
    assert v.login("ana", CLAVE) == "access granted"


def _pbkdf2_por_intento(monkeypatch, intentar):
    """Cuenta cuántas veces se llama a PBKDF2 en un solo intento fallido (el costo caro del login)."""
    import hashlib
    llamadas = []
    real = hashlib.pbkdf2_hmac
    monkeypatch.setattr(hashlib, "pbkdf2_hmac", lambda *a, **k: llamadas.append(1) or real(*a, **k))
    intentar()
    return len(llamadas)


def test_un_usuario_inexistente_cuesta_lo_mismo_que_uno_real(v, monkeypatch):
    """Si tardara el doble, el tiempo de respuesta delataría qué correos existen (se midió 152 ms vs 75 ms antes de corregirlo)."""
    existente = _pbkdf2_por_intento(monkeypatch, lambda: v.login(USUARIO, "mala-mala-mala"))
    inexistente = _pbkdf2_por_intento(monkeypatch, lambda: v.login("nadie", "mala-mala-mala"))
    assert existente == inexistente == 1


def test_el_login_real_del_servicio_tambien_cuesta_lo_mismo(monkeypatch):
    from api.auth import Autenticador
    monkeypatch.setenv("TOKEN_SECRET", "x" * 40)
    a = Autenticador(":memory:")
    a.registrar("ana@finnorte.mx", "segura1234")

    def fallar(correo):
        try:
            a.login(correo, "mala-mala-mala")
        except Exception:
            pass
    assert _pbkdf2_por_intento(monkeypatch, lambda: fallar("ana@finnorte.mx")) == \
        _pbkdf2_por_intento(monkeypatch, lambda: fallar("nadie@finnorte.mx")) == 1


# ── por qué se reemplaza el oficial (evidencia para la tabla de problemas) ──
def test_el_oficial_revela_si_el_usuario_existe():
    assert login_oficial.login("admin", "mala") != login_oficial.login("nadie", "mala")


def test_el_oficial_tiene_un_espacio_extra_en_el_mensaje():
    assert login_oficial.login("nadie", "x") == "user not found "


def test_el_oficial_no_bloquea_nunca():
    for _ in range(50):
        login_oficial.login("admin", "mala")
    assert login_oficial.login("admin", "1234") == "access granted"
