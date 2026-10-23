# Dominio agronómico — reglas de negocio clave

## Índices de vegetación y cuándo usar cada uno

| Índice | Cuándo usarlo | Bandas (Sentinel-2) |
|---|---|---|
| **SAVI** | Primeras 3 semanas post-siembra (cobertura < 30%) | NIR, RED |
| **NDVI** | Crecimiento vegetativo (25–60 días desde siembra) | B8, B4 |
| **GNDVI** | Cuando NDVI > 0.75 (fase reproductiva, saturación) | B8, B3 |
| **NDRE** | Detección temprana de estrés clorofílico, nitrógeno | B8, B5 |
| **EVI** | Cultivos muy densos donde NDVI satura | B8, B4, B2 |
| **MSAVI** | Inicio de campaña, suelo expuesto | NIR, RED |

**Fórmula NDVI:** `(NIR - RED) / (NIR + RED)` → bandas Sentinel-2: B8 (NIR), B4 (RED)

## Umbrales NDVI para alertas automáticas

```python
# Reglas generales
ndvi < 0.20          → suelo desnudo / sin vegetación
0.20 <= ndvi < 0.70  → cultivo con estrés o en desarrollo
ndvi >= 0.70         → vigor óptimo

# Soja — ciclo fenológico
if dias_desde_siembra < 25:       usar SAVI
if 25 <= dias_desde_siembra < 60: usar NDVI
if ndvi > 0.75:                   usar GNDVI (floración/llenado)
if delta_ndvi < 0 and ndvi → 0.2: estado Senescencia/Cosecha

# Clasificación temporal soja/maíz (sur Córdoba)
pico_ndvi < 2026-02-01  → Siembra Temprana (De Primera)
pico_ndvi > 2026-02-01  → Siembra Tardía (De Segunda)
ndvi_max_estival < 0.70 → alerta "Ciclo Incompleto"
```

**Cómo lo usa el motor (v1.1.0):** "NDVI bajo" en las reglas es `reglas.py::ndvi_bajo()`, es decir, por debajo del `ndvi_min` del estadio en `ndvi_esperado_estadio`. Solo sin curva para ese cultivo+estadio cae al corte fijo 0.50. La severidad toma la peor caída entre la del promedio del lote y la de lo esperado. La curva de la migración 0025 es genérica (placeholder): si da falsos positivos, ajustar la curva antes que los umbrales de las reglas.

## Patrones espaciales → diagnóstico

| Patrón | Causa probable | Índice afectado |
|---|---|---|
| Circular / radial | Enfermedades fúngicas (Sclerotinia, Rhizoctonia) | NDRE bajo, NDVI bajo |
| Lineal / franjas | Compactación, falla sembradora | NDVI bajo uniforme en franjas |
| Difuso / gradiente | Variabilidad edáfica, déficit hídrico, deficiencia N | NDVI bajo generalizado |
| Aleatorio / disperso | Plagas móviles (orugas, chinches), granizo | NDVI bajo puntual |
| Manchones persistentes | Nematodos, salinidad, suelo (posición fija entre campañas) | NDVI/GNDVI crónicos |
| Siguiendo microtopografía | Anegamiento, Phytophthora (partes bajas del lote) | NDWI alto + NDVI bajo |

**Métricas de forma (Shapely):**
```python
circularidad = (4 * pi * area) / perimetro**2  # ~1 → enfermedad focal
elongacion   = eje_mayor / eje_menor            # alta → compactación/maquinaria
densidad     = num_poligonos / area_total       # alta → plagas/granizo
```

## Particularidades del NEA (Chaco)
- Vertisoles: grietas en época seca generan patrones lineales — usar SAVI en lugar de NDVI cuando la cobertura es < 30%
- Anegamiento temporario frecuente (pendientes < 0.5%) — cruzar NDWI + NDVI + MDE
- Suelos sódico-salinos: NDVI crónico < 0.2 — marcar como limitación edáfica permanente, no fitosanitaria
- Temperaturas altas (> 25°C suelo) → Meloidogyne incognita es el nematodo predominante en algodón

## Diagnóstico — mensajes al usuario

El sistema debe comunicar tres niveles de certeza:
1. **"Diagnóstico probable con alta confianza"** — patrón + índice + contexto consistentes con una sola causa
2. **"Diagnóstico ambiguo — se requiere verificación en campo"** — dos o más causas con igual verosimilitud
3. **"Patrón no clasificable — factor edáfico permanente probable"** — patrón persistente entre campañas, sin respuesta a tratamiento
