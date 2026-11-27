# Comparación de las 4 versiones (A3 · paso 6)

| Criterio | Original | `login_seguridad.py` | `login_eficiencia.py` | `login_mantenible.py` |
|---|---|---|---|---|
| Seguridad | Muy baja (P1, P2, P3 sin corregir) | **Alta** — hash+sal, tiempo constante, mensaje único | Baja a propósito — `==` y texto plano, igual que el original | Media — mensaje único (P1), pero sigue en texto plano y `==` |
| Claridad | Baja (anidado, literales mágicos) | Media (criptografía explícita pero sigue regresando `str`) | Alta (una función corta, un dict) | **Alta** — tipos, dataclasses, nombres explícitos |
| Eficiencia (latencia) | N/A (un único usuario) | Baja — PBKDF2 con 200 000 iteraciones es *caro* a propósito | **Alta** — una comparación de cadenas, sin criptografía | Alta — misma comparación simple que eficiencia |
| Escalabilidad (a N usuarios) | Nula — un `if` por usuario | Media — dict, pero sin API para agregar usuarios | **Alta** — dict pensado para muchos usuarios, O(1) | **Alta** — `AlmacenUsuarios` inyectable y extensible |
| Facilidad de prueba | Baja (todo hardcodeado, nada inyectable) | Media (constantes de módulo, no inyectable) | Media (dict de módulo, no inyectable) | **Alta** — `AlmacenUsuarios` se puede instanciar vacío por prueba |

## Recomendaciones de la IA: aceptadas, modificadas y descartadas

| Recomendación del asistente | Decisión | Criterio técnico |
|---|---|---|
| Usar `bcrypt` o `argon2` para el hash | **Modificada** → usé PBKDF2-HMAC-SHA256 | Es lo que ya usa `api/auth.py` en este mismo repo (consistencia del proyecto) y no agrega una dependencia nueva; PBKDF2 con 200 000 iteraciones cumple el mínimo de la actividad |
| Agregar un `try/except` genérico alrededor de toda la función "por si acaso" | **Descartada** | Oculta errores de programación reales (p. ej. pasar un tipo equivocado) en vez de dejarlos fallar en pruebas; no es manejo de errores, es silenciarlos |
| Unificar las 3 versiones en una sola función con banderas (`modo="seguro"`, `modo="rapido"`) | **Descartada** | El objetivo del ejercicio es comparar 3 diseños distintos; una sola función con banderas oculta el trade-off en vez de mostrarlo, y mezclaría responsabilidades |
| Usar `secrets.compare_digest` en vez de `hmac.compare_digest` | **Aceptada como equivalente, usé `hmac.compare_digest`** | Ambas son la misma comparación en tiempo constante; me quedé con `hmac` porque ya es la que usa `api/auth.py` en este repo |
| Agregar bloqueo por intentos fallidos dentro de `login()` mismo | **Descartada aquí, pero ya existe en otro lado** | Esa regla de negocio ya vive en `api/auth.py:Autenticador.login` (5 intentos / 15 min) y está probada en `tests/test_lab_producto.py::test_bloqueo_tras_5_intentos`; duplicarla en la función de ejemplo mezclaría dos capas distintas |

## Reflexión (A3 · paso 7)

Lo más útil de usar el asistente aquí no fue que escribiera el código — las 3 versiones las
terminé escribiendo y ajustando yo, decidiendo explícitamente qué problema atacaba cada
una — sino que me obligó a nombrar explícitamente el trade-off entre seguridad y velocidad
(P3/P4), que el `login()` original esconde porque simplemente no lo resuelve. Sin validar
cada sugerencia contra el código real del proyecto (por ejemplo, contra lo que ya hace
`api/auth.py`) hubiera terminado con 3 implementaciones de hashing distintas en el mismo
repo, que es exactamente el tipo de inconsistencia que esta actividad pide evitar.
