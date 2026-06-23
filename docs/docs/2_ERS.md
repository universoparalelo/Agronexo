1. #  **Introducción** {#introducción}

El presente documento describe los requisitos del sistema **AgroNexo**, una aplicación web orientada al soporte de decisiones en el ámbito de la agricultura de precisión, específicamente en tareas de fumigación. 

Este documento va a especificar los requisitos funcionales y no funcionales del sistema, definiendo su alcance, comportamiento esperado y restricciones, con el fin de servir como base para su desarrollo y validación.

## **1.1 Propósito** {#1.1-propósito}

El propósito de este documento es servir como base para el diseño, desarrollo y validación del sistema, así como también un medio de comunicación entre los distintos actores involucrados en el proyecto.

Asimismo, tiene como objetivo establecer un entendimiento común sobre el alcance del sistema, facilitando la planificación y asegurando que la solución desarrollada responda a las necesidades del usuario en el contexto de la fumigación en agricultura de precisión. 

## **1.2 Alcance** {#1.2-alcance}

El sistema consiste en una herramienta orientada al análisis de mapas multiespectrales para la detección de anomalías en cultivos, identificación de causas y la generación de recomendaciones de aplicación para la fumigación en un lote.

La plataforma permitirá procesar información geoespacial, interpretar índices de vegetación y traducirlos en diagnósticos comprensibles, junto con prescripciones de fumigación específicas para ser procesadas por otro sistema de un agente fumigador, y orden de trabajo con el detalle de la aplicación necesaria, como sea la dosis, el volumen y el área.

Su finalidad es mejorar la eficiencia en el uso de insumos, optimizar las decisiones agronómicas y reducir la dependencia de especialistas para la interpretación de datos técnicos, brindando una solución accesible especialmente para pequeños y medianos productores.

## **1.3 Personal involucrado**  {#1.3-personal-involucrado}

* **Equipo de desarrollo**: responsable del análisis, diseño, implementación, pruebas y documentación del sistema. Participa activamente en la definición y validación de los requisitos.  
* **Product Owner**: encargado de representar las necesidades del usuario final, priorizar los requisitos y validar que el sistema cumpla con los objetivos planteados.  
* **Usuarios finales (productores agrícolas y prestadores de servicios)**: aportan información del dominio, validan la utilidad de las funcionalidades y serán los principales beneficiarios del sistema.  
* **Docente / evaluador académico**: responsable de supervisar el desarrollo del proyecto, validar el cumplimiento de los objetivos académicos y brindar retroalimentación durante el proceso.

## **1.4 Definiciones, acrónimos y abreviaturas** {#1.4-definiciones,-acrónimos-y-abreviaturas}

* **ERS**: Especificación de Requisitos de Software.  
* **RF**: Requisito Funcional.  
* **RNF**: Requisito No Funcional.  
* **NDVI**: Índice de Vegetación de Diferencia Normalizada.  
* **NDRE**: Índice de Vegetación de Borde Rojo.  
* **GeoTIFF**: Formato de archivo raster georreferenciado.  
* **API**: Interfaz de Programación de Aplicaciones.  
* **MVP**: Producto Mínimo Viable.  
* **IA**: Inteligencia Artificial.  
* **Ortomosaico**: Imagen compuesta georreferenciada generada a partir de múltiples capturas aéreas.

## **1.5 Referencias** {#1.5-referencias}

Se listan todas las fuentes o recursos que se utilizaron para justificar las decisiones que se tomaron para el sistema:

* IEEE. *IEEE 830-1998 – Recommended Practice for Software Requirements Specifications*.  
* Documentación oficial de **GDAL (Geospatial Data Abstraction Library)**.  
* Documentación oficial de **Rasterio**.  
* Documentación oficial de **GeoPandas** y **Shapely**.  
* Documentación oficial de **NumPy**.  
* DJI. *Especificaciones técnicas del drone DJI Mavic 3 Multispectral*.  
* Concepto de índice NDVI: Rouse, J.W. et al. (1974). *Monitoring Vegetation Systems in the Great Plains with ERTS*.  
* FAO. *Agricultura de precisión y uso eficiente de insumos agrícolas*.

## **1.6 Resumen** {#1.6-resumen}

En el contexto de la agricultura de precisión, el uso de drones con sensores multiespectrales permite obtener información detallada sobre el estado de los cultivos. Sin embargo, las herramientas actuales presentan limitaciones en la interpretación de estos datos, ya que suelen expresarse en términos técnicos que requieren conocimientos especializados, generando dependencia de expertos y dificultando su adopción por parte de productores.

Además, las soluciones existentes tienden a generar recomendaciones automáticas sin una justificación clara del criterio utilizado, lo que puede derivar en decisiones poco confiables o en el uso ineficiente de insumos, como fumigaciones generalizadas innecesarias.

En respuesta a esta problemática, el sistema propuesto busca convertirse en una herramienta integral de soporte a la decisión, capaz de analizar imágenes multiespectrales, identificar zonas con comportamiento anómalo y traducir dicha información en diagnósticos claros y accionables.

La solución no solo permitirá delimitar áreas específicas que requieren intervención, sino también explicar las posibles causas del problema y generar recomendaciones fundamentadas sobre la fumigación, promoviendo una aplicación más eficiente, localizada y sustentable de productos fitosanitarios.

De este modo, el sistema apunta a reducir costos, mejorar la productividad y disminuir el impacto ambiental, facilitando al mismo tiempo la toma de decisiones mediante información clara, accesible y respaldada.

# **2\. 	Descripción general**  {#2.-descripción-general}

## **2.1 Perspectiva del producto**   {#2.1-perspectiva-del-producto}

El sistema propuesto es una aplicación orientada al soporte de decisiones en el ámbito de la agricultura de precisión. Se concibe como una solución independiente que procesa información proveniente de imágenes multiespectrales capturadas por drones, con el objetivo de generar diagnósticos y recomendaciones de fumigación.

Desde el punto de vista tecnológico, el sistema estará compuesto por un backend encargado del procesamiento geoespacial y análisis de datos (utilizando herramientas como procesamiento raster y librerías científicas), y un frontend que permitirá la interacción con el usuario mediante una interfaz clara e intuitiva.

El sistema integrará procesamiento de archivos geoespaciales (GeoTIFF), cálculo de índices de vegetación (como NDVI y NDRE), segmentación de zonas y generación de salidas interpretables. Además, podrá interactuar con dispositivos o plataformas externas utilizadas en agricultura de precisión, como drones y sistemas de aplicación variable.

Se concibe como un producto escalable, capaz de adaptarse a diferentes cultivos, regiones y contextos productivos, con foco en traducir información técnica compleja en conocimiento útil para la toma de decisiones.

## **2.2  Funcionalidades del producto**   {#2.2-funcionalidades-del-producto}

El sistema proporcionará las siguientes funcionalidades principales:

* **Carga de datos del lote**: permite ingresar información relevante como tipo de cultivo, fechas, características del suelo y delimitación del área.  
* **Carga y validación de ortomosaicos**: permite subir archivos multiespectrales (GeoTIFF) y verificar su integridad, resolución y georreferenciación.  
* **Procesamiento de imágenes**: cálculo de índices de vegetación (NDVI, NDRE, entre otros) mediante operaciones sobre los datos raster.  
* **Segmentación de zonas**: identificación y delimitación de áreas con comportamientos anómalos dentro del cultivo.  
* **Análisis e interpretación**: traducción de datos técnicos en diagnósticos comprensibles, indicando posibles causas de los problemas detectados.  
* **Generación de recomendaciones**: elaboración de sugerencias de intervención, indicando dónde, cómo y en qué medida realizar la fumigación.  
* **Generación de prescripciones**: creación de archivos compatibles con maquinaria agrícola para ejecutar aplicaciones variables.  
* **Emisión de informes**: generación de reportes que incluyan mapas, diagnósticos, recomendaciones y criterios de decisión.  
* **Carga de imágenes complementarias (opcional)**: permite incorporar fotos RGB para validar o reforzar el diagnóstico.

## **2.3 Características de los usuarios**   {#2.3-características-de-los-usuarios}

**Tipo de usuario: Productor agrícola**  
**Actividades:**  
Puede cargar datos de sus lotes, subir imágenes multiespectrales, visualizar diagnósticos, interpretar resultados y aplicar las recomendaciones generadas por el sistema para optimizar sus decisiones de fumigación.

**Tipo de usuario: Prestador de servicios agrícolas**  
**Actividades:**  
Tiene la capacidad de analizar múltiples lotes, generar informes profesionales para clientes, validar diagnósticos mediante imágenes adicionales y exportar prescripciones para maquinaria o drones de fumigación.

## **2.4 Restricciones**   {#2.4-restricciones}

* El sistema depende de la calidad y resolución de las imágenes multiespectrales proporcionadas; datos deficientes pueden afectar la precisión del análisis.  
* El procesamiento de grandes volúmenes de datos geoespaciales puede requerir recursos computacionales elevados.  
* La precisión de los diagnósticos está condicionada por la correcta calibración de los índices de vegetación según cultivo, región y estadio fenológico.  
* La compatibilidad con maquinaria agrícola dependerá de los formatos de salida soportados por cada equipo.

## **2.5 Suposiciones y dependencias**   {#2.5-suposiciones-y-dependencias}

* **Disponibilidad de imágenes multiespectrales:** se asume que los usuarios contarán con acceso a drones o servicios que generen ortomosaicos de calidad.  
* **Conectividad a internet:** se supone que el usuario tendrá acceso a conexión para cargar archivos, procesarlos y visualizar resultados.  
* **Conocimiento básico del dominio:** se asume que los usuarios poseen conocimientos básicos de agricultura que les permitan interpretar recomendaciones.  
* **Dependencia de herramientas externas:** el sistema se apoya en librerías y herramientas de procesamiento geoespacial (como GDAL, Rasterio, NumPy), cuyo funcionamiento impacta directamente en el sistema.  
* **Disponibilidad de hardware adecuado:** el procesamiento eficiente puede depender de servidores o infraestructura con capacidad suficiente para manejar archivos de gran tamaño.

## **2.6 Evolución previsible del sistema**   {#2.6-evolución-previsible-del-sistema}

En futuras versiones, el sistema podrá evolucionar incorporando nuevas capacidades:

* Integración de modelos de **inteligencia artificial** para mejorar la precisión de los diagnósticos y automatizar la detección de patrones complejos.  
* Adaptación a distintos tipos de cultivos y regiones mediante calibración automática de índices y umbrales.  
* Desarrollo de una versión instalable (PWA) que permita acceder al sistema desde cualquier dispositivo (computadora, tablet o celular) y consultar resultados, diagnósticos y órdenes de trabajo sin conexión a internet.  
* Integración directa con maquinaria agrícola o drones para ejecutar prescripciones en tiempo real.  
* Inclusión de históricos y analítica avanzada para comparar campañas y mejorar la toma de decisiones a largo plazo.  
* Desarrollo de funcionalidades colaborativas que permitan compartir informes entre productores, técnicos y asesores.

# **3\. 	Requisitos**   {#3.-requisitos}

## **3.1 Requisitos funcionales** {#3.1-requisitos-funcionales}

### **1\. Requisitos de entrada y validación** {#1.-requisitos-de-entrada-y-validación}

*Se enfocan en asegurar que la materia prima (datos) sea de calidad.*

| ID | Nombre | Descripción |
| :---: | :---: | ----- |
| **RFME-01** | Carga de archivos ráster | El sistema debe permitir la carga de archivos ráster en formato GeoTIFF. |
| **RFME-02** | Validación de metadatos | El sistema debe verificar que el archivo contenga bandas espectrales válidas (RGB/NIR) y un Sistema de Referencia de Coordenadas (CRS) definido. |
| **RFME-03** | Registro de contexto agrológico | El sistema debe permitir el ingreso de datos del lote: tipo de cultivo, etapa fenológica, fecha de vuelo y condiciones climáticas. |
| **RFME-04** | Visualización de integridad | El sistema debe generar una vista previa rápida (low-res) del área de cobertura para confirmar la carga correcta antes del procesamiento. |
| **RFME-05** | Seguimiento de procesamiento | El sistema debe mostrar al usuario el estado  y progreso de cada análisis en curso, indicando la etapa actual y el porcentaje de avance. |

### **2\. Requisitos de análisis y procesamiento** {#2.-requisitos-de-análisis-y-procesamiento}

*Aquí es donde transformamos píxeles en información agronómica.*

| ID | Nombre | Descripción |
| :---: | :---: | :---- |
| **RFMA-01** | Procesamiento de índices | El sistema debe permitir la selección y cálculo de índices de vegetación (NDVI, NDRE, SAVI, ExG) según las bandas disponibles en el archivo cargado. |
| **RFMA-02** | Umbralización dinámica | El sistema debe definir rangos de valores para segmentar el índice calculado en categorías de vigor o presencia de anomalías. |
| **RFMA-03** | Calibración de umbrales | El sistema debe ofrecer herramientas para el ajuste manual o automático (ej. método de Otsu) de los puntos de corte del análisis. |
| **RFMA-04** | Detección de anomalías | El sistema debe identificar áreas con valores atípicos que sugieran estrés hídrico, nutricional o presencia de plagas. |

### **3\. Requisitos de procesamiento geoespacial y vectorización** {#3.-requisitos-de-procesamiento-geoespacial-y-vectorización}

| ID | Nombre | Descripción |
| :---: | :---: | ----- |
| **RFMP-01** | Reproyección cartográfica | El sistema debe permitir transformar las coordenadas del análisis al sistema local requerido por la aplicación (ej. UTM). |
| **RFMP-02** | Extracción de geometrías | El sistema debe convertir las áreas clasificadas en objetos vectoriales (polígonos) manteniendo la georreferenciación. |
| **RFMP-03** | Generalización de datos | El sistema debe permitir la simplificación de polígonos para reducir la densidad de vértices sin perder la precisión de la zona de aplicación. |
| **RFMP-04** | Filtrado de ruido | El sistema debe permitir eliminar polígonos menores a un área mínima definida (puntos de ruido que la maquinaria no puede procesar). |
| **RFMP-05** | Persistencia de datos | El sistema debe garantizar el almacenamiento seguro de los archivos fuente, resultados intermedios y vectores finales. |

### **4\. Requisitos de diagnóstico, recomendación y prescripción** {#4.-requisitos-de-diagnóstico,-recomendación-y-prescripción}

*La capa de inteligencia que asiste.*

| ID | Nombre | Descripción |
| :---: | :---: | ----- |
| **RFDR-01** | Motor de reglas | El sistema debe aplicar lógica de negocio para asociar niveles de índice con acciones recomendadas (ej. dosis variable). |
| **RFDR-02** | Zonificación de manejo | El sistema debe agrupar áreas contiguas con necesidades similares en unidades de gestión diferenciadas. |
| **RFDR-03** | Estimación de severidad | El sistema debe cuantificar el grado de afectación o desarrollo de cada zona identificada en comparación con el lote promedio. |
| **RFDR-04** | Registro de criterio técnico | El sistema debe permitir al profesional adjuntar una justificación o comentario técnico a cada diagnóstico generado. |
| **RFDR-05** | Trazabilidad de vuelo | El sistema debe vincular cada diagnóstico con el identificador del vuelo y el lote histórico correspondiente. |

### **5\. Requisitos de gestión del lote** {#5.-requisitos-de-gestión-del-lote}

*Administración de la cuenta y los activos del cliente.*

| ID | Nombre | Descripción |
| :---: | :---: | ----- |
| **RFGL-01** | Multi-tenencia de datos | El sistema debe aislar la información por usuario y cliente, garantizando la privacidad de los datos de cada prestador. |
| **RFGL-02** | Inventario de lotes | El sistema debe permitir la creación de un inventario de lotes con sus límites geográficos históricos. |
| **RFGL-03** | Historial de intervenciones | El sistema debe mantener y mostrar al usuario una línea de tiempo por lote que relacione vuelos, análisis realizados (con fecha, índice utilizado, estado y resultados) y diagnósticos generados. |
| **RFGL-04** | Gestión de capas | El sistema debe permitir la superposición de diferentes análisis realizados sobre un mismo lote en distintas fechas. |
| **RFGL-05** | Análisis de eficiencia | El sistema debe calcular la diferencia entre el área total del lote y el área prescrita para determinar el ahorro de insumos. |
| **RFGL-06** | Gestión de datos | El sistema debe permitir al usuario eliminar lotes, vuelos o análisis propios que ya no necesite.  |

### **6\. Requisitos de salida** {#6.-requisitos-de-salida}

*Los entregables finales del sistema.*

| ID | Nombre | Descripción |
| :---: | :---: | ----- |
| **RFSA-01** | Visualización de resultados | El sistema debe presentar los resultados del análisis en un dashboard interactivo que incluya: mapa con zonas clasificadas, estadísticas por zona (área, índice promedio, severidad), diagnóstico y recomendaciones, y cálculo de ahorro de insumos. |
| **RFSA-02** | Exportación de prescripción | El sistema debe permitir descargar los polígonos de prescripción en formatos compatibles con maquinaria agrícola (Shapefile, GeoJSON). |
| **RFSA-03** | Reporte ejecutivo descargable | El sistema debe permitir generar y descargar un reporte ejecutivo en formato PDF que resuma el análisis: mapas, estadísticas, diagnóstico y recomendaciones. El mismo contenido visible en el dashboard debe poder exportarse como documento imprimible. |
| **RFSA-04** | Orden de trabajo | El sistema debe permitir generar y descargar una orden de trabajo con dosis por zona, restricciones ambientales e instrucciones de seguridad, en formato descargable o imprimible desde el dashboard. |

## **3.2 Requisitos no funcionales** {#3.2-requisitos-no-funcionales}

### **1\. Rendimiento** {#1.-rendimiento}

*Define los tiempos de respuesta y capacidad de procesamiento esperados.*

| ID | Nombre | Descripción |
| :---: | :---: | :---- |
| **RNF-01** | Tiempo de carga de interfaz | Las páginas de la interfaz web deben cargar en menos de 3 segundos bajo condiciones normales de conectividad. |
| **RNF-02** | Tiempo de procesamiento de ortomosaico | El sistema debe completar el procesamiento de un archivo GeoTIFF estándar (hasta 500 MB) en un tiempo máximo de 5 minutos. |
| **RNF-03** | Tiempo de generación de resultados | El diagnóstico, la segmentación de zonas y las recomendaciones deben estar disponibles en menos de 2 minutos tras finalizar el procesamiento. |
| **RNF-04** | Retroalimentación en tiempo real | El sistema debe informar el progreso del procesamiento mediante indicadores visuales actualizados al menos cada 10 segundos. |

### **2\. Seguridad**  {#2.-seguridad}

*Establece los mecanismos de protección de datos y acceso al sistema.*

| ID | Nombre | Descripción |
| :---: | :---: | :---- |
| **RNF-05** | Autenticación de usuarios | El sistema debe requerir autenticación mediante usuario y contraseña para acceder a cualquier funcionalidad. |
| **RNF-06** | Control de acceso | Cada usuario solo podrá acceder a los datos y lotes que le pertenecen, sin posibilidad de visualizar información de otros usuarios. |
| **RNF-07** | Cifrado de comunicaciones | Todas las comunicaciones entre el cliente y el servidor deben realizarse mediante HTTPS (TLS 1.2 o superior) en el entorno de producción. En el entorno de desarrollo local se permite el uso de HTTP. |
| **RNF-08** | Validación de entradas | El sistema debe validar y sanitizar todos los datos ingresados por el usuario para prevenir inyecciones y ataques de tipo XSS. |
| **RNF-09** | Gestión de sesiones | Las sesiones inactivas deben expirar automáticamente tras 30 minutos sin actividad. |

### **3\. Usabilidad** {#3.-usabilidad}

*Define los atributos que hacen al sistema accesible y comprensible para sus usuarios.*

| ID | Nombre | Descripción |
| :---: | :---: | :---- |
| **RNF-10** | Curva de aprendizaje | Un usuario con conocimientos básicos de agricultura debe poder realizar el flujo completo de análisis sin requerir capacitación previa. |
| **RNF-11** | Mensajes de error comprensibles | Ante errores o condiciones inválidas, el sistema debe mostrar mensajes descriptivos en lenguaje no técnico que orienten al usuario sobre cómo proceder. |
| **RNF-12** | Consistencia de la interfaz | La interfaz debe mantener una estructura visual y de navegación consistente en todas las secciones del sistema. |
| **RNF-13** | Accesibilidad básica | La interfaz debe ser utilizable desde teclado y cumplir con los criterios mínimos de contraste y legibilidad. |

### **4\. Disponibilidad** {#4.-disponibilidad}

*Define los criterios de uptime y recuperación ante fallos.*

| ID | Nombre | Descripción |
| :---: | :---: | :---- |
| **RNF-14** | Disponibilidad del sistema | El sistema debe estar disponible al menos el 95% del tiempo durante el período de campaña agrícola (septiembre a abril). |
| **RNF-15** | Recuperación ante fallos | Ante una interrupción inesperada del procesamiento, el sistema debe conservar los datos ya ingresados y permitir reiniciar desde el último estado válido. |
| **RNF-16** | Manejo de errores del sistema | El sistema no debe caerse de forma irrecuperable ante errores individuales; los fallos deben quedar registrados para su diagnóstico posterior. |

### **5\. Escalabilidad** {#5.-escalabilidad}

*Define la capacidad del sistema para crecer en carga y volumen.*

| ID | Nombre | Descripción |
| :---: | :---: | :---- |
| **RNF-17** | Soporte de archivos de gran tamaño | El sistema debe ser capaz de procesar archivos GeoTIFF de hasta 1 GB sin degradación significativa del rendimiento. |
| **RNF-18** | Usuarios concurrentes | El sistema debe soportar al menos 10 usuarios concurrentes realizando operaciones de carga y procesamiento simultáneamente. |
| **RNF-19** | Procesamiento de múltiples lotes | Un prestador de servicios debe poder gestionar hasta 50 lotes distintos dentro de la misma sesión sin pérdida de datos. |

### **6\. Portabilidad** {#6.-portabilidad}

*Define la compatibilidad del sistema con distintos entornos de uso.*

| ID | Nombre | Descripción |
| :---: | :---: | :---- |
| **RNF-20** | Compatibilidad con navegadores | El sistema debe funcionar correctamente en las versiones actuales de Google Chrome, Mozilla Firefox y Microsoft Edge. |
| **RNF-21** | Diseño responsivo | La interfaz debe adaptarse correctamente a distintas resoluciones de pantalla, siendo usable en computadoras de escritorio y tablets. |
| **RNF-22** | Independencia del sistema operativo | El sistema debe ser accesible desde Windows, macOS y Linux sin requerir instalación de software adicional en el cliente. |

### **7\. Mantenibilidad** {#7.-mantenibilidad}

*Define los atributos que facilitan el mantenimiento y evolución del sistema.*

| ID | Nombre | Descripción |
| :---: | :---: | :---- |
| **RNF-23** | Arquitectura modular | El sistema debe estar estructurado de forma modular, de modo que los componentes de procesamiento geoespacial, análisis y presentación puedan modificarse de forma independiente. |
| **RNF-24** | Documentación técnica | El código fuente debe incluir documentación suficiente para que un desarrollador externo pueda comprender, mantener y extender el sistema. |
| **RNF-25** | Registro de actividad (logs) | El sistema debe registrar las operaciones relevantes (cargas, procesamientos, errores) con marca de tiempo para facilitar el diagnóstico de problemas. |

### **8\. Interoperabilidad** {#8.-interoperabilidad}

*Define la capacidad del sistema para integrarse con herramientas y formatos del dominio agrícola.*

| ID | Nombre | Descripción |
| :---: | :---: | :---- |
| **RNF-26** | Formatos de exportación estándar | Las prescripciones generadas deben exportarse en formatos compatibles con maquinaria agrícola de aplicación variable (shapefile, GeoJSON o similares). |
| **RNF-27** | Compatibilidad con sistemas de referencia de coordenadas | El sistema debe aceptar archivos con distintos CRS y realizar las transformaciones necesarias de forma transparente para el usuario. |
| **RNF-28** | Compatibilidad con datos de distintos sensores | El sistema debe procesar archivos GeoTIFF provenientes de distintos modelos de drones multiespectrales, siempre que contengan las bandas requeridas. |

