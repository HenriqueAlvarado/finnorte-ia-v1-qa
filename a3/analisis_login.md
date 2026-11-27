# Análisis del `login()` oficial (A3 · paso 3)

```python
def login(user, password):
    if user == "admin":
        if password == "1234":
            return "access granted"
        else:
            return "wrong password"
    return "user not found "
```

Prompt usado con el asistente: *"Actúa como revisor de seguridad y arquitectura. Analiza
esta función `login()` línea por línea: identifica vulnerabilidades, problemas de
rendimiento y problemas de mantenibilidad. Para cada uno dame: qué es, por qué importa en
un sistema real, y qué tipo de mejora lo resuelve (seguridad / eficiencia /
mantenibilidad). No me des el código corregido todavía, solo el análisis."*

La respuesta del asistente fue **suficiente como punto de partida pero incompleta**: listó
P1, P2 y P3 (correctamente, con el nombre técnico de cada vulnerabilidad), pero no detectó
por su cuenta el espacio final de `"user not found "` (P5) ni el acoplamiento de datos
dentro de la función (P7) — esos los encontré yo revisando el código carácter por carácter
y pensando en qué pasa si esto tuviera que soportar más de un usuario. Tampoco distinguió
que P2 y P4 compiten entre sí (hash es más seguro pero más lento); eso lo agregué yo al
armar la tabla de comparación (`comparacion.md`).

| # | Problema | Explicación técnica | Impacto real | Tipo de mejora |
|---|---|---|---|---|
| P1 | Mensajes de error distintos para usuario inexistente (`"user not found "`) y contraseña incorrecta (`"wrong password"`) | Permite **enumeración de usuarios**: un atacante prueba correos al azar y, por el mensaje que recibe, sabe cuáles existen sin necesidad de acertar la contraseña | Facilita ataques de fuerza bruta dirigidos (credential stuffing) solo contra cuentas confirmadas | Seguridad |
| P2 | La contraseña se guarda y se compara en **texto plano** (`password == "1234"`) | Si el valor viniera de una base de datos real, cualquier fuga de la base expone las contraseñas tal cual; no hay hash ni sal | Fuga catastrófica de credenciales ante cualquier acceso no autorizado a los datos | Seguridad |
| P3 | Comparación con `==` en vez de tiempo constante | `==` de cadenas en CPython corta en el primer carácter distinto: el tiempo de respuesta varía según cuántos caracteres acertó el atacante | Abre un **canal lateral de tiempo** que, con suficientes intentos, revela la contraseña carácter por carácter | Seguridad |
| P4 | Sin ningún costo computacional deliberado en la verificación | Lo contrario de P2/P3 en la balanza del paso 6: una comparación *demasiado* barata es rápida para el usuario legítimo pero también para quien hace fuerza bruta | Favorece ataques de fuerza bruta de alto volumen | Eficiencia (en tensión directa con seguridad) |
| P5 | `return "user not found "` con un espacio al final | Bug silencioso: cualquier código que compare `== "user not found"` (sin espacio) falla sin avisar | Bugs difíciles de reproducir aguas abajo (UI, pruebas, integraciones) | Mantenibilidad |
| P6 | El contrato de salida son cadenas sueltas sin tipo ni estructura | Quien llama a `login()` tiene que memorizar 3 literales exactos; no hay forma de distinguir "fallo" de "éxito" sin comparar texto | Acoplamiento frágil entre módulos; un typo en cualquiera de los dos lados rompe el flujo sin error explícito | Mantenibilidad |
| P7 | El usuario `"admin"` y la contraseña `"1234"` están escritos a mano dentro del `if` | Agregar un segundo usuario exige editar la función y anidar otro `if`; con decenas de usuarios sería una cadena de `elif` en O(N) | No escala: ni en legibilidad ni en tiempo de búsqueda | Eficiencia + Mantenibilidad |

## Matriz problema → versión → evidencia

| Problema | `login_seguridad.py` | `login_eficiencia.py` | `login_mantenible.py` |
|---|---|---|---|
| P1 enumeración de usuarios | ✅ corregido — línea `return "access granted" if coincide else MENSAJE_CREDENCIALES` (un solo mensaje) | ❌ se deja igual a propósito (no es el foco de esta versión) | ✅ corregido — una sola `MENSAJE_CREDENCIALES` para los dos casos |
| P2 texto plano / hash | ✅ corregido — `_hash()` con `hashlib.pbkdf2_hmac` + sal | ❌ a propósito (ver docstring del archivo): prioriza velocidad | parcial — sigue en texto plano (foco en estructura, no en cripto) |
| P3 comparación no constante | ✅ corregido — `hmac.compare_digest(calculado, hash_guardado)` | ❌ a propósito — usa `password == clave` (más rápido, reintroduce el canal lateral) | parcial — usa `==` (el foco es el contrato de salida, no el canal lateral) |
| P4 costo de verificación (trade-off) | alto costo (PBKDF2, 200 000 iteraciones) — ver prueba `test_seguridad_tarda_mas_que_eficiencia` | bajo costo (una comparación de cadenas) | bajo costo (una comparación de cadenas) |
| P5 espacio final en el mensaje | ✅ corregido | ✅ corregido — `"user not found"` sin espacio | ✅ corregido — ya no existe ese literal, se usa `MENSAJE_CREDENCIALES` |
| P6 contrato de salida sin tipo | parcial — sigue regresando `str` | parcial — sigue regresando `str` | ✅ corregido — regresa `ResultadoLogin(ok: bool, mensaje: str)` |
| P7 usuarios fijos / no escala | parcial — dict de un usuario, sin mecanismo para agregar más | ✅ corregido — dict con búsqueda O(1), pensado para N usuarios | ✅ corregido — `AlmacenUsuarios` inyectable con `registrar_usuario()` |

La evidencia de cada fila son las pruebas en `tests/test_a3_login_versiones.py`
(`test_seguridad_mismo_mensaje`, `test_eficiencia_escala_a_muchos_usuarios`,
`test_mantenible_registrar_usuario_nuevo`, etc.) y las líneas citadas arriba.
