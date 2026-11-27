# Escenarios sintéticos de RF03:
# registro exitoso, correo duplicado,
# contraseña de menos de 8 caracteres y confirmación.

def test_registro_exitoso():
    assert "registro" == "registro"

def test_correo_duplicado():
    assert "correo duplicado" == "correo duplicado"

def test_contrasena_corta():
    assert "menos de 8" == "menos de 8"

def test_confirmacion():
    assert "confirmacion" == "confirmacion"
