# Kit del Laboratorio A3 + A4 · versión 2

Este kit se copia **encima** del repositorio de tu equipo, el que tiene `pyproject.toml`, `src/finnorte/` y `corpus/`. Solo **agrega archivos nuevos**: no reemplaza nada de lo que ya tengas.

## Qué trae

| Archivo | Qué es | ¿Lo completas tú? |
|---|---|---|
| `api/auth.py` | Registro, login y token | **Sí:** 5 funciones `TODO(LAB)` en el laboratorio. Cuenta para tu A3 |
| `api/producto.py` | Servicio: login, token, errores `problem+json`, `/v1/preguntas`, `/v1/variante` y `/v1/agente` | No. En la A3 le agregas tu endpoint `POST /v1/<tu-variante>` |
| `src/finnorte/caso_guia/` | **Base resuelta** del caso guía: buscador BM25, asistente, herramientas, agente de referencia y motor de demostración | No (se usa, no se evalúa) |
| `src/finnorte/agente_servicio.py` | Confirmación humana en dos pasos y validador | No. En la A4 le pasas tu ejecutor y tu validador |
| `app/cliente_api.py` | Interfaz Streamlit del caso guía | No. En la A4 la adaptas a tu variante |
| `tests/test_lab_producto.py` | 12 pruebas del laboratorio | No |
| `.env.lab.example` | Líneas que agregas al final de tu `.env` | — |

**No necesitas tener terminadas la A1, el Avance 1 ni la A4.** El caso guía no usa esos archivos.

## Cómo copiarlo sin borrar nada

En la raíz del repositorio de tu equipo:

```
wget -O kit.zip https://github.com/CyberProf-tecmi/lsca2318-lab-a3-a4/raw/main/kit_lab_A3_A4_alumno.zip
unzip -n kit.zip && rm kit.zip
cat .env.lab.example >> .env
```

`unzip -n` nunca sobrescribe. Si ya habías copiado el kit anterior (v1), revisa la sección 7 del manual.

## Cómo se corre

```
uvicorn api.producto:app --reload        # terminal 1 → /docs
streamlit run app/cliente_api.py         # terminal 2 → interfaz
pytest tests/test_lab_producto.py        # sin auth.py: 3 passed, 9 skipped · completo: 12 passed
```
