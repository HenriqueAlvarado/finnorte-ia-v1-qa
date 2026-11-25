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
