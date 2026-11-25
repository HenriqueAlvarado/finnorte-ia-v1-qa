"""A3 · login() OFICIAL del enunciado, tal cual. Es solo el punto de partida que se analiza: NO usarlo.

Problemas (ver la tabla del PDF): credenciales escritas en el código, comparación con ==,
mensajes distintos que revelan si el usuario existe, espacio extra en «user not found »,
sin hash, sin bloqueo, sin bitácora y sin pruebas.
"""


def login(user, password):
    if user == "admin":
        if password == "1234":
            return "access granted"
        else:
            return "wrong password"
    return "user not found "
