# Lectura de la matriz con 3 entradas (Lab 2, checkpoint 5)

Archivo: `bitacora/a2_matriz_entradas.md`, generado con
`python guia/a2_flujo_variante.py --requisitos RF07,RF12,RF15` (gemini-3.1-flash-lite, con RAG, k=4, 6 de noviembre).

Primero lo intenté con gemini-3.5-flash, el modelo de `bitacora/a2_matriz.md`, pero la cuota diaria ya estaba agotada (HTTP 429 en las 3 entradas). Por eso esta corrida usa flash-lite, el mismo modelo de la medición A–D.

## Qué pasó

| Entrada | Llegó hasta | Por qué se detuvo |
|---|---|---|
| RF07 | analizar | La validación de la etapa 1 encontró datos personales en `datos_prueba` y el reintento no lo corrigió |
| RF12 | revisar | El modelo reportó 0 casos positivos y el conteo en código encontró 1 |
| RF15 | revisar | El modelo reportó 2 casos `limite_exacto` y el conteo en código encontró 1 |

Ningún flujo llegó a la etapa 4 (`pytest`). Hubo 4 de 7 etapas válidas al primer intento y la corrida costó US$0.025.

## Qué significa

- Las tres paradas son validaciones en código que hicieron su trabajo: no dejaron pasar un dato personal ni un conteo de cobertura equivocado. Sin `validar=`, el flujo habría seguido con información falsa.
- Con flash-lite el flujo es más frágil que con 3.5-flash: en `a2_matriz.md` (RF12 × 3 con 3.5-flash) los 3 flujos llegaron completos.
- Pendiente: repetir con gemini-3.5-flash cuando se renueve la cuota, para tener las 3 entradas con el mismo modelo que la matriz de consistencia. Si `revisar` sigue fallando por el conteo, una opción es darle el recuento hecho en código dentro del prompt, en lugar de pedirle al modelo que cuente.
