"""Caso guía del Laboratorio A3 + A4 · BASE RESUELTA (se usa, NO se evalúa).

Este paquete existe para que el laboratorio funcione aunque todavía no termines
A1 (buscador semántico), Avance 1 (motor de tu variante) ni A4 (tu ejecutor del agente).
No reemplaza ni toca esos archivos: vive aparte, en src/finnorte/caso_guia/.

| Módulo          | Qué hace                                                        |
|-----------------|-----------------------------------------------------------------|
| buscador.py     | Busca en corpus/comun con BM25 (palabras clave; no usa tu A1)   |
| asistente.py    | Responde preguntas del caso guía con citas o se abstiene        |
| herramientas.py | Herramientas del agente: buscar_manual, revisar_ventana_despliegue, crear_ticket_cambio (sensible) |
| agente_ref.py   | Ejecutor de REFERENCIA del agente (la A4 te pide implementar el tuyo en herramientas.py) |
| motor_demo.py   | Motor de DEMOSTRACIÓN para /v1/variante mientras tu sistema() no exista |
"""
