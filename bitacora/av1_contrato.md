# Mediciones A–D contra `contrato_calidad.yaml`

Contrato: Equipo 1 · v1-qa · fecha 2026-11-06.
Datos: `bitacora/av1_A.json` … `av1_D.json` (gemini-3.1-flash-lite, 20 casos × 3 repeticiones).

| Meta | Objetivo | A | B | C | D |
|---|---|---|---|---|---|
| exactitud_min | >= 0.8 | 0.167 ✗ | 0.217 ✗ | 0.45 ✗ | 0.433 ✗ |
| citas_correctas_min | >= 0.8 | 0.35 ✗ | 0.35 ✗ | 0.9 ✓ | 0.8 ✓ |
| alucinacion_max | <= 0.05 | 1 ✗ | 0 ✓ | 0 ✓ | 0 ✓ |
| fuga_pii_max | <= 0.0 | 0.117 ✗ | 0.133 ✗ | 0.2 ✗ | 0.15 ✗ |
| abstencion_correcta_min | >= 0.85 | 0.8 ✗ | 0.8 ✗ | 0.8 ✗ | 1 ✓ |
| consistencia_min | >= 0.75 | 0.95 ✓ | 0.95 ✓ | 0.75 ✓ | 0.75 ✓ |
| latencia_p95_ms_max | <= 20000 | 60944 ✗ | 76672 ✗ | 44719 ✗ | 41214 ✗ |
| costo_promedio_usd_max | <= 0.005 | 0.00513 ✗ | 0.00925 ✗ | 0.0114 ✗ | 0.00922 ✗ |

Metas cumplidas por configuración: A 1/8 · B 2/8 · C 3/8 · D 4/8
