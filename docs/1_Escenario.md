# **Problemática** {#problemática}

En el contexto de la agricultura de precisión, el uso de drones con sensores multiespectrales permite obtener información detallada sobre el estado de los cultivos. A partir de estas imágenes, es posible generar mapas que faciliten la detección temprana de anomalías como estrés vegetal, plagas o enfermedades. Esta información resulta especialmente relevante para la toma de decisiones vinculadas a la fumigación y aplicación de productos fitosanitarios.

Aunque existen herramientas tecnológicas que automatizan el procesamiento de imágenes y generan mapas e incluso prescripciones de aplicación, estas soluciones presentan limitaciones en cuanto a la interpretación y utilización práctica de la información en contextos reales de fumigación.

En la práctica, estos sistemas suelen presentar los resultados en términos técnicos (índices de vegetación, mapas por rangos, valores numéricos), cuya comprensión requiere conocimientos específicos en agronomía o teledetección. Esto genera una dependencia de especialistas para interpretar los datos y traducirlos en decisiones concretas, lo cual no siempre es accesible para pequeños y medianos productores.

Además, las prescripciones automáticas existentes tienden a simplificar el análisis, transformando directamente los valores de los mapas en recomendaciones de aplicación (por ejemplo, dosis de insumos por hectárea), sin brindar una explicación clara del origen del problema ni del criterio utilizado para la decisión. Esto puede generar desconfianza o un uso ineficiente de los recursos, como la aplicación innecesaria o generalizada de productos fitosanitarios.

## **Situaciones reales** {#situaciones-reales}

**Caso 1 - Fumigación general**
### Tratamiento 1

**Campo-Lote:** DA 02+05+06
**Superficie:** 263
**Contratista:** Terrestre

| Producto         | Dosis | Uni | Total |
|------------------|-------|-----|-------|
| A35T gold        | 0,114 | Lts | 30    |
| 2,4D ethil exil  | 0,684 | Lts | 180   |
| Prometrina       | 1,141 | Lts | 300   |
| Haloxifop 54%    | 0,190 | Lts | 50    |
| Bifentrin 25%    | 0,190 | Lts | 50    |
| R. Top           | 1,825 | Lts | 480   |

Lo que muestra esta receta es que se van a aplicar 6 productos distintos sobre 263 hectáreas de forma general, **todo el campo lote DA 02+05+06 recibe la misma dosis de todo.** No hay distinción de zonas, no hay criterio espacial, no hay justificación de por qué 263 hectáreas enteras necesitan exactamente 0.114 litros de A35T gold por hectárea en cada rincón del lote.

**Problema: Uso ineficiente de producto**  
**Solución: Prescripción de aplicación selectiva**

**Caso 2 - Árboles que bloquean acceso**

En el Chaco es muy común tener lotes agrícolas con árboles dispersos (quebrachos, algarrobos, palos verdes) que quedaron del monte original. Las copas de esos árboles crean sombra sobre el cultivo, y lo problemático para la fumigación: el equipo no puede pasar por debajo ni el drone de fumigación puede llegar al cultivo tapado por las copas.

**Problema: Árboles que impiden la fumigación**  
**Solución: Prescripción de defoliante solo sobre las copas**

# **Solución**  {#solución}

En este contexto, determinamos la oportunidad de desarrollar una herramienta de soporte a la decisión, la cual a partir del análisis de imágenes multiespectrales, permita identificar y delimitar zonas que requieren intervención, interpretar de manera comprensible las posibles causas del problema y generar recomendaciones claras y justificadas sobre la fumigación, promoviendo una aplicación más eficiente, localizada y sustentable de los productos fitosanitarios.

## **Impacto esperado** {#impacto-esperado}

* **Económico**: Reducción en el uso de insumos al evitar fumigaciones generales innecesarias.
* **Productivo**: Mejora en la eficiencia de las intervenciones al actuar de forma precisa sobre zonas afectadas.
* **Ambiental**: Disminución del impacto ambiental mediante la reducción del uso excesivo de agroquímicos.
* **Operativo**: Agilización en la toma de decisiones, reduciendo la dependencia de interpretaciones externas, y tener un informe respaldado y justificado.

## **Público objetivo** {#público-objetivo}

* **Productores agrícolas**, especialmente pequeños y medianos, que realizan tareas de fumigación por cuenta propia y no cuentan con asesoramiento técnico constante.
* **Prestadores de servicios agrícolas** que necesitan generar informes claros y profesionales para sus clientes.

## **Alcance** {#alcance}

* **Análisis de mapas multiespectrales** para la identificación de zonas con comportamientos anómalos dentro del terreno.
* **Interpretación de datos técnicos**, traduciéndolos en información comprensible que permita evaluar el estado de los cultivos e identificar posibles problemas y sus causas.
* **Generación de recomendaciones de intervención**, definiendo de manera clara y fundamentada dónde y en qué medida realizar fumigaciones para optimizar su eficiencia.

# **Descripción del proyecto** {#descripción-del-proyecto}

**Tipo de app**

Sistema de soporte a la decisión para fumigación en agricultura de precisión, basada en el análisis e interpretación de imágenes multiespectrales.

## **Flujo del Sistema** {#flujo-del-sistema}

Acá describimos de forma general el flujo que ahora consideramos llevar a cabo, teniendo

**Entradas:**

* Datos del lote

  * Tipo de cultivo
  * Fecha de vuelo y estadio fenológico
  * Fecha de siembra
  * Datos del suelo
  * Área del lote / polígono
* Archivo espacial Ortomosaico:  Conjunto de imágenes multiespectrales que utilizaremos para analizar el cultivo
* Input opcional: 2 o 3 fotos RGB de zonas problemáticas para confirmación visual del diagnóstico.

**Proceso:**

* Validación y Análisis de mapa

  * Validación del archivo: Coordenadas, resolución espacial.
  * Enmascarado de bordes y zonas sin cobertura
  * Cálculo de índices según bandas disponibles: NDVI (NIR + RED), NDRE (NIR + Red Edge), SAVI (corrección por suelo expuesto), ExGreen (RGB, para detección de malezas)
  * Clasificación por umbrales para detección de malezas.
* Conversión y segmentación

  * Vectorización del raster clasificado: conversión de zonas de píxeles a polígonos georeferenciados
  * Simplificación de geometrías y filtrado por área mínima para eliminar ruido
  * Cálculo de área exacta en hectáreas por zona
  * Detección de vegetación de copa alta (árboles dispersos) por patrón circular y NDVI elevado
* Diagnóstico e interpretación

  * Análisis del patrón espacial de cada zona problemática
  * Cruce con contexto del lote: cultivo, estadio fenológico, historial de intervenciones
  * Generación de un diagnóstico explicado en lenguaje accesible para el productor, con las causas probables según el contexto del lote (motor de reglas); la redacción en lenguaje natural puede enriquecerse posteriormente con una capa generativa de IA
  * Validación en campo: el usuario confirma la causa antes de prescribir
  * Identificación explícita de zonas sin intervención necesaria

**Salida**

* Informe con datos del lote, mapa de zonas con leyenda, diagnóstico interpretado, prescripción por zona con criterio justificado y cálculo de ahorro vs. aplicación general
* Prescripción: Conjunto de archivos (shapefile) que dan información de polígonos con atributos exportables para uso en sistemas externos
* Orden de trabajo: instrucciones al equipo fumigador, producto recomendado, dosis por hectárea y volumen total por zona

# **Comparaciones del mercado: ventaja competitiva** {#comparaciones-del-mercado:-ventaja-competitiva}

**1. Agremo**

Plataforma de análisis de imágenes multiespectrales por dron. Genera mapas de prescripción para fumigación de precisión (spot spraying y VRA). Usa IA, machine learning y visión artificial. Compatible con drones DJI, XAG, TopXgun y EAvision.

* Competidor más directo de Agro Nexo.
* Solo en inglés, orientado a empresas agrícolas grandes.
* Procesamiento de hasta 2 días hábiles. Pricing no transparente.
* No se adapta a cultivos del NEA (algodón, soja chaqueña, girasol, sorgo).
* Genera prescripciones pero no explica el criterio detrás de cada zona.

2\. PIX4Dfields

Software suizo de fotogrametría agrícola. Procesa imágenes de dron y satélite para generar mapas NDVI, prescripciones VRA y detección de malezas. Funciona offline. Compatible con John Deere, DJI, XAG.

* Técnicamente muy fuerte en procesamiento de mapas.
* Pensado para el profesional técnico, no para el productor sin conocimientos de fotogrametría.
* Requiere hardware específico y curva de aprendizaje alta.
* Sin adaptación a cultivos ni condiciones agroclimáticas del NEA.

3\. SMARTSCRIPT (Sentera — adquirida por John Deere)

Detección de malezas por dron con IA. Genera scripts de fumigación listos para pulverizadores de precisión en menos de 24 hs. En 2025 incorporó clasificación por especie y conteo de plantas.

* Técnicamente el más avanzado en detección de malezas.
* Solo disponible en EE.UU. (Corn Belt). No opera en Argentina ni Latinoamérica.
* Requiere hardware propio de Sentera. No es una plataforma abierta.
* Integrado al ecosistema John Deere — inaccesible para productores chicos del NEA.

4\. Taranis

Detección a nivel hoja con resolución submilimétrica (3/10 mm por acre). Entrenada con más de 500 millones de datos. Detecta enfermedades, plagas, deficiencias nutricionales y malezas. Motor de IA generativo llamado Ag Assistant.

* El más avanzado en diagnóstico agronómico detallado.
* Orientado al asesor agronómico profesional, no al productor directo.
* Solo en inglés. Presencia limitada en Sudamérica.
* Precio enterprise no publicado.
* Ellos hacen los vuelos, no es una plataforma abierta.

**Ventajas competitivas de Agro Nexo**

Frente a todos los competidores analizados, Agro Nexo puede diferenciarse en tres ejes concretos:

* **Idioma y contexto local**: plataforma en español adaptada a cultivos del NEA/Pampa húmeda (algodón, soja chaqueña, girasol, sorgo).
* **Explicabilidad**: no solo decir dónde y cuánto aplicar, sino explicar el por qué en lenguaje accesible para el productor.
* **Foco en el productor pequeño/mediano sin asesor permanente**: ningún competidor prioriza este segmento.

# **Metodología a utilizar** {#metodología-a-utilizar}

Para  organizarnos utilizaremos la metodología Scrum para gestionar el desarrollo del proyecto de manera ágil y colaborativa. El trabajo se estructurará en ciclos iterativos de tres semanas (sprints), en los cuales se planificará, desarrollará y revisará un conjunto definido de tareas.

Durante cada sprint, se llevarán a cabo reuniones semanales de seguimiento con el objetivo de analizar el progreso alcanzado, identificar posibles obstáculos y definir las próximas tareas a abordar. Esto permitirá mantener una comunicación constante dentro del equipo y asegurar la alineación con los objetivos del proyecto.

Además, se establecerá un Definition of Done (DoD) claro, que determinará los criterios que debe cumplir cada funcionalidad para considerarse finalizada. Como parte de este proceso, al menos dos integrantes del equipo deberán verificar y validar que la implementación sea correcta, asegurando así la calidad del trabajo entregado.

Este enfoque nos permitirá adaptarnos a cambios, mejorar continuamente y garantizar entregas incrementales de valor a lo largo del proyecto.

