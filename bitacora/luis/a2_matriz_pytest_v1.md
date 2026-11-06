# Matriz de la etapa 4 · qa_pytest v1

Modelo: gemini / gemini-3.1-flash-lite · casos de entrada: `a2_casos_entrada.json` (los mismos para v1 y v2)

Artefacto y Válida son del intento final; la última columna son los errores que la validación devolvió en el 1.er intento.

| Entrada | Rep | Prompt | Artefacto (final) | Válida | Intentos | 1.er intento | Errores (1.er intento) |
|---|---|---|---|---|---|---|---|
| RF07 | 1 | qa_pytest.v1 | test_rf07.py · 0/5 casos con su test | ✗ | 2 | ✗ | test_cp_rf07_01: no cita la regla REG-RF07-07; test_cp_rf07_02: no cita la regla REG-RF07-02; test_cp_rf07_03: no cita la regla REG-RF07-03; test_cp_rf07_04: no |
| RF12 | 1 | qa_pytest.v1 | test_rf12.py · 8/8 casos con su test | ✗ | 2 | ✗ | CP-RF12-01: falta la función test_cp_rf12_01; CP-RF12-02: falta la función test_cp_rf12_02; CP-RF12-03: falta la función test_cp_rf12_03; CP-RF12-04: falta la f |
| RF12 | 2 | qa_pytest.v1 | test_rf12.py · 8/8 casos con su test | ✗ | 2 | ✗ | CP-RF12-01: falta la función test_cp_rf12_01; CP-RF12-02: falta la función test_cp_rf12_02; CP-RF12-03: falta la función test_cp_rf12_03; CP-RF12-04: falta la f |
| RF12 | 3 | qa_pytest.v1 | test_rf12.py · 8/8 casos con su test | ✗ | 2 | ✗ | CP-RF12-01: falta la función test_cp_rf12_01; CP-RF12-02: falta la función test_cp_rf12_02; CP-RF12-03: falta la función test_cp_rf12_03; CP-RF12-04: falta la f |
| RF15 | 1 | qa_pytest.v1 | test_rf15.py · 9/9 casos con su test | ✗ | 2 | ✗ | test_cp_rf15_01: no cita la regla REG-RF15-01; test_cp_rf15_02: no cita la regla REG-RF15-04; test_cp_rf15_03: no cita la regla REG-RF15-01; test_cp_rf15_04: no |

Consistencia (RF12 × 3): [(False, 8, 'test_rf12.py'), (False, 8, 'test_rf12.py'), (False, 8, 'test_rf12.py')]  ← (válida al 1.er intento, casos con test, nombre_archivo)
