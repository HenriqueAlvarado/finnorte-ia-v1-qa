"""login() oficial de la Actividad 3 (texto literal de la consigna, sin tocar).

Se deja aquí, sin modificar, como punto de comparación para las 3 versiones
mejoradas (login_seguridad.py, login_eficiencia.py, login_mantenible.py) y
para el análisis de código en analisis_login.md.
"""


def login(user, password):
    if user == "admin":
        if password == "1234":
            return "access granted"
        else:
            return "wrong password"
    return "user not found "
