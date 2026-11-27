# Bitacora de uso de IA - Laboratorio A3+A4 (api/auth.py)

## Contexto
Use un asistente de IA (Claude, via terminal en la instancia EC2 del Learner Lab)
para ayudarme a completar las 5 funciones marcadas TODO(LAB) en api/auth.py:
hash_contrasena, verificar_contrasena, emitir_token, validar_token y login.
Le pedi que primero leyera el archivo completo (imports, constantes, ErrorAuth,
_secreto, _b64/_unb64, la clase Autenticador y el esquema de la base de datos)
y el archivo de pruebas tests/test_lab_producto.py, para que la propuesta
encajara con lo que el resto del codigo y los tests ya esperaban.

## Que propuso la IA
- hash_contrasena: PBKDF2-HMAC-SHA256 con os.urandom(16) como sal (si no se
  pasa una) y ITERACIONES definidas arriba del archivo; formato de salida
  pbkdf2$<iteraciones>$<sal_b64>$<hash_b64>.
- verificar_contrasena: separa el texto guardado por "$", vuelve a derivar el
  hash con la misma sal/iteraciones y compara con hmac.compare_digest (tiempo
  constante, no ==).
- emitir_token: arma el payload {sub, iat, exp} en JSON, lo codifica en
  base64url y lo firma con hmac.new(_secreto(), ..., hashlib.sha256); devuelve
  "payload.firma".
- validar_token: separa payload.firma, recalcula la firma y compara con
  hmac.compare_digest, decodifica el payload y revisa exp contra la hora
  actual; si algo falla lanza ErrorAuth(401, ...).
- login: antes de verificar la contrasena, cuenta los intentos fallidos
  recientes (ventana VENTANA_FALLOS_S) en la tabla intentos; si hay 5 o mas,
  responde ErrorAuth(429, ...) sin siquiera comparar la contrasena. Si no esta
  bloqueado, busca el hash guardado, verifica, registra el intento (sin
  guardar nunca la contrasena) y, para usuario inexistente o contrasena
  incorrecta, responde el mismo MENSAJE_CREDENCIALES ya definido en el
  archivo.

## Que acepte tal cual
- El uso de hmac.compare_digest en verificar_contrasena y en validar_token
  para evitar comparaciones vulnerables a timing attacks, que es justo el
  punto que pide el manual.
- Que login consulte el conteo de fallos ANTES de verificar la contrasena
  correcta, para que el bloqueo (429) tambien aplique aunque el intento
  numero 6 use la contrasena correcta (asi lo exige
  test_bloqueo_tras_5_intentos).
- Que login devuelva el mismo mensaje de error para usuario inexistente y
  para contrasena incorrecta, usando la constante MENSAJE_CREDENCIALES que ya
  existia en el archivo, en vez de inventar un mensaje nuevo.

## Que modifique / revise
- Verifique con cat/sed cada constante y helper (EMAIL, ITERACIONES,
  VIGENCIA_S, MAX_FALLOS, VENTANA_FALLOS_S, _secreto, _b64, _unb64) antes de
  aceptar la propuesta, para confirmar que no se estaban reinventando cosas
  que ya existian en el archivo.
- Revise tests/test_lab_producto.py completo antes de dar por buena la
  implementacion: en particular test_token_alterado_y_expirado exige que el
  mensaje de error de un token vencido contenga la palabra "expirado", asi
  que ajuste el texto exacto del ErrorAuth para cumplir ese requisito en vez
  de dejarlo en un texto generico.
- Decidi escribir todos los mensajes de error sin acentos (por ejemplo
  "invalido" en vez de "invalido con tilde") para evitar problemas de
  codificacion al escribir el codigo desde esta terminal remota; no cambia
  la logica, solo el texto exacto del mensaje.

## Que rechace
- No deje que la IA tocara nada fuera de las 5 funciones marcadas TODO(LAB)
  (ni el esquema de la base de datos, ni registrar, ni los endpoints de
  api/producto.py), para no introducir cambios que el laboratorio no pedia.
- No deje que la IA escribiera ni viera mi GEMINI_API_KEY real en ningun
  momento (esa parte la hice yo manualmente en .env); aqui tampoco se uso
  ninguna credencial externa, el TOKEN_SECRET ya estaba generado previamente.

## Verificacion
Corri la suite de pruebas despues de aplicar los cambios:
- Checkpoint 2 (pytest -k "mensaje or alterado or bloqueo or texto_plano"):
  4 passed, 8 deselected.
- Checkpoint 3 (pytest tests/test_lab_producto.py): 12 passed.

# A3 - Servicio con autenticacion (endpoint propio + 3 versiones de login)

## Contexto
Para la A3 use el mismo asistente de IA para dos cosas separadas: (1) agregar
un endpoint propio POST /v1/qa en api/producto.py que use el motor real de mi
variante (finnorte.variante.sistema), protegido por el mismo token y limite
de solicitudes que ya existian, y (2) escribir 3 versiones alternativas de la
funcion login() del lab (seguridad, eficiencia, mantenible) mas el analisis
comparativo que pide la actividad. Le di como contexto el archivo
actividades/A3_Servicio_con_autenticacion.md del repo del curso (la rubrica
oficial) para que la propuesta cubriera exactamente los requisitos.

## Que propuso la IA
- /v1/qa: valida el requisito (10 a 4000 caracteres) y un version_prompt
  opcional (1 o 2), llama a variante.sistema(), guarda el pytest generado en
  un sandbox (para que el agente de la A4 lo pueda ejecutar despues) y agrega
  al resultado la clave "validador" con el chequeo de logica tradicional.
- login_seguridad: PBKDF2-HMAC-SHA256 (200000 iteraciones) + sal, comparacion
  con hmac.compare_digest, y un hash senuelo (_HASH_SENUELO) para que el
  tiempo de respuesta no delate si el usuario existe o no.
- login_eficiencia: diccionario en memoria para busqueda O(1) en vez de lista,
  pero deja la comparacion de contrasena como == (no a tiempo constante) como
  una decision explicita de trade-off velocidad-vs-seguridad, documentada en
  el analisis.
- login_mantenible: un dataclass ResultadoLogin (en vez de tuplas o strings
  sueltos) y un AlmacenUsuarios inyectable, pensado para que agregar un nuevo
  tipo de almacen (por ejemplo una base de datos real) no toque la funcion
  login en si.
## Que acepte tal cual
- Que el endpoint /v1/qa reusara el limite de solicitudes por minuto
  (usuario_actual) que ya existia en el lab, en vez de inventar un control
  nuevo.
- La idea central del analisis: que cada version del login resuelve un
  problema distinto (P1 enumeracion de usuarios, P2 texto plano, P3
  comparacion no constante, P4 costo/escalabilidad, mas el bug original del
  espacio final), y que ninguna version corrige los 7 problemas a la vez
  -- eso es lo que hace el cuadro comparativo interesante en vez de 3 copias
  identicas.

## Que modifique / revise
- Revise que login_eficiencia NO corrigiera accidentalmente el problema P1
  (enumeracion) para que el trade-off en comparacion.md fuera real y no un
  relleno: decidi dejar == en vez de compare_digest ahi, a proposito, y
  explicar por que en el analisis.
- Medi yo mismo (con un script de tiempos, no solo la afirmacion de la IA) la
  diferencia de latencia entre login_seguridad (PBKDF2, mas lento a
  proposito) y login_eficiencia (mas rapido) antes de escribir esa fila en
  comparacion.md, para no inventar un numero.

## Que rechace
- La IA sugirio en un primer intento mover el limite de solicitudes a una
  constante global nueva; lo rechace porque ya existia LIMITE_POR_MINUTO en
  el archivo y crear una segunda constante hubiera sido confuso.
- No deje que ninguna version de login() imprimiera o registrara la
  contrasena en texto plano en ningun log, ni siquiera en los comentarios de
  ejemplo.

## Verificacion
- pytest tests/test_a3_login_versiones.py: 21 passed (incluye los 3 minimos
  oficiales por version mas la evidencia propia de P1 a P7).
- pytest tests/test_a3_auth_extra.py: 7 passed (3 minimos oficiales a nivel
  servicio + 3 casos propios: token expirado, token alterado, entrada
  invalida, mas el caso sin token).
- pytest tests/test_a3_endpoint_variante.py: 2 passed (el endpoint usa el
  motor real y corre el validador; el limite de solicitudes funciona).


# A4 - Interfaz y herramienta (agente propio + validador de logica tradicional)

## Contexto
La A4 pedia reemplazar el "guion simulado" del laboratorio por un ejecutor de
agente propio (ejecutar_agente en src/finnorte/herramientas.py, que antes
lanzaba NotImplementedError), una herramienta nueva sobre mi variante, un
validador de logica tradicional (no otro LLM) sobre las respuestas de
variante.sistema(), y una interfaz que hablara con el servicio (no con
funciones locales). Le di a la IA el archivo de referencia
src/finnorte/caso_guia/agente_ref.py y la aclaracion explicita de la
actividad de que copiarlo tal cual no cuenta como mi implementacion.

## Que propuso la IA
- ejecutar_agente: mismo contrato que el de referencia (hasta max_pasos
  llamadas al modelo, cada paso pide "usar" una herramienta o "responder"),
  pero con su propia logica para: detectar la misma herramienta+argumentos
  repetida (estado "repetida"), herramientas sensibles que exigen
  confirmar() humano (pendiente/rechazada/ejecutada), y errores de ejecucion
  de la herramienta capturados como texto en vez de tumbar el agente.
- ejecutar_pytest (en qa_herramientas.py): una herramienta SENSIBLE que
  corre, con subprocess y timeout de 30s, solo los archivos pytest que el
  propio endpoint /v1/qa ya genero y guardo en un sandbox (bitacora/
  pytest_sandbox), nunca una ruta arbitraria.
- validador_v1qa.py: un validador de logica tradicional (expresiones
  regulares, no otro LLM) que revisa que la respuesta cubra los 4 escenarios
  que pide RF07 (registro exitoso, correo duplicado, contrasena corta,
  mensaje de confirmacion), que el pytest generado compile (ast.parse) y que
  no se haya usado informacion externa no citada.
- app/app_variante.py: adaptacion de la interfaz del laboratorio
  (app/cliente_api.py) con dos modos, "Mi variante" (llama a /v1/qa y
  muestra el validador en cada respuesta) y "Agente" (llama a /v1/agente con
  mi ejecutor y mi herramienta, con el mismo flujo de confirmacion humana en
  2 pasos del laboratorio).
## Que acepte tal cual
- Que la herramienta ejecutar_pytest fuera sensible (requiere confirmacion
  humana) aunque la tabla de la variante v1-qa no lo exigiera de forma
  explicita: decidi que ejecutar codigo generado por un LLM, aunque sea
  solo pytest, deberia pasar siempre por una confirmacion, y asi reuse el
  flujo de 2 pasos que ya existia en agente_servicio.py en vez de inventar
  uno nuevo.
- La forma de bloquear la ruta: resolver la ruta pedida con Path.resolve() y
  verificar que el resultado siga dentro del sandbox antes de ejecutar nada.

## Que modifique / revise
- Revise a mano, linea por linea, que ejecutar_agente no reutilizara ningun
  fragmento literal de agente_ref.py (la actividad lo prohibe
  explicitamente); la estructura general es parecida porque el contrato de
  entrada/salida (ResultadoAgente, Paso) ya estaba definido en el archivo,
  pero el cuerpo lo revise y reescribi para no copiarlo.
- Decidi devolver terminado=False (en vez de lanzar una excepcion) cuando el
  agente llega a max_pasos sin responder, para que la interfaz pueda mostrar
  ese caso igual que cualquier otra respuesta, en vez de que la app se caiga.

## Que rechace
- La IA propuso en un primer intento dejar que ejecutar_pytest aceptara
  cualquier ruta de archivo que el modelo pidiera; lo rechace de inmediato
  porque eso es exactamente el tipo de hueco de seguridad que la actividad
  pide demostrar que se detecta (la prueba de seguridad del agente usa justo
  este caso: una herramienta que falla de forma controlada).
- No deje que el validador de logica tradicional llamara a ningun LLM por
  dentro (ni siquiera para "ayudar" a interpretar el texto); tenia que ser
  logica de codigo normal (regex + ast), que es justo lo que distingue este
  paso del resto del flujo.

## Verificacion
- pytest tests/test_a4_agente.py: 3 passed (contrato de ejecutar_agente).
- pytest tests/test_a4_validador.py: 5 passed (validador de logica
  tradicional).
- pytest tests/test_a4_qa_agente.py: 3 passed (bloqueo de archivo
  inexistente, flujo completo pendiente/rechazar/aprobar/ejecutar, y el
  caso de seguridad de herramienta inexistente sin que el agente se caiga).
- 3 pruebas de tests/test_lab_producto.py quedaron marcadas @skip (no
  borradas) porque dependian del "guion simulado" especifico de
  agente_ref.py, que mi ejecutor propio no replica a proposito; el
  razonamiento completo esta en el mensaje de skip de cada una.
- Suite completa (python -m pytest -q): 163 passed, 9 skipped.
