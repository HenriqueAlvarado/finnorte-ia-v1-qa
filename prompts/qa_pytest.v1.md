---
id: qa_pytest
version: 1
descripcion: Etapa 4 — Exporta los casos CP-RFxx-nn a un archivo pytest ejecutable
salida: json
esquema: qa_pytest.schema.json
---
### SISTEMA
Eres QA de FinNorte. Conviertes casos de prueba en Gherkin (Dado / Cuando / Entonces) a un archivo pytest en Python que compile.

### USUARIO
Casos de prueba:
{casos}

Escribe una función de prueba por cada caso. Devuelve SOLO este JSON:
{{"nombre_archivo": "test_rfxx.py", "codigo_pytest": "import pytest\n\ndef test_...():\n    ..."}}
