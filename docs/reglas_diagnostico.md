# Reglas del motor de diagnóstico

Generado desde `app/diagnostico/reglas.py`. Son 20 reglas evaluadas **en este orden**: para cada zona gana la **primera** que cumple todo (cultivo, estadio, índices disponibles y condición) y las demás no se evalúan.

Los estadios se comparan normalizados (minúsculas, sin acentos, espacios → guión bajo). `área_ha` es el área de la zona; `patrón` es el patrón espacial de la zona (ver al final).

## Resumen

| # | Regla | Bloque | Cultivo | Estadios | Índices que necesita | Condición | Confianza | Causa |
|---|---|---|---|---|---|---|---|---|
| 1 | **R00** Copa de árbol u obstáculo físico | exclusiones | todos | todos | NDVI | `NDVI < 0.20 Y patrón == "circular" Y área_ha < 0.05` | alta | sin_problema_detectado |
| 2 | **R01** Suelo desnudo — sin cobertura vegetal | exclusiones | todos | todos | NDVI | `NDVI < 0.20` | alta | sin_problema_detectado |
| 3 | **R10** Interferencia de malezas | malezas | todos | todos | NDVI, EXG | `NDVI < 0.50 Y EXG > 0.20` | alta | interferencia_vegetacion |
| 4 | **R20** Enfermedad fúngica en soja — estadio reproductivo | enfermedades_fungicas | soja | r1, r2, r3, r4, r5 | NDVI | `NDVI < 0.50 Y patrón == "circular"` | alta | estres_biotico_fungico |
| 5 | **R21** Enfermedad tardía en soja — detección por GNDVI | enfermedades_fungicas | soja | r3, r4, r5 | GNDVI | `GNDVI < 0.40 Y patrón in {"circular", "focos_aislados"}` | media | estres_biotico_fungico |
| 6 | **R22** Enfermedad fúngica en maíz | enfermedades_fungicas | maiz | v7, v8, v9, v10, v11, v12, vt | NDVI | `NDVI < 0.50 Y patrón == "circular"` | media | estres_biotico_fungico |
| 7 | **R23** Enfermedad fúngica en algodón | enfermedades_fungicas | algodon | r1, r2, boton_floral, floracion | NDVI | `NDVI < 0.50 Y patrón in {"circular", "focos_aislados"}` | media | estres_biotico_fungico |
| 8 | **R24** Enfermedad fúngica en sorgo | enfermedades_fungicas | sorgo | v6, v7, v8, v9, espigado, floracion | NDVI | `NDVI < 0.50 Y patrón in {"circular", "focos_aislados"}` | media | estres_biotico_fungico |
| 9 | **R30** Ataque de insectos en soja | insectos | soja | r1, r2, r3, r4, v4, v5, v6 | NDVI | `NDVI < 0.50 Y patrón in {"manchas_irregulares", "focos_aislados"}` | media | estres_biotico_insecto |
| 10 | **R31** Ataque de insectos en maíz y sorgo | insectos | maiz, sorgo | v6, v7, v8, v9, v10, v11, v12, vt | NDVI | `NDVI < 0.50 Y patrón in {"manchas_irregulares", "bordes_lote"}` | media | estres_biotico_insecto |
| 11 | **R32** Ataque de insectos en algodón | insectos | algodon | r1, r2, r3, boton_floral, floracion | NDVI | `NDVI < 0.50 Y patrón in {"manchas_irregulares", "focos_aislados", "circular"}` | media | estres_biotico_insecto |
| 12 | **R40** Déficit de nitrógeno en soja | nutricional | soja | r1, r2, v4, v5, v6 | NDRE | `NDRE < 0.20 Y patrón in {"difuso_homogeneo", "por_sectores"}` | alta | estres_nutricional_nitrogeno |
| 13 | **R41** Déficit de nitrógeno en maíz y sorgo | nutricional | maiz, sorgo | v4, v5, v6, v7, v8 | NDRE | `NDRE < 0.20 Y patrón in {"difuso_homogeneo", "por_sectores"}` | alta | estres_nutricional_nitrogeno |
| 14 | **R42** Déficit de nitrógeno en algodón | nutricional | algodon | v4, v5, v6, v7, v8 | NDRE | `NDRE < 0.20 Y patrón in {"difuso_homogeneo", "por_sectores"}` | alta | estres_nutricional_nitrogeno |
| 15 | **R43** Déficit de micronutrientes (Mg, B) | nutricional | todos | todos | NDRE | `NDRE < 0.20 Y patrón in {"bordes_lote", "manchas_irregulares"}` | media | estres_nutricional_micro |
| 16 | **R44** Déficit de fósforo | nutricional | maiz, soja | v1, v2, v3, v4, v5, v6 | NDVI, NDRE | `NDVI < 0.50 Y NDRE < 0.20 Y patrón in {"por_sectores", "difuso_homogeneo"}` | media | estres_nutricional_fosforo |
| 17 | **R50** Estrés hídrico generalizado | hidrico | todos | todos | NDVI | `NDVI < 0.50 Y patrón == "difuso_homogeneo"` | media | estres_hidrico |
| 18 | **R60** Madurez temprana diferencial en algodón | madurez | algodon | r4, r5, apertura_de_capsulas | NDVI | `NDVI < 0.25 Y NDVI < 0.40 * NDVI_promedio_lote Y patrón in {"focos_aislados", "manchas_irregulares"}` | media | madurez_temprana_diferencial |
| 19 | **R70** Vigor excesivo en maíz | vigor | maiz | r1, vt | NDVI | `NDVI > 0.85 Y patrón == "difuso_homogeneo"` | baja | vigor_excesivo |
| 20 | **R99** Sin problema detectado | cierre | todos | todos | — | `True` | alta | sin_problema_detectado |

## Detalle de cada regla

### 1. R00 — Copa de árbol u obstáculo físico

- **Bloque:** exclusiones
- **Aplica a:** cultivo todos; estadios todos
- **Índices requeridos:** NDVI
- **Condición:** `NDVI < 0.20 Y patrón == "circular" Y área_ha < 0.05`
- **Confianza:** alta · **Causa:** sin_problema_detectado · **Excluye la zona del análisis**

**Qué hacer:** La zona se excluye del análisis. No se genera diagnóstico ni recomendación de producto. Se marca como obstáculo para que el frontend la muestre diferenciada en el mapa.

**Cómo confirmarlo en campo:** No requiere confirmación. Si el productor sabe que hay árboles en esa posición del lote, la regla es correcta. Si no había árboles, puede ser un charco de agua (también NDVI muy bajo) — en ese caso se descarta manualmente.

### 2. R01 — Suelo desnudo — sin cobertura vegetal

- **Bloque:** exclusiones
- **Aplica a:** cultivo todos; estadios todos
- **Índices requeridos:** NDVI
- **Condición:** `NDVI < 0.20`
- **Confianza:** alta · **Causa:** sin_problema_detectado

**Qué hacer:** No se genera recomendación de agroquímico. Se alerta al usuario para que verifique la implantación del cultivo en esa zona. Puede ser suelo desnudo por falla de siembra, rastrojo seco o pisoteo de maquinaria.

**Cómo confirmarlo en campo:** Verificar en campo si hay plantas en esa zona. Si no hay plantas, el problema fue de implantación — no es tratable con agroquímico.

### 3. R10 — Interferencia de malezas

- **Bloque:** malezas
- **Aplica a:** cultivo todos; estadios todos
- **Índices requeridos:** NDVI, EXG
- **Condición:** `NDVI < 0.50 Y EXG > 0.20`
- **Confianza:** alta · **Causa:** interferencia_vegetacion

**Qué hacer:** Aplicar herbicida selectivo según el cultivo presente. Para soja usar herbicida graminicida o de hoja ancha según el tipo de maleza. Para maíz usar atrazina u otro herbicida registrado. Para algodón usar cletodim u otro selectivo.

**Cómo confirmarlo en campo:** Recorrer la zona identificada y verificar qué tipo de maleza está presente. Observar si son de hoja ancha (yuyo colorado, enredadera) o gramíneas (sorgo de alepo, gramón). Esto define el herbicida a usar.

### 4. R20 — Enfermedad fúngica en soja — estadio reproductivo

- **Bloque:** enfermedades_fungicas
- **Aplica a:** cultivo soja; estadios r1, r2, r3, r4, r5
- **Índices requeridos:** NDVI
- **Condición:** `NDVI < 0.50 Y patrón == "circular"`
- **Confianza:** alta · **Causa:** estres_biotico_fungico

**Qué hacer:** Aplicar fungicida en las zonas afectadas. Los más usados en el NEA son los triazoles (tebuconazol, propiconazol) o las mezclas estrobilurina + triazol (azoxistrobina + ciproconazol). Evaluar la severidad de la afección antes de decidir si tratar solo las zonas afectadas o todo el lote.

**Cómo confirmarlo en campo:** Buscar en las hojas de la zona afectada: pústulas de color óxido o marrón en el envés de la hoja (roya asiática), o manchas circulares con centro gris rodeadas de halo amarillo (mancha marrón, ojo de rana). Para roya: rascar levemente el envés de la hoja con el dedo — si hay polvo anaranjado, confirma roya.

### 5. R21 — Enfermedad tardía en soja — detección por GNDVI

- **Bloque:** enfermedades_fungicas
- **Aplica a:** cultivo soja; estadios r3, r4, r5
- **Índices requeridos:** GNDVI
- **Condición:** `GNDVI < 0.40 Y patrón in {"circular", "focos_aislados"}`
- **Confianza:** media · **Causa:** estres_biotico_fungico

**Qué hacer:** Evaluar si el estadio aún permite que un tratamiento fungicida sea económicamente viable. En R5 avanzado o R6, la efectividad del fungicida es baja porque el grano ya está formado. Si el estadio lo justifica, aplicar fungicida de acción rápida.

**Cómo confirmarlo en campo:** Observar las hojas del tercio medio y superior de la planta. Buscar hojas con amarillamiento irregular que avanza desde los bordes hacia el centro, manchas necróticas o presencia de estructuras fúngicas visibles. Comparar con plantas sanas del lote para distinguir senescencia normal de patológica.

### 6. R22 — Enfermedad fúngica en maíz

- **Bloque:** enfermedades_fungicas
- **Aplica a:** cultivo maiz; estadios v7, v8, v9, v10, v11, v12, vt
- **Índices requeridos:** NDVI
- **Condición:** `NDVI < 0.50 Y patrón == "circular"`
- **Confianza:** media · **Causa:** estres_biotico_fungico

**Qué hacer:** Si se confirma en campo, aplicar fungicida. Los triazoles tienen buena acción sobre las enfermedades foliares del maíz.

**Cómo confirmarlo en campo:** Buscar en las hojas: lesiones alargadas de color gris verdoso que avanzan de forma necrótica desde el margen de la hoja hacia el nervio central (tizón foliar), o manchas de color agua que se tornan necróticas con halo amarillo (antracnosis foliar). En tizón el síntoma característico es la forma de cigarro en las lesiones.

### 7. R23 — Enfermedad fúngica en algodón

- **Bloque:** enfermedades_fungicas
- **Aplica a:** cultivo algodon; estadios r1, r2, boton_floral, floracion
- **Índices requeridos:** NDVI
- **Condición:** `NDVI < 0.50 Y patrón in {"circular", "focos_aislados"}`
- **Confianza:** media · **Causa:** estres_biotico_fungico

**Qué hacer:** Si se confirma, aplicar fungicida. El mancozeb o los triazoles son efectivos contra la alternaria. Respetar el intervalo de seguridad antes de la cosecha.

**Cómo confirmarlo en campo:** Buscar en las hojas: manchas de color marrón oscuro a negro con forma irregular, a veces rodeadas por un halo clorótico amarillo (alternaria). Las manchas suelen aparecer primero en las hojas más viejas y avanzar hacia arriba. En Verticillium buscar en el tallo al cortarlo transversalmente: el tejido vascular aparece marrón oscuro o negro.

### 8. R24 — Enfermedad fúngica en sorgo

- **Bloque:** enfermedades_fungicas
- **Aplica a:** cultivo sorgo; estadios v6, v7, v8, v9, espigado, floracion
- **Índices requeridos:** NDVI
- **Condición:** `NDVI < 0.50 Y patrón in {"circular", "focos_aislados"}`
- **Confianza:** media · **Causa:** estres_biotico_fungico

**Qué hacer:** Evaluar la severidad y aplicar fungicida si corresponde. Los triazoles tienen acción sobre las principales enfermedades foliares del sorgo.

**Cómo confirmarlo en campo:** Buscar en las hojas del tercio medio y superior: manchas de forma oval o irregular de color rojizo a púrpura con centro gris (helmintosporiosis), o lesiones pequeñas de color rojo brillante (antracnosis foliar). En antracnosis avanzada el centro de la mancha puede mostrar masas de esporas anaranjadas.

### 9. R30 — Ataque de insectos en soja

- **Bloque:** insectos
- **Aplica a:** cultivo soja; estadios r1, r2, r3, r4, v4, v5, v6
- **Índices requeridos:** NDVI
- **Condición:** `NDVI < 0.50 Y patrón in {"manchas_irregulares", "focos_aislados"}`
- **Confianza:** media · **Causa:** estres_biotico_insecto

**Qué hacer:** Aplicar insecticida solo si el monitoreo en campo confirma que se supera el umbral de daño económico: para chinche ese umbral es 1 chinche adulta o 2 ninfas grandes por metro de fila; para oruga defoliadora es 30% de defoliación o 40 orugas por metro de fila en R1-R5.

**Cómo confirmarlo en campo:** Recorrer la zona afectada en zigzag. Para chinche: usar paño de batida (una tela blanca de 1 metro entre dos plantas) y sacudir la planta — contar chinches adultas y ninfas que caen. Para oruga defoliadora: revisar el porcentaje de hojas consumidas y buscar orugas en el suelo o en el follaje. Para trips o ácaro blanco en algodón: observar el envés de las hojas con lupa — tripas plateadas o deformación de hojas jóvenes.

### 10. R31 — Ataque de insectos en maíz y sorgo

- **Bloque:** insectos
- **Aplica a:** cultivo maiz, sorgo; estadios v6, v7, v8, v9, v10, v11, v12, vt
- **Índices requeridos:** NDVI
- **Condición:** `NDVI < 0.50 Y patrón in {"manchas_irregulares", "bordes_lote"}`
- **Confianza:** media · **Causa:** estres_biotico_insecto

**Qué hacer:** Monitorear en campo antes de aplicar. El umbral para chinche en maíz es variable según el momento — en VT-R1 el daño en el choclo es el más crítico.

**Cómo confirmarlo en campo:** Buscar en las plantas de la zona afectada: daño en las espigas de maíz o en la panoja de sorgo (insectos chupadores). Revisar el follaje por daño mecánico (hojas con agujeros irregulares = defoliadoras). Para barrenador del tallo: buscar aserrín en la base de las hojas o en el suelo alrededor de la planta. Sacudir la planta y observar si caen insectos.

### 11. R32 — Ataque de insectos en algodón

- **Bloque:** insectos
- **Aplica a:** cultivo algodon; estadios r1, r2, r3, boton_floral, floracion
- **Índices requeridos:** NDVI
- **Condición:** `NDVI < 0.50 Y patrón in {"manchas_irregulares", "focos_aislados", "circular"}`
- **Confianza:** media · **Causa:** estres_biotico_insecto

**Qué hacer:** Monitorear en campo para confirmar la presencia y nivel de infestación. Para oruga bellotero el umbral es 10% de daño visible en estructuras reproductivas.

**Cómo confirmarlo en campo:** Buscar en los botones florales y cápsulas: agujeros circulares de entrada de la oruga (bellotero). Los botones atacados suelen caerse al suelo — buscar botones caídos con agujero. Para trips: revisar con lupa el envés de las hojas más jóvenes — insectos minúsculos de 1-2 mm amarillentos o plateados, hojas con plateado en el envés y deformación. Para picudo: buscar en la base del botón floral un pequeño agujero de oviposición.

### 12. R40 — Déficit de nitrógeno en soja

- **Bloque:** nutricional
- **Aplica a:** cultivo soja; estadios r1, r2, v4, v5, v6
- **Índices requeridos:** NDRE
- **Condición:** `NDRE < 0.20 Y patrón in {"difuso_homogeneo", "por_sectores"}`
- **Confianza:** alta · **Causa:** estres_nutricional_nitrogeno

**Qué hacer:** Aplicar fertilizante nitrogenado. La forma de aplicación depende del estadio: foliar (urea al 2-3%) para correcciones rápidas en R1-R2, o granulado en suelo para estadios vegetativos donde aún puede incorporarse.

**Cómo confirmarlo en campo:** Observar las hojas en la zona afectada: las plantas con déficit de N tienen hojas más viejas (las del tercio inferior de la planta) amarillentas, mientras las hojas jóvenes del tope son más verdes. Esto es la clorosis por déficit de N (el N es móvil y la planta lo saca de las hojas viejas para alimentar las jóvenes). Extraer 2-3 plantas y comparar el color de las hojas del tercio inferior vs superior.

### 13. R41 — Déficit de nitrógeno en maíz y sorgo

- **Bloque:** nutricional
- **Aplica a:** cultivo maiz, sorgo; estadios v4, v5, v6, v7, v8
- **Índices requeridos:** NDRE
- **Condición:** `NDRE < 0.20 Y patrón in {"difuso_homogeneo", "por_sectores"}`
- **Confianza:** alta · **Causa:** estres_nutricional_nitrogeno

**Qué hacer:** Aplicar urea u otro fertilizante nitrogenado. En V4-V6 se puede aplicar en superficie o incorporado. La dosis depende del análisis de suelo y el rendimiento objetivo.

**Cómo confirmarlo en campo:** El síntoma clásico del déficit de N en maíz es el 'bandereo': la punta de las hojas más viejas (de la base de la planta) amarillea y ese amarillo avanza hacia la nervadura central formando una V invertida. En estadios avanzados las plantas parecen 'quemadas' de abajo hacia arriba. En sorgo el síntoma es similar pero menos marcado.

### 14. R42 — Déficit de nitrógeno en algodón

- **Bloque:** nutricional
- **Aplica a:** cultivo algodon; estadios v4, v5, v6, v7, v8
- **Índices requeridos:** NDRE
- **Condición:** `NDRE < 0.20 Y patrón in {"difuso_homogeneo", "por_sectores"}`
- **Confianza:** alta · **Causa:** estres_nutricional_nitrogeno

**Qué hacer:** Aplicar fertilizante nitrogenado. En algodón del NEA se usa principalmente urea. La aplicación en V4-V6 tiene alto impacto en el rendimiento.

**Cómo confirmarlo en campo:** Buscar hojas intermedias con coloración verde pálida o amarillenta, empezando por las hojas más viejas. El algodón con déficit de N también tiende a tener tallos más delgados y entrenudos más cortos. Las brácteas (hojas que rodean el botón floral) pueden ser más pequeñas de lo normal.

### 15. R43 — Déficit de micronutrientes (Mg, B)

- **Bloque:** nutricional
- **Aplica a:** cultivo todos; estadios todos
- **Índices requeridos:** NDRE
- **Condición:** `NDRE < 0.20 Y patrón in {"bordes_lote", "manchas_irregulares"}`
- **Confianza:** media · **Causa:** estres_nutricional_micro

**Qué hacer:** Aplicar fertilizante foliar de micronutrientes (sulfato de magnesio o boro soluble). Confirmar con muestra foliar antes de aplicar si es posible, ya que el costo del análisis foliar es bajo comparado con el de la aplicación innecesaria.

**Cómo confirmarlo en campo:** Para déficit de magnesio: buscar clorosis internerval en hojas intermedias — las nervaduras permanecen verdes mientras el tejido entre ellas amarillea (efecto mosaico o 'espina de pescado'). Se ve primero en hojas viejas porque el Mg es móvil. Para déficit de boro: buscar deformación de hojas jóvenes y brotes terminales, hojas arrugadas o en forma de copa, tallos quebradizos en prefloración de algodón. El boro NO es móvil, por lo que los síntomas aparecen en la parte nueva de la planta.

### 16. R44 — Déficit de fósforo

- **Bloque:** nutricional
- **Aplica a:** cultivo maiz, soja; estadios v1, v2, v3, v4, v5, v6
- **Índices requeridos:** NDVI, NDRE
- **Condición:** `NDVI < 0.50 Y NDRE < 0.20 Y patrón in {"por_sectores", "difuso_homogeneo"}`
- **Confianza:** media · **Causa:** estres_nutricional_fosforo

**Qué hacer:** La corrección efectiva del fósforo para el ciclo actual es limitada porque el P aplicado tardíamente tiene baja disponibilidad inmediata. La recomendación principal es documentar la zona para planificar la fertilización fosfatada en la siembra de la próxima campaña. Se puede aplicar fosfato monoamónico foliar como paliativo.

**Cómo confirmarlo en campo:** Buscar plantas con crecimiento retrasado comparado con el promedio del lote. La hoja más característica del déficit de P es la coloración rojiza o violácea en el envés de las hojas inferiores, especialmente en condiciones de baja temperatura. Las raíces de plantas con déficit de P son más cortas y menos ramificadas — arrancar 2-3 plantas y comparar el sistema radicular con plantas sanas.

### 17. R50 — Estrés hídrico generalizado

- **Bloque:** hidrico
- **Aplica a:** cultivo todos; estadios todos
- **Índices requeridos:** NDVI
- **Condición:** `NDVI < 0.50 Y patrón == "difuso_homogeneo"`
- **Confianza:** media · **Causa:** estres_hidrico

**Qué hacer:** No se aplica agroquímico. Verificar las precipitaciones de los últimos 10-15 días. Si no hubo lluvia suficiente y el cultivo está en estadio crítico (R1-R3 en soja, VT-R1 en maíz, floración en algodón), evaluar la posibilidad de riego. Si hay sistema de riego, activarlo prioritariamente en las zonas con mayor caída de NDVI.

**Cómo confirmarlo en campo:** Buscar en las plantas los síntomas clásicos de estrés hídrico: hojas enrolladas o curvadas hacia adentro (los bordes de la hoja se pliegan formando un tubo, mecanismo de defensa para reducir la transpiración), hojas con tonalidad azul-grisácea, plantas con turgencia reducida (se doblan o inclinan en horas de mayor calor). En soja: las hojas muestran un leve colgante en las horas más calientes del día. Presionar la hoja con los dedos — si no recupera su forma inmediatamente, hay pérdida de turgencia.

### 18. R60 — Madurez temprana diferencial en algodón

- **Bloque:** madurez
- **Aplica a:** cultivo algodon; estadios r4, r5, apertura_de_capsulas
- **Índices requeridos:** NDVI
- **Condición:** `NDVI < 0.25 Y NDVI < 0.40 * NDVI_promedio_lote Y patrón in {"focos_aislados", "manchas_irregulares"}`
- **Confianza:** media · **Causa:** madurez_temprana_diferencial

**Qué hacer:** Evaluar la aplicación de defoliante localizado solo en las zonas con madurez temprana para uniformizar la apertura de cápsulas y facilitar la cosecha mecanizada. Confirmar visualmente antes de aplicar. Los productos disponibles son Ethephon (acelerador de madurez) o la mezcla Tiidiazurón + Diurón (defoliante propiamente dicho).

**Cómo confirmarlo en campo:** Recorrer la zona identificada y contar el porcentaje de cápsulas abiertas vs cerradas. Si el 60-70% de las cápsulas están abiertas en esa zona mientras el resto del lote está en R3-R4, confirma madurez diferencial. Verificar también que no haya insectos o enfermedad que haya forzado la madurez prematura (buscar agujeros en cápsulas = oruga bellotero, o cápsulas ennegrecidas = enfermedad). La temperatura debe ser mayor a 18°C para que los defoliantes actúen correctamente.

### 19. R70 — Vigor excesivo en maíz

- **Bloque:** vigor
- **Aplica a:** cultivo maiz; estadios r1, vt
- **Índices requeridos:** NDVI
- **Condición:** `NDVI > 0.85 Y patrón == "difuso_homogeneo"`
- **Confianza:** baja · **Causa:** vigor_excesivo

**Qué hacer:** No se aplica ningún agroquímico. Es una alerta informativa para que el productor esté atento a las condiciones climáticas. Si se esperan tormentas con viento fuerte, considerar medidas preventivas como reducir la densidad de siembra para futuros ciclos.

**Cómo confirmarlo en campo:** No requiere confirmación de campo para esta regla. Si el productor observa plantas con tallos muy gruesos y hojas anchas que se superposician, el diagnóstico de alto vigor es correcto. Verificar el estado de los tallos — deben ser firmes, no huecos (un tallo hueco es señal de barrenador, no de vigor).

### 20. R99 — Sin problema detectado

- **Bloque:** cierre
- **Aplica a:** cultivo todos; estadios todos
- **Índices requeridos:** ninguno
- **Condición:** `True`
- **Confianza:** alta · **Causa:** sin_problema_detectado

**Qué hacer:** No se requiere ninguna intervención. La zona está dentro de los rangos normales para el cultivo y estadio fenológico registrado.

**Cómo confirmarlo en campo:** No requiere confirmación en campo. Si el productor tiene dudas, puede verificar visualmente que las plantas de esa zona se ven sanas, con buen color y tamaño normal para el estadio.

## Patrones espaciales (los clasifica `forma.py`, en este orden)

| Orden | Patrón | Cuándo |
|---|---|---|
| 1 | bordes_lote | la zona está a ≤ 30 m del borde del lote y ≥ 50% de su perímetro corre pegado a él |
| 2 | por_sectores | ocupa ≥ 15% del lote y llena ≥ 70% de su rectángulo mínimo |
| 3 | circular | circularidad ≥ 0.65 (4πA/P²) y elongación < 3.0 |
| 4 | lineal | elongación ≥ 3.0 (lado mayor / lado menor del rectángulo mínimo) |
| 5 | focos_aislados | área ≤ 2000 m² y ≥ 3 zonas de la misma clase |
| 6 | difuso_homogeneo | la clase completa cubre ≥ 30% del lote en ≤ 2 zonas |
| 7 | manchas_irregulares | todo lo demás |
