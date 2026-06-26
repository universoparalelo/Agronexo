# Release 1



# Sprint 1



# Cálculo y validación NDVI/GNDVI/SAVI

Análisis de índices vegetativos. Revisión de umbrales agronómicos para soja en el NEA.

## Bibliografía

[Tema Indices de vegetación.pdf](https://t90171211803.p.clickup-attachments.com/t90171211803/0f24d626-a9e2-47ab-96b2-a8cf25e43fc3/Tema%20Indices%20de%20vegetaci%C3%B3n%2C%20Pedro%20Mu%C3%B1oz%20A.pdf)

[https://eos.com/es/blog/ndvi-preguntas-frecuentes/](https://eos.com/es/blog/ndvi-preguntas-frecuentes/)
[https://eos.com/es/blog/indices-de-vegetacion/](https://eos.com/es/blog/indices-de-vegetacion/)

## 1\. Introducción: Los Índices Espectrales como Variables de Software
Para un programador, una imagen satelital es un archivo raster (como un `.tiff`) con múltiples capas o bandas. Un Índice de Vegetación (IV) no es más que una función matemática que toma los valores de esas bandas en un píxel y devuelve un único valor flotante.

Imagina los índices como los sensores de un tablero de control:
*   Nos dicen si el motor está funcionando (si hay actividad fotosintética).
*   Miden el nivel de combustible hídrico (humedad del suelo o del dosel).
*   Actúan como un "escáner de diagnóstico" a kilómetros de distancia, ahorrando el costo de enviar drones o inspectores a revisar manualmente cada hectárea.
## 2\. Fundamentos Físicos: El "Secreto" Óptico de las Plantas
Para que nuestro algoritmo distinga un cultivo de la tierra seca o del asfalto, aprovecha la forma en que las plantas interactúan con la radiación solar:

*   **La Banda Roja (RED):** Es la fuente de energía de la planta. La clorofila absorbe esta luz para hacer fotosíntesis. En tu código: Planta sana = Valor RED muy bajo.
*   **El Infrarrojo Cercano (NIR):** No es visible para los humanos, pero las hojas sanas lo reflejan como un espejo debido a su estructura celular interna. En tu código: Planta sana = Valor NIR extremadamente alto.
*   **El Borde Rojo (RED EDGE):** Es una delgada zona de transición. Si la planta se enferma o pierde nitrógeno, sus hojas se vuelven amarillas y esta zona sufre un desplazamiento óptico inmediato. Planta sana = Valor RED EDGE alto
*   **El Infrarrojo de Onda Corta (SWIR)**: Es el sensor de agua. Es altamente absorbido por el líquido; si el cultivo sufre estrés hídrico, la firma en el SWIR se altera. Planta sana = Valor SWIR bajo

![](https://t90171211803.p.clickup-attachments.com/t90171211803/c5378422-aa7d-4570-b90e-154b1a4ecaa3/image.png)

## 3\. Catálogo de Índices para tu API

Cada mosaico NDVI es un mapeo a nivel píxel, de estadísticos (media, mediana, mínimo, máximo, desviación estándar) de los valores de este índice de vegetación.

Cuando configures los endpoints de tu servicio de mapas, puedes ofrecer distintos índices según lo que el usuario necesite evaluar en cada fase del ciclo agrícola:
### A. Para el inicio de campaña (Suelo descubierto o plántulas pequeñas)
*   MSAVI (Índice de Vegetación Ajustado al Suelo Modificado):
*   Fórmula:

![](https://t90171211803.p.clickup-attachments.com/t90171211803/53a3ea89-d1ae-4dbc-9d45-5fff05597e05/image.png)
> _Uso en Software: Cuando el NDVI falla porque hay demasiada tierra visible y poco cultivo (baja cobertura), MSAVI cancela el ruido del suelo. Es ideal para detectar cuándo empiezan a emerger las primeras plántulas en el lote._
### B. Para el monitoreo general de vigor y crecimiento activo
*   NDVI (Índice de Diferencia Normalizada): El estándar de la industria. Mide la biomasa fotosintéticamente activa. (Lo analizaremos a fondo en la siguiente sección) .
*   EVI (Índice de Vegetación Mejorado):

![](https://t90171211803.p.clickup-attachments.com/t90171211803/826f841c-433b-45d4-bc9c-5664fea3b5d4/image.png)
> _Uso en Software: El NDVI tiene un problema de "saturación": cuando un cultivo está sumamente tupido y denso, el NDVI se clava en valores cercanos a 1 y ya no muestra variaciones. EVI corrige esto ajustando el fondo y usando la banda azul para limpiar la dispersión de aerosoles atmosféricos, manteniendo la sensibilidad en coberturas densas._
### C. Para agricultura de precisión avanzada y fertilización
*   ReCl (Índice de Clorofila de Borde Rojo): $\\frac{\\text{NIR}}{\\text{RED}} - 1$. Monitorea directamente el nitrógeno y el verdor. Si el valor cae en la fase de desarrollo, indica la necesidad de aplicar fertilizantes.
*   NDRE (Índice de Diferencia Normalizada de Borde Rojo): Combina el NIR con el Borde Rojo para penetrar en las cubiertas vegetales de alta densidad cuando los cultivos ya alcanzaron su fase de madurez avanzada.
## 4\. El NDVI bajo la Lupa del Desarrollador

El cálculo del NDVI es la función básica de cualquier módulo GIS:
![](https://t90171211803.p.clickup-attachments.com/t90171211803/15ed188c-68ec-42ad-bdd6-9687e6912123/image.png)
Dada la simpleza en la definición del NDVI y su capacidad para distinguir la presencia de vegetación, así como la salud de esta.

Si estás utilizando imágenes de Sentinel-2, debes mapear en tu script que la banda RED corresponde a la Banda 4 (665 nm) y el NIR corresponde a la Banda 8 (842 nm).
### Tu matriz de interpretación para el código:

*   **Valores cercanos a 0 o negativos (< 0.1):** Agua, rastrojo puro, suelo completamente desnudo o nubes. Ausencia de vegetación.
*   **Valores intermedios (0.2 a 0.5):** Cultivos jóvenes en crecimiento, pastizales naturales con baja vigorosidad o cultivos bajo estrés hídrico moderado.
*   **Valores máximos (0.7 a 1.0):** Cultivo sano en su pico de verdor, canopia completamente cerrada (floración/fructificación).

![](https://t90171211803.p.clickup-attachments.com/t90171211803/060831d4-aa2e-45e3-a92e-ebefa0000168/image.png)
## 5\. Lógica Multicultivo y Umbrales Agronómicos en Territorio Argentino
Aquí es donde traducimos los datos de la bibliografía en reglas de negocio o condicionales para nuestro sistema. Los umbrales varían según el tipo de planta y su manejo en las campañas agrícolas:
### Soja y Maíz: Clasificación automática de Siembras (Tempranas vs. Tardías)
En los departamentos del sur de Córdoba (Unión y General Roca), la soja y el maíz representan más del 90% del área cultivada. Los modelos de clasificación tradicionales fallan porque confunden las curvas de desarrollo de ambos cultivos. La solución es programar un agrupamiento (K-means) sobre la serie temporal completa de NDVI promedio en lugar de mirar una sola foto satelital.
*   Regla de Filtrado Inicial: Si un lote arroja un NDVI máximo estival menor a 0.70, el sistema debe emitir una alerta de "Ciclo Incompleto" o pérdida potencial de rendimiento. Esto denota campos que sufrieron sequías severas, problemas sanitarios o fueron cosechados antes de tiempo como cultivo verde.
*   Regla de Clasificación Temporal (Ventana de Siembra):
    *   Si el valor pico máximo de NDVI de la serie ocurre antes del 1° de febrero, tu base de datos debe etiquetar el lote como Cultivo Temprano (o de Primera).
    *   Si el pico se desplaza y ocurre después del 1° de febrero, se etiqueta como Cultivo Tardío (o de Segunda).
    *   _Nota del Sistema:_ Los clústeres tardíos suelen mostrar valores de NDVI erráticos o elevados entre agosto y diciembre antes de la siembra del cultivo de verano. Esto delata la presencia de un antecesor invernal (como el trigo) que consume agua y acentúa el déficit hídrico del perfil del suelo.
### Algodón: El Vacío Sanitario Obligatorio
En regiones como el Chaco, el algodón es un cultivo preponderante.
*   Fase Final de Ciclo: Al finalizar el mes de marzo, el algodón culmina su ciclo vegetativo. El NDVI disminuye drásticamente debido a la madurez y defoliación.
*   Lógica de Alerta GIS: El sistema puede monitorear si el productor realizó la destrucción del rastrojo (dejando el suelo con un NDVI bajo, cercano a 0.2). Esto es vital para el control de plagas (como el picudo del algodonero) que usan los restos del cultivo como hospedero.
### Sorgo y Pastizales: Monitoreo Forrajero y Ganadero
*   El sorgo (muy común en el departamento Unión) y los pastizales naturales se monitorean continuamente para la planificación forrajera antes del ingreso al otoño e invierno.
*   Anomalías de NDVI: Investigadores del INTA La Rioja utilizan las anomalías (desviaciones del NDVI actual frente al promedio histórico de los últimos 24 años para ciclos de 16 días) para predecir crisis de alimento para el ganado bovino y caprino. Si tu sistema detecta una anomalía negativa persistente en otoño, debe emitir una alerta para que el productor compre suplementos energéticos o realice destetes precoces antes de que las vacas pierdan condición corporal.
## 6\. Integración en un Sistema de Software (Pipeline GIS)
Para que tu plataforma procese esto de forma automatizada, debes estructurar el procesamiento de datos en tres capas claras:

```less
[ CAPA DE INGESTA ]      -> Descarga de mosaicos Sentinel-2/Landsat (GeoTIFF) [cite: 6, 42]
         |
[ CAPA DE CÓMPUTO ]      -> Rasterio extrae las bandas y calcula los índices (NDVI/EVI) [cite: 54, 195]
         |
[ CAPA DE ANALÍTICA ]    -> GeoPandas cruza los polígonos de los lotes y corre K-means [cite: 51, 83]
```

1. Capa de Ingesta: Automatizar la descarga de imágenes con bajo porcentaje de nubes. La nubosidad y sus sombras introducen datos anómalos (caídas bruscas y erráticas en el gráfico de NDVI) que arruinan las curvas fenológicas si no se limpian mediante un filtro extra.
2. Capa de Cómputo: Procesar las bandas ópticas e infrarrojas (resolución de 10 metros en Sentinel-2) para generar las capas de índices.
3. Capa de Analítica: Utilizar archivos vectoriales (`shapefiles` o `GeoJSON` manejados con GeoPandas) que delimiten las fronteras reales de los lotes agrícolas. El sistema calcula el valor promedio de los píxeles internos de cada polígono y construye la serie de tiempo para la toma de decisiones.
## 7\. Tabla Final Consolidada de Umbrales Multicultivo
Aquí tienes las reglas numéricas exactas que debes cargar en el archivo de configuración de tu sistema (`config.json` o variables de entorno) para activar las alertas automáticas:

| Índice Utilizado | Cultivo / Cobertura | Región / Ubicación | Valor del Umbral | Significado Agronómico / Acción del Sistema | Fuente / Autor |
| ---| ---| ---| ---| ---| --- |
| NDVI | Todos los cultivos | General | `< 0.20` | Suelo desnudo, rastrojo o área sin actividad fotosintética activa. Filtro de depuración inicial. | Nolasco et al. / EOSDA |
| NDVI | Soja y Maíz | Central (Córdoba) | `< 0.70 (Máximo estival)` | Cultivo estival que no completó su ciclo reproductivo por estrés severo, secado o cosecha anticipada en verde. | Nolasco et al., 49 JAIIO |
| NDVI (Temporal) | Soja y Maíz | Central (Córdoba) | `Pico < 1° de Febrero` | Clasificación automática: Siembra Temprana (De Primera). | Nolasco et al., 49 JAIIO |
| NDVI (Temporal) | Soja y Maíz | Central (Córdoba) | `Pico > 1° de Febrero` | Clasificación automática: Siembra Tardía (De Segunda). Denota posible cultivo invernal antecesor. | Nolasco et al., 49 JAIIO |
| NDVI / EVI | Maíz, Algodón, Soja, Sorgo | NEA (Chaco) | `0.70 a 1.00` | Lotes agrícolas consolidados con vegetación en óptimo estado de vigor y alta densidad. | Informe CEDEI (Marzo 2024) |
| NDVI / EVI | Maíz, Algodón, Soja, Sorgo | NEA (Chaco) | `0.10 a 0.50` | Cultivos retrasados, vegetación escasa o bajo estrés hídrico y térmico por alta evapotranspiración. | Informe CEDEI (Marzo 2024) |
| Anomalía de NDVI | Pastizales y Pasturas | Zonas Áridas | Desviación negativa respecto al promedio histórico | Alerta de Sequía: Alerta temprana de escasez de recurso forrajero para ganado bovino y caprino. | Alicia Sancho (INTA La Rioja) |
| MSAVI | Cualquier grano grueso | General | Valores iniciales estables post-siembra | Éxito de implantación: Sensible a la vegetación temprana cuando la tierra apenas empieza a cubrirse. | EOSDA Crop Monitoring |

# Investigación Rasterio y GDAL

Rasterio, GDAL, GeoPandas: procesamiento ráster, sistemas de referencia y lectura multiespectral.

* * *
# Antes de Rasterio y GeoPandas: ¿qué son los datos geoespaciales?
En programación tradicional solemos trabajar con datos como:

| Nombre | Edad |
| ---| --- |
| Juan | 25 |
| Ana | 30 |

Esto puede manejarlo perfectamente Pandas.

```haskell
import pandas as pd

df = pd.read_csv("personas.csv")
```

Pandas es la librería más utilizada para trabajar con datos tabulares:
*   CSV
*   Excel
*   SQL
*   DataFrames
Podés filtrar, agrupar, ordenar y analizar información.
La limitación es que Pandas **no entiende geografía**.
Para Pandas:

```diff
-27.45, -58.98
```

son solamente dos números.
No sabe que representan una ubicación en el mundo.
* * *
# Entonces aparece GeoPandas
GeoPandas es una extensión de Pandas.
Podés pensarlo como:

```cs
Pandas
  +
Geometrías
  =
GeoPandas
```

Mantiene casi toda la funcionalidad de Pandas, pero agrega la capacidad de trabajar con objetos geográficos.
* * *
# ¿Qué es una geometría?
Una geometría es una forma que existe sobre la superficie terrestre.
Puede ser:

```plain
Punto
Línea
Polígono
```

* * *
## Punto
Por ejemplo:

```plain
Ubicación de una estación meteorológica
●
```

* * *
## Línea
Por ejemplo:

```powershell
Ruta nacional
Canal de riego
Río
──────────────
```

* * *
## Polígono
Por ejemplo:

```plain
Un lote agrícola
Una provincia
Una laguna
┌───────────┐
│           │
│           │
└───────────┘
```

* * *
# El concepto de polígono
Un polígono es simplemente una secuencia de coordenadas que delimitan una superficie.
Ejemplo:

```scheme
(-58.98,-27.45)
(-58.97,-27.45)
(-58.97,-27.46)
(-58.98,-27.46)
```

Si unimos esos puntos:

```css
A────────B
│        │
│ Campo  │
│        │
D────────C
```

acabamos de definir un lote.
* * *
# Una metáfora útil
Imaginá Google Maps.
Cuando alguien dibuja el límite de una propiedad:

```plain
Casa
Patio
Campo
Barrio
```

lo que realmente está guardando el sistema es un polígono.
No guarda una imagen.
Guarda una **lista de vértices**.
* * *
# ¿Por qué los polígonos son tan importantes?
Porque permiten responder preguntas.
Por ejemplo:
### ¿Cuál es el área del lote?
GeoPandas puede calcularla.
### ¿Qué cultivos están dentro del lote?
GeoPandas puede verificarlo.
### ¿Qué parte del NDVI corresponde a este campo?
GeoPandas puede recortar la imagen.
* * *
# Aquí aparece la diferencia fundamental
Hay dos formas de representar el mundo:
## Modelo vectorial
Usa geometrías.

```plain
Punto
Línea
Polígono
```

Ejemplos:
*   Lotes
*   Caminos
*   Provincias
*   Ríos
* * *
## Modelo ráster
Usa píxeles.

```css
[][][][][]
[][][][][]
[][][][][]
```

Ejemplos:
*   Imágenes satelitales
*   NDVI
*   Temperatura
*   Elevación
* * *
# Una analogía excelente
Imaginá un mapa impreso.
Los límites de las provincias:

```plain
Chaco
Corrientes
Formosa
```

serían vectores.
Porque pueden describirse mediante líneas y polígonos.
* * *
La fotografía satelital que aparece debajo:

```plain
Cultivos
Bosques
Nubes
Agua
```

sería un ráster.
Porque está compuesta por millones de píxeles.
* * *
# Entonces, ¿por qué existen GeoPandas y Rasterio?
Porque cada uno trabaja con un modelo distinto.
* * *
## GeoPandas
Trabaja con vectores.

```plain
Puntos
Líneas
Polígonos
```

Archivos típicos:
*   GeoJSON
*   Shapefile
*   GeoPackage
* * *
Ejemplo:

```haskell
import geopandas as gpd

lotes = gpd.read_file("lotes.geojson")
```

Obtendrás algo parecido a:

| id | propietario | geometría |
| ---| ---| --- |
| 1 | Juan | POLYGON(...) |
| 2 | Ana | POLYGON(...) |

* * *
## Rasterio
Trabaja con rásters.

```plain
GeoTIFF
```

Ejemplo:

```haskell
import rasterio

img = rasterio.open("sentinel.tif")
```

* * *
# ¿Qué devuelve Rasterio?
Bandas convertidas en matrices NumPy.
Ejemplo:

```dpr
b4 = img.read(4)
```

Resultado:

```yaml
[[6821 6900 7011]
 [6750 6880 6990]
 [6600 6710 6900]]
```

* * *
# ¿Qué es NumPy?
Otra pieza importante que suele darse por conocida.
NumPy es la **librería matemátic**a fundamental de Python.
Permite trabajar eficientemente con matrices.
* * *
Por ejemplo:

```plain
ndvi = (nir-red)/(nir+red)
```

parece una operación simple.
Pero en realidad puede estar calculando:

```plain
10980 × 10980
=
120 millones de píxeles
```

en una sola instrucción.
* * *
# ¿Dónde entra GDAL?
GDAL es la infraestructura que está debajo de casi todo.
Podés imaginarlo como el motor de un auto.

```css
Auto
 ↓
Motor
```

* * *
En GIS:

```plain
Rasterio
GeoPandas
QGIS
 ↓
GDAL
```

Muchísimas herramientas utilizan GDAL internamente, lo que sucede es que la curva de aprendizaje de esta libreria es mucho mayor, por ello se crean librerias mas amigables para el desarrollo.
* * *
# El caso típico de Agro Nexo
Ahora podemos conectar todo.
Supongamos que un productor registra un lote.
GeoPandas podría leer:

```css
Lote A
```

como un polígono.

```css
┌─────────────┐
│             │
│   Lote A    │
│             │
└─────────────┘
```

* * *
Después descargan una imagen Sentinel-2.
Rasterio la abre.

```css
[][][][][][][][][]
[][][][][][][][][]
[][][][][][][][][]
```

* * *
La imagen cubre toda una región.
Pero el productor sólo quiere su campo.
Entonces:

```css
Imagen completa
        +
Polígono del lote
```

↓

```css
Recorte del lote
```

* * *
Conceptualmente:

```markdown
GeoPandas
        ↓
Polígono del lote

Rasterio
        ↓
Imagen Sentinel

Ambos
        ↓
Recortar la imagen
        ↓
Calcular NDVI
        ↓
Guardar GeoTIFF resultado
```

* * *
Si tuviera que resumir las tres herramientas en una sola frase:
*   **GDAL:** el motor geoespacial que sabe leer y transformar datos geográficos.
*   **Rasterio:** la forma cómoda de trabajar con imágenes satelitales (rásters) en Python.
*   **GeoPandas:** la forma cómoda de trabajar con puntos, líneas y polígonos (vectores) en Python.
Y para Agro Nexo, probablemente el concepto más importante no sea Rasterio ni GDAL, sino entender que **el análisis geoespacial consiste en combinar un polígono (el lote) con un ráster (la imagen satelital)** para obtener información específica de esa parcela. Ese patrón aparece una y otra vez en casi todos los sistemas agrícolas basados en satélites.

# Investigacion geotiff

Estudio de archivos GeoTIFF con múltiples bandas. Metadatos, resolución espacial y CRS.

# ¿Qué es un GeoTIFF?
Un **GeoTIFF** es una extensión del formato TIFF tradicional que incorpora información geográfica dentro del archivo.
Mientras un TIFF común solo almacena píxeles, un GeoTIFF además guarda:
*   Coordenadas geográficas
*   Sistema de referencia espacial (CRS)
*   Resolución espacial
*   Transformación geográfica
*   Metadatos del sensor
Por eso puede abrirse directamente en software SIG como:
*   QGIS
*   ArcGIS Pro
*   Python mediante Rasterio o GDAL
* * *
# Estructura básica de un GeoTIFF
Un GeoTIFF contiene:

```erlang
GeoTIFF
│
├── Raster
│   ├── Banda 1
│   ├── Banda 2
│   ├── Banda 3
│   └── ...
│
├── Georeferenciación
│
├── CRS
│
└── Metadatos
```

* * *
# Bandas (Bands)
Una banda es una matriz de píxeles.
_Las bandas no representan "tipos" sino_ **_rangos específicos de longitudes de onda_** _del espectro electromagnético._
Ejemplo:

```yaml
1000 x 1000 píxeles
```

Cada píxel almacena un valor.
* * *
## Imagen RGB
Una imagen satelital "normal"

```plain
Banda 1 → Rojo
Banda 2 → Verde
Banda 3 → Azul
```

* * *
## Sentinel-2
_Sentinel-2 es un_ **_satélite_** _del programa Copernicus Programme._
_No captura solamente RGB._
_Captura muchas regiones del espectro electromagnético._

Cada banda mide una región distinta del espectro electromagnético.

| Banda | Descripción | Resolución |
| ---| ---| --- |
| B2 | Azul | 10 m |
| B3 | Verde | 10 m |
| B4 | Rojo | 10 m |
| B8 | Infrarrojo cercano (NIR) | 10 m |
| B5 | Red Edge | 20 m |
| B11 | SWIR | 20 m |

*   **Red Edge** (B5, B6, B7 en Sentinel-2): es la zona de transición entre el rojo y el infrarrojo cercano. Es muy sensible al estado de la vegetación, contenido de clorofila y estrés de las plantas.
*   **SWIR** (_Short-Wave Infrared_, B11 y B12): es infrarrojo de onda corta. Sirve para detectar humedad en suelo y vegetación, áreas quemadas, sequías y algunos tipos de minerales.

Por ejemplo:

```elixir
sentinel.tif

Band 1 -> B2
Band 2 -> B3
Band 3 -> B4
Band 4 -> B8
```

* * *
# ¿Cómo se almacenan los valores?
No siempre son colores.
En imágenes satelitales suelen representar:

```plain
Reflectancia
Radiancia
Temperatura
Elevación
NDVI
```

Ejemplo:

```yaml
Pixel = 7432
```

Puede significar:

```plain
Reflectancia = 0.7432
```

dependiendo del factor de escala indicado en los metadatos.
* * *
# Resolución espacial
La resolución espacial indica cuánto terreno representa un píxel.
Ejemplo:

```plain
10 m/pixel
```

Significa:

```plain
1 pixel = 10 m × 10 m
```

Área:

```plain
100 m²
```

* * *
## Ejemplo Sentinel-2
![](https://images.openai.com/static-rsc-4/MM2Vm7VzmqB_ZQPW5K7tOufvwvDPUEspCwgJCBwaabnofHFWl89v8-M44YEpZzQGsX693HHi1x3oV1GbNOY1bQMvSlSZZG0xHyUnU5WeqK5Yo2jHti8chWs9CYAiOYK5A85x8XBky-Zv7DEtRjWOBr8sz2pIt-ksYmyvb0EVkZLwPVeM9LMNBqKfr9k2Ngz7?purpose=fullsize)

Si una parcela mide:

```plain
500 m x 500 m
```

entonces aparecerá aproximadamente como:

```css
50 x 50 píxeles
```

* * *
## Cómo obtener la resolución en Python

```python
import rasterio

with rasterio.open("imagen.tif") as src:
    print(src.res)
```

Salida:

```scheme
(10.0, 10.0)
```

* * *
# Sistema de Referencia (CRS)
El CRS indica cómo interpretar las coordenadas.
Sin CRS no sabemos dónde está la imagen.
* * *
## Ejemplos comunes
### WGS84 o EPSG:4326
Utiliza:

```plain
Latitud
Longitud
```

Ejemplo:

```scheme
(-27.45, -58.98)
```

* * *
### UTM
Muy utilizado para agricultura.
Ejemplo:

```plain
EPSG:32721
```

UTM Zona 21 Sur
(Coordenadas en metros)

```plain
x = 301234
y = 6951234
```

* * *
## ¿Qué es EPSG?
La organización histórica **European Petroleum Survey Group** creó una base de datos de sistemas de referencia. Cada sistema recibió un identificador único.
Entonces existen el CRS WGS84 y el UTM, el primero se mide en **grados** (latitud y longitud) y el segundo en **metros** (se utiliza para mejorar la precision debido a calculos que se pueden realizar con los mismos).
Un dia esta organizacion EPSG decidio ponerle un **identificador unico** como id a cada sistema. Entonces quedo el 4326 para el WGS84, por lo cual es equivalente decir que esta imagen tiene un CRS **WGS84 a decir EPSG:4326**.
Luego con el UTM lo que sucede con su identificador es que **es unico dependiendo la region**. Este CRS se divide por zonas, por ejemplo para argentina:

```plain
32721
│ │
│ └── Zona 21
│
└──── Hemisferio Sur
```

## Ver CRS en Python

```python
with rasterio.open("imagen.tif") as src:
    print(src.crs)
```

Resultado:

```plain
EPSG:32721
```

* * *
# Transformación geográfica
Es la relación entre:

```plain
Fila/Columna
```

y

```plain
Coordenadas reales
```

Se almacena como una matriz afín.
Ejemplo:

```css
src.transform
```

Resultado:

```scss
Affine(
10.0, 0.0, 300000.0,
0.0,-10.0, 6950000.0
)
```

Interpretación:

```java
Pixel size = 10 m
Origen X = 300000
Origen Y = 6950000
```

Esto permite ubicar cualquier píxel en el mundo real.
* * *
# Metadatos
Los GeoTIFF almacenan mucha información adicional.
* * *
## Metadatos generales

```python
with rasterio.open("imagen.tif") as src:
    print(src.meta)
```

Ejemplo:

```bash
{
 'driver': 'GTiff',
 'dtype': 'uint16',
 'width': 10980,
 'height': 10980,
 'count': 4,
 'crs': 'EPSG:32721'
}
```

* * *
## Significado

| Campo | Descripción |
| ---| --- |
| width | ancho en píxeles |
| height | alto en píxeles |
| count | cantidad de bandas |
| dtype | tipo de dato |
| crs | sistema de coordenadas |
| driver | formato |

* * *
# Tipos de datos (dtype)
Los valores de los píxeles pueden almacenarse como:

| Tipo | Tamaño |
| ---| --- |
| uint8 | 8 bits |
| uint16 | 16 bits |
| int16 | 16 bits |
| float32 | 32 bits |
| float64 | 64 bits |

* * *
## Sentinel-2
Normalmente:

```go
uint16
```

porque la reflectancia se escala.
Ejemplo:

```go
Reflectancia real = valor / 10000
6832 → 0.6832
```

# Soja: Interpretación agronómica de índices

Revisión bibliográfica NDVI/GNDVI/SAVI: significado agronómico en soja y estadios fenológicos.

Para esta sección específica de tu informe académico, el enfoque cambia. Ya no explicamos qué son las fórmulas o cómo se ve un píxel en general, sino que diseñamos la lógica temporal y biológica del cultivo de soja vinculada a tres sensores específicos de tu API.
En términos de desarrollo, esta sección equivale a escribir el diccionario de estados de la aplicación (la máquina de estados del ciclo de vida del cultivo). Aquí detallamos la información exacta, didáctica y orientada a objetos que debe incluirse, estructurada paso a paso según los estadios de la soja:
## Sección: Revisión Bibliográfica de Índices en el Ciclo Fenológico de la Soja
Un estadio fenológico es simplemente una fase del ciclo de vida de la planta (como la infancia, adolescencia o madurez en humanos). En la soja se dividen en dos grandes etapas: V (Vegetativas, aparición de hojas) y R (Reproductivas, aparición de flores, vainas y semillas).
Para nuestro sistema informático, la fenología es una curva de tiempo donde el eje Y es el valor del índice y el eje X son los días transcurridos desde la siembra. Así interactúan SAVI, NDVI y GNDVI en cada fase:
### Fase 1: Emergencia e Implantación (Estadios V1 a V3)
*   El reto informático: Las plantas de soja son diminutas plántulas espaciadas. Si miras el lote con un satélite, el 90% del píxel es tierra marrón húmeda o seca. El NDVI se confunde por el brillo del suelo y arroja valores erráticos.
*   Índice estrella a aplicar: SAVI (Soil-Adjusted Vegetation Index).
    *   Significado agronómico: Este índice introduce una constante de ajuste físico (L = 0.5) en su denominador para cancelar el "ruido blanco" que genera el reflejo de la tierra desnuda.
    *   Comportamiento en el sistema: El programador debe configurar que durante las primeras 3 semanas post-siembra, el backend ignore el NDVI y analice el SAVI. Un aumento constante y plano en los valores de SAVI (ej. saltar de 0.15 a 0.35) valida que el cultivo ha "emergido" de forma homogénea en el lote.
### Fase 2: Crecimiento Vegetativo y Cierre de Entresurco (Estadios V4 a Vn)
*   El reto informático: Las ramas de la soja empiezan a expandirse hacia los costados hasta que las hojas de una hilera se tocan con las de la hilera de al lado, cubriendo la tierra por completo (esto se llama económicamente _cierre de entresurco_).
*   Índice estrella a aplicar: NDVI.
    *   Significado agronómico: A medida que se acumulan capas de hojas verdes, la absorción de luz roja es masiva y el rebote de Infrarrojo Cercano (NIR) se dispara. El NDVI se vuelve el sensor más lineal y preciso.
    *   Comportamiento en el sistema: La curva en tu base de datos debe mostrar una pendiente ascendente pronunciada (una tasa de cambio diaria alta, $\\Delta\\text{NDVI}/\\Delta t$). Si el gradiente de la curva se estanca o se deprime en esta fase, el sistema debe disparar una alerta de anomalía vegetativa (posible ataque de orugas o estrés hídrico temprano).
### Fase 3: Floración y Llenado de Granos (Estadios R1 a R5) - El "Pico Fenológico"
*   El reto informático: El cultivo llega a su máximo tamaño y densidad biológica. Aquí el NDVI sufre de saturación: el lote está tan asombrosamente verde que el NDVI se "clava" en un valor plano (ej. 0.82) y es incapaz de distinguir si una zona del campo tiene más o menos clorofila/nitrógeno que otra. El tablero de control se vuelve "ciego" a los matices.
*   Índice estrella a aplicar: GNDVI (Green NDVI).
    *   Significado agronómico: El GNDVI reemplaza la banda roja por la banda verde. La luz verde penetra mucho más profundo en las capas inferiores del dosel de la soja en lugar de quedarse solo en las hojas de arriba.
    *   Comportamiento en el sistema: En el momento en que el NDVI global del lote supere el umbral de 0.75, tu código debe activar un "conmutador" para mostrar mapas basados en GNDVI. Esto le permitirá al productor ver la variabilidad real del rendimiento potencial dentro del lote de soja durante su período crítico: áreas con GNDVI alto significarán vainas bien nutridas; caídas en el GNDVI delatarán muerte celular o senescencia prematura por falta de nutrientes.
### Fase 4: Madurez y Cosecha (Estadios R7 a R8)
*   El reto informático: La soja es un cultivo que "se entrega" (se seca por completo en pie antes de cosecharse). Las hojas pierden clorofila, se vuelven amarillas, caen al suelo y el lote se transforma en un manto de tallos y vainas de color marrón crujiente.
*   Comportamiento en el sistema (NDVI/GNDVI en caída libre):
    *   Ambos índices experimentan un desplome vertical inverso a la fase 2. El valor cae por debajo de 0.30 de manera uniforme.
    *   Lógica de decisión para el software: Cuando la serie temporal detecte que el lote lleva más de 10 días estabilizado en un valle plano de NDVI bajo (entre 0.20 y 0.25) luego de una caída abrupta, el sistema debe cambiar el estado del lote a "Listo para Cosecha". Si de pronto el índice vuelve a subir de golpe en esta fase, ¡cuidado! No es que la soja revivió, sino que nacieron malezas peligrosas que están invadiendo el lote seco, y el sistema debe enviar una alerta urgente de aplicación de herbicidas.
### Resumen de Reglas de Inyección para el Backend (Arquitectura del Módulo)
Para resumir la información bibliográfica en arquitectura limpia de software, cada índice tiene una ventana de validez según el estado del _pipeline_ temporal:
1. `if dias_desde_siembra < 25:` -> Usar SAVI. Monitorea el nacimiento y stand de plantas mitigando el efecto del suelo desnudo.
2. `if 25 <= dias_desde_siembra < 60:` -> Usar NDVI. Mide la velocidad de crecimiento vegetativo y detecta anomalías en el desarrollo de biomasa verde.
3. `if NDVI > 0.75 (Fase Crítica R):` -> Usar GNDVI. Rompe la saturación del espectro rojo e inspecciona la salud fotosintética profunda en el llenado de semillas.
4. `if Delta_NDVI < 0 y NDVI -> 0.2` -> Estado: Senescencia/Cosecha. Determina el fin del ciclo biológico del cultivo de soja.

# Sprint 2



# Patrones espaciales y causas probables

# Patrones espaciales y causas probables

**Tarea:** Sprint 2 — R1 · Discovery & Arquitectura
**Investigador:** (asignar)
> **Fuentes base:** ERS AgroNexo (Drive), bibliografía científica y INTA
* * *

## 1\. ¿Qué es un patrón espacial en un cultivo?

En agricultura de precisión, un **patrón espacial** es la distribución geográfica que adoptan las anomalías dentro de un lote cuando se visualizan en un mapa de índices como NDVI, NDRE o NDWI. La forma, extensión y distribución de esas zonas anómalas no es aleatoria: responde a la naturaleza del problema que las origina.

### Fundamento conceptual

La idea de que los problemas agronómicos producen patrones espaciales identificables proviene del campo de la **geoestadística aplicada a la agricultura de precisión**. Según Whelan & McBratney (2000), la variabilidad espacial dentro de un lote puede tener causas tanto edáficas (propiedades del suelo) como bióticas (plagas, enfermedades) o de manejo (compactación, aplicaciones diferenciales), y cada una genera una estructura espacial distinta que puede caracterizarse estadísticamente.

> **Referencia:** Whelan, B.M. & McBratney, A.B. (2000). _The "null hypothesis" of precision agriculture management_. Precision Agriculture, 2(3), 265–279.

### Los 6 patrones fundamentales

**1\. Patrón circular o radial**

*   Zona de bajo vigor con forma aproximadamente circular, que se expande desde un punto focal hacia los bordes.
*   Causa típica: enfermedades fúngicas que se propagan desde un inóculo inicial (Sclerotinia sclerotiorum, Rhizoctonia solani, podredumbre carbonosa).
*   Cómo se ve en NDVI: núcleo de NDVI muy bajo rodeado de gradiente decreciente hacia los bordes.
*   Índice más sensible: NDRE (detecta estrés clorofílico antes que el NDVI en estadios tempranos).
![](https://t90171211803.p.clickup-attachments.com/t90171211803/09c1dafb-7944-47e0-89c9-db579540f1eb/image.png)

**2\. Patrón lineal o en franjas**

*   Bandas de bajo vigor paralelas al sentido de trabajo de la maquinaria o de la siembra.
*   Causa típica: compactación subsuperficial por pisada de tractor, problemas de dosificación en sembradora (tapones, fallas por cuerpo), fertilización diferencial por falla de aplicador.
*   Cómo se ve en NDVI: rayas de igual ancho que el interfilare del equipo, perfectamente alineadas.
*   Indicador clave: la separación entre franjas coincide exactamente con el ancho de labor de la máquina.
![](https://t90171211803.p.clickup-attachments.com/t90171211803/9c1b4f97-9267-4839-8baa-5617cb7c350d/image.png)

**3\. Patrón difuso o gradual**

*   Degradación progresiva del vigor sin bordes definidos, transición suave entre zonas sanas y afectadas.
*   Causa típica: variabilidad edáfica natural (cambio de textura, materia orgánica, profundidad de horizonte B), déficit hídrico generalizado, deficiencias nutricionales de elementos móviles (N, S).
*   Cómo se ve en NDVI: mapa con "gradiente" continuo, similar a un mapa topográfico suavizado.
*   Índice complementario: SAVI (corrige efecto del suelo en coberturas bajas, muy útil en estadios tempranos de soja en el Chaco).
![](https://t90171211803.p.clickup-attachments.com/t90171211803/9e5d6e6f-0949-4eec-ac6f-1bb51fbf5b51/image.png)

**4\. Patrón aleatorio o disperso**

*   Manchas de bajo vigor distribuidas sin estructura geométrica clara, sin relación entre sí.
*   Causa típica: plagas móviles (chinches, orugas defoliadoras), daño por granizo localizado, pisadas de fauna silvestre (carpinchos, ciervos en el NEA).
*   Cómo se ve en NDVI: "salpicado" irregular, difícil de vectorizar en polígonos grandes.
![](https://t90171211803.p.clickup-attachments.com/t90171211803/bea7212b-cf75-4a8f-91ef-4d3a77579d36/image.png)

**5\. Patrón en manchones irregulares persistentes**

*   Manchas de forma irregular, con bordes relativamente definidos, que se repiten en posiciones fijas campaña tras campaña.
*   Causa típica: variabilidad de tipo de suelo (transición entre serie edáfica), nematodos (Heterodera glycines en soja, Pratylenchus spp.), salinidad o sodicidad puntual.
*   Cómo se ve en NDVI: manchones que se repiten en la misma posición geográfica en vuelos de diferentes fechas. Criterio diagnóstico clave: **persistencia temporal**.
*   Referencia: Landa, B.B. et al. (2006). _Influence of temperature on plant-parasitic nematode spatial patterns_. Phytopathology, 96(1), 97–104.

**6\. Patrón siguiendo curvas de nivel o microtopografía**

*   Las zonas afectadas coinciden con las partes más bajas del lote (cañadas, mallines, sectores con drenaje impedido).
*   Causa típica: anegamiento temporario, hipoxia radicular, pudriciones de raíz asociadas a exceso hídrico (Phytophthora sojae, Pythium spp.).
*   Cómo se ve en NDVI + NDWI: NDWI alto + NDVI bajo en las mismas coordenadas. Correlaciona perfectamente con un MDE (modelo digital de elevación).
*   Relevancia para el NEA: el Chaco presenta llanuras con pendientes menores al 0,5%, donde el anegamiento temporario es uno de los principales limitantes productivos según INTA EEA Las Breñas.
* * *

## 2\. Tabla de decisión: Patrón → Causa probable

Esta tabla es el núcleo del módulo **RFDR-01 (Motor de reglas)** del sistema AgroNexo. Cruza el patrón espacial observado, los índices afectados y el contexto del lote para producir una lista de causas probables ordenadas por verosimilitud.

La lógica no es determinista (un patrón = una causa única) sino probabilística: el sistema presenta causas probables que el agrónomo confirma o descarta con inspección en campo (RFDR-04).

### Tabla maestra — Soja (cultivo principal NEA)

| Índices complementarios | Patrón espacial | Índice principal afectado | Causa probable (orden de prioridad) | Estadio más frecuente | Confirmación en campo |
| ---| ---| ---| ---| ---| --- |
| MSI elevado | Circular, bordes nítidos, < 50 m diámetro | NDRE muy bajo, NDVI bajo | 1\. Sclerotinia sclerotiorum 2. Rhizoctonia solani 3. Fusarium spp. | R1–R5 | Buscar micelio blanco en cuello de planta |
| NDWI elevado en centro | Circular, bordes difusos, > 100 m | NDVI bajo gradual | 1\. Phytophthora sojae 2. Pythium spp. (hipoxia) | V3–R3 | Raíces oscuras, olor a podredumbre |
| SAVI reducido | Lineal, ancho = interfilare máquina | NDVI bajo uniforme en franjas | 1\. Compactación subsuperficial 2. Falla de sembradora (tapón) 3. Subfertilización diferencial | V1–V6 | Penetrómetro, inspección de plantas por fila |
| SAVI bajo, NDRE bajo | Difuso, gradiente suave, sin bordes | NDVI bajo generalizado | 1\. Deficiencia de N (estadio tardío) 2. Variabilidad edáfica (materia orgánica) 3. Estrés hídrico generalizado | V4–R2 | Análisis foliar, calicata, muestras de suelo |
| GNDVI reducido | Manchones irregulares, posición repetida en campañas anteriores | NDVI bajo persistente | 1\. Nematodos (Heterodera glycines) 2. Variabilidad de suelo (textura/serie) 3. Salinidad/sodicidad | Todos | Muestras de suelo para nematología |
| MSI elevado | Siguiendo microtopografía (partes bajas) | NDWI alto + NDVI bajo | 1\. Anegamiento temporario 2. Phytophthora sojae 3. Pythium spp. | V1–R3 | Calicata: horizonte gleyzado, raíces pardas |
| — | Aleatorio, disperso, bordes indefinidos | NDVI bajo puntual | 1\. Orugas defoliadoras (Anticarsia gemmatalis) 2. Chinches (Nezara viridula) 3. Daño por granizo | R1–R6 | Conteo de insectos, inspección visual |
| NDRE bajo | Borde del lote + franjas internas alineadas al viento | NDVI bajo progresivo | 1\. Roya asiática (Phakopsora pachyrhizi) — avance desde bordes | R1–R5 | Pústulas en haz de hoja, color oxidado |
| — | Manchones con forma alargada en sentido del viento | NDVI bajo | 1\. Mancha ojo de rana (Cercospora sojina) | R3–R6 | Manchas circulares con centro gris en hojas |

### La columna "Estadio más frecuente" de la tabla de decisión
Hace referencia a la **escala de estadios fenológicos de la soja**, que es el sistema estándar para describir en qué momento del ciclo del cultivo aparece cada problema. Se divide en:
**Estadios vegetativos (V):**
*   V1, V2, V3... → primera, segunda, tercera hoja trifoliada desplegada
*   V6 → sexta hoja trifoliada (planta bien desarrollada)
**Estadios reproductivos (R):**
*   R1 → inicio de floración (primeras flores abiertas)
*   R2 → floración plena
*   R3 → inicio de formación de vainas
*   R4 → vainas llenas
*   R5 → inicio de llenado de granos
*   R6 → granos llenos (máximo peso verde)
*   R7 → inicio de madurez
*   R8 → madurez completa

### Tabla complementaria — Algodón (NEA)

| Patrón espacial | Índice afectado | Causa probable | Observaciones |
| ---| ---| ---| --- |
| Circular, foco definido | NDRE bajo | Verticillium dahliae (marchitez) | Muy frecuente en suelos con historia algodonera |
| Franjas paralelas a la siembra | NDVI bajo | Compactación, falla de sembradora | Igual lógica que soja |
| Manchones irregulares, persistentes | NDVI bajo | Nematodo del nódulo (Meloidogyne incognita) | Muy relevante en el Chaco, favorecido por altas T° del suelo |
| Siguiendo microtopografía | NDWI alto + NDVI bajo | Anegamiento, Phytophthora gossypii | Similar a soja |
| Disperso, sin estructura | NDVI bajo puntual | Picudo del algodón (Anthonomus grandis), daño por granizo | — |

### Lógica de implementación en AgroNexo

El motor de reglas (RFDR-01) implementa esta tabla como un sistema de scoring:

1. **Entrada:** forma del polígono (circularidad, elongación), tamaño, posición relativa en el lote (bajo/alto), índice(s) afectado(s), cultivo, estadio fenológico.
2. **Proceso:** cada causa recibe un puntaje según cuántas condiciones cumple.
3. **Salida:** lista ordenada de causas probables con porcentaje de verosimilitud + mensaje al agrónomo indicando qué verificar en campo.
* * *

## 3\. Factores edáficos y ambientales del NEA que generan variabilidad espacial

### Por qué el NEA necesita tratamiento especial

Gran parte de la bibliografía sobre patrones espaciales y umbrales NDVI proviene de la región pampeana o de estudios norteamericanos. El NEA (Chaco, Formosa, Corrientes, Misiones) presenta condiciones particulares que alteran significativamente los valores esperados y la forma de los patrones.

![](https://t90171211803.p.clickup-attachments.com/t90171211803/072c1f7a-1f95-421c-a0bf-d367d87542cc/image.png)
Imagen para entender los horizontes

### 3.1 Suelos predominantes del Chaco y su efecto en los índices

**Vertisoles**

*   Suelos oscuros, con alta plasticidad y contracción/expansión por humedad.
*   Generan grietas profundas en época seca que producen patrones lineales de bajo NDVI que pueden confundirse con fallas de maquinaria.
*   El color negro del suelo seco eleva artificialmente la reflectancia en banda roja → NDVI más bajo de lo real en suelos con cobertura incompleta.
*   **Implicancia para AgroNexo**: el **SAVI** es más confiable que el NDVI en estas condiciones de cobertura parcial.

**Alfisoles (Argiudoles vérticos y Haplustoles)**

*   Presencia de horizonte B argílico que puede generar restricciones al drenaje y la penetración radicular → produce manchones de bajo vigor que se confunden con enfermedades de raíz.
*   La transición abrupta entre horizontes genera contrastes de NDVI coincidentes con cambios de textura subsuperficial.

**Suelos Sódicos y Salino-Sódicos**

*   Presentes en sectores del Chaco central y este.
*   Producen manchones de vegetación rala o nula de posición fija, persistentes entre campañas, que el sistema debe identificar como limitación edáfica permanente (no susceptible a prescripción fitosanitaria).
*   NDVI crónico < 0.2 incluso con cultivo establecido.
*   Fuente: INTA EEA Las Breñas (2018). _Caracterización de suelos problemáticos en el Chaco semiárido_.

### 3.2 Anegamiento temporario — el principal limitante del NEA

El NEA presenta una de las frecuencias de anegamiento temporario más altas de Argentina para uso agrícola. Las llanuras aluviales del Chaco tienen pendientes < 0.5% y suelos con baja permeabilidad, lo que genera inundaciones cortas pero recurrentes durante la campaña.

*   El anegamiento produce hipoxia radicular que se manifiesta como NDVI bajo exactamente en las partes topográficamente más bajas del lote.
*   La firma espectral es: NDWI alto + NDVI bajo + MSI bajo (alta humedad foliar al inicio, luego deshidratación por muerte radicular).
*   El patrón coincide perfectamente con el modelo digital de elevación (MDE).
*   Soja: extremadamente sensible en V1–R3. Más de 72 h de anegamiento causa daños irreversibles.
*   Fuente: INTA EEA Las Breñas (2019). _Manejo del anegamiento en cultivos extensivos del Chaco semiárido_. / Borrás, L. et al. (2003). Field Crops Research, 83(2), 143–151.

### 3.3 Variabilidad de materia orgánica (MO)

*   En el Chaco, la deforestación histórica ha generado lotes con marcadas diferencias de MO entre sectores según la fecha de desmonte.
*   Sectores desmontados hace más tiempo → MO más baja → menor disponibilidad de N → NDVI estructuralmente más bajo.
*   Patrón resultante: gradiente difuso, no corregible con fumigación, que el sistema debe identificar como "variabilidad edáfica" y no como problema biótico.

### 3.4 Malezas problemáticas del NEA relevantes para detección multiespectral

| Maleza | Familia | Por qué importa | Índice más útil |
| ---| ---| ---| --- |
| Rama negra (Conyza bonariensis) | Asteraceae | Resistente a glifosato, muy extendida | ExG, VARI |
| Sorgo de Alepo (Sorghum halepense) | Poaceae | Perenne, rebrota desde rizoma | NDVI, ExG |
| Yuyo colorado (Amaranthus hybridus) | Amaranthaceae | Altísima producción de semillas | ExG, GNDVI |
| Gramón (Cynodon dactylon) | Poaceae | Cobertura baja pero densa, difícil de distinguir del suelo | NDRE, SAVI |
| Verdolaga (Portulaca oleracea) | Portulacaceae | Muy presente en barbechos húmedos del NEA | ExG |

*   Fuentes: INTA SINAVIMO (2024). [https://www.sinavimo.gob.ar](https://www.sinavimo.gob.ar) / Vigna, M. & Gigón, R. (2014). _Malezas resistentes en Argentina_. INTA EEA Bordenave.
* * *

## 4\. Patrones de estrés biótico

### 4.1 Malezas

**Diferencia entre hoja ancha y gramínea en imagen multiespectral**

| Característica | Hoja ancha (dicotiledóneas) (malesa) | Gramínea (Poaceae) |
| ---| ---| --- |
| Reflectancia NIR | Alta | Moderada |
| ExG típico | \> 0.1 | 0.05–0.10 |
| NDVI | Similar al cultivo | Levemente inferior |
| Forma del patrón | Manchones irregulares | Franjas o cobertura difusa |
| Mejor índice discriminador | ExG, VARI | NDRE, GNDVI |

![](https://t90171211803.p.clickup-attachments.com/t90171211803/3922be3b-f000-45e2-b510-fc55022886ff/image.png)
**Reflectancia NIR** — Las hojas anchas (como el yuyo colorado o la rama negra) tienen una estructura interna más compleja que refleja más luz infrarroja. Las gramíneas (como el sorgo de Alepo) tienen hojas más finas y paralelas, reflejan menos NIR.
**ExG (Exceso de Verde)** — Es una fórmula que resalta píxeles verdes: `2×Verde - Rojo - Azul`. Cuanto más verde intenso y estructurado es el tejido foliar, mayor el ExG. Las hojas anchas tienen más masa foliar verde → ExG más alto. Las gramíneas, más delgadas → ExG más bajo.
**NDVI** — Como el cultivo de soja también es hoja ancha, las malezas de hoja ancha en el cultivo tienen NDVI _similar_ al cultivo → difíciles de distinguir. Las gramíneas tienen NDVI levemente inferior, lo que ayuda un poco, pero no es suficiente solo.
**Forma del patrón** — Las malezas de hoja ancha crecen en manchones irregulares (se expanden radialmente desde una semilla). Las gramíneas como el sorgo de Alepo o el gramón tienden a cubrir franjas o áreas difusas porque se propagan por rizomas o estolones horizontales.
**Mejor índice discriminador** — ExG y VARI funcionan mejor para hojas anchas porque explotan la diferencia de verde intenso. NDRE y GNDVI funcionan mejor para gramíneas porque son más sensibles a pequeñas diferencias en clorofila donde el contraste de verde no es tan marcado.

**Buffer de aplicación**
La prescripción de fumigación de malezas requiere agregar un buffer geométrico al polígono vectorizado. La maquinaria fumigadora necesita tiempo de apertura de la boquilla antes de llegar a la zona de maleza. Distancia estándar para equipos terrestres en Argentina: **3 a 7 metros** según velocidad de avance y tiempo de respuesta de la consola.

*   Fuente: Bragachini, M. et al. (2012). _Agricultura de precisión: siembra variable y prescripción de insumos_. INTA PRECOP.

### 4.2 Enfermedades fúngicas en soja

**Roya asiática (Phakopsora pachyrhizi)**

*   Patrón: comienza en los bordes del lote (ingreso por viento) y avanza en dirección del viento dominante.
*   NDRE es el índice más sensible para detección temprana: cae antes que el NDVI porque afecta la clorofila antes de producir necrosis visible.
*   Condiciones favorables en el Chaco: alta humedad + temperatura 25–28°C.
*   Fuente: Carmona, M. & Gally, M. (2004). _Roya de la soja: guía práctica_. Facultad de Agronomía UBA.

**Sclerotinia sclerotiorum (podredumbre blanca)**

*   Patrón: circular o elíptico, muy definido, diámetro 5–50 m. Se origina desde esclerocios en el suelo.
*   NDVI cae abruptamente en el centro del foco → patrón ideal para vectorización.
*   Condición predisponente: alta densidad de siembra, días frescos con rocíos prolongados (R1–R3).

**Rhizoctonia solani (podredumbre de raíz y tallo)**

*   Patrón: circular irregular, puede fusionar focos. La planta se seca sin volcar.
*   NDVI cae bruscamente; en estadios tardíos aspecto "quemado" con plantas erectas muertas.

**Mancha ojo de rana (Cercospora sojina)**

*   Patrón: manchones dispersos sin estructura geométrica, distribución irregular.
*   NDVI moderadamente bajo, difícil de distinguir de estrés hídrico leve → requiere validación en campo.

### 4.3 Plagas defoliadoras

**Orugas (Anticarsia gemmatalis, Rachiplusia nu)**

*   Patrón: difuso, avanza desde bordes hacia el centro del lote.
*   La defoliación reduce el LAI → menos reflectancia NIR → NDVI cae.
*   Umbral de daño económico en soja: 30% de defoliación en estadios vegetativos / 15% en reproductivos (SENASA / INTA).

**Chinches (Nezara viridula, Piezodorus guildinii)**

*   Patrón: muy difuso y disperso. Baja sensibilidad del NDVI.
*   Caso donde el sistema debe reconocer su limitación diagnóstica y remitir al agrónomo.

**Mosca blanca (Bemisia tabaci)**

*   Puede generar patrones difusos de amarillamiento (NDRE bajo) por transmisión de virus (Begomovirus).
*   Asociada a sequía y temperaturas altas → NEA muy susceptible.

### 4.4 Nematodos

**Heterodera glycines (nematodo del quiste de la soja)**

*   Patrón: manchones irregulares con posición fija, persistentes entre campañas.
*   NDVI y GNDVI bajos de forma crónica. No responden a ningún tratamiento fitosanitario aéreo → el sistema debe identificar este patrón como limitación de suelo.
*   Diagnóstico definitivo: análisis de suelo (conteo de quistes y larvas por 100 cm³).

**Meloidogyne incognita (nematodo del nódulo)**

*   Las temperaturas del suelo en el Chaco (> 25°C) son óptimas para este nematodo.
*   En algodón es la especie más limitante.
*   Fuente: INTA EEA Sáenz Peña (2021). _Nematodos parásitos de cultivos en el Chaco: diagnóstico y estrategias de manejo_.
* * *

## 5\. Patrones de estrés abiótico

### 5.1 Estrés hídrico

**Índices clave y sus limitaciones con el DJI Mavic 3 Multispectral**

*   **NDWI convencional** (NIR − SWIR) / (NIR + SWIR): requiere banda SWIR, que el DJI Mavic 3 M **no tiene**. No es calculable directamente. Esta limitación técnica debe documentarse en los RNF del sistema.
*   **NDWI de McFeeters** (Verde − NIR) / (Verde + NIR): disponible con el sensor, pero detecta agua superficial, no estrés hídrico foliar.
*   **NDRE como proxy:** cae antes que el NDVI ante estrés hídrico. Una caída del NDRE > 15% respecto al promedio del lote en R1–R2 puede anticipar estrés hídrico antes de que sea visible en campo.
*   Fuente: Gitelson, A.A. et al. (2006). Remote Sensing of Environment, 144, 65–72.

**Tipos de estrés hídrico y sus patrones**

| Tipo de estrés | Patrón espacial | Evolución temporal | Causa |
| ---| ---| ---| --- |
| Temporal (sequía) | Difuso, generalizado | Se recupera con lluvias | Déficit de precipitaciones |
| Estructural (suelo) | Manchones o gradiente fijo | Persiste entre campañas | Baja retención hídrica, tosca, horizonte B impermeable |
| Por anegamiento | Partes bajas del lote | Se recupera si drenan | Exceso hídrico, hipoxia radicular |

### 5.2 Deficiencias nutricionales

**Principio: movilidad de nutrientes**

*   Nutrientes móviles (N, P, K, Mg, S): síntomas en hojas viejas → amarillamiento difuso desde base del canopeo.
*   Nutrientes inmóviles (Ca, Fe, Mn, Zn, B): síntomas en hojas jóvenes → patrones más puntuales.

**Nitrógeno (N)**

*   Patrón difuso, gradiente suave, correlacionado con materia orgánica del suelo.
*   NDVI, GNDVI y NDRE bajos (el N es componente central de la clorofila).
*   En soja: la deficiencia de N puede deberse a falla de inoculación, suelo con alta actividad microbiana competidora, o anegamiento previo que mató los nódulos. El sistema debe contemplar este contexto.
*   Fuente: Salvagiotti, F. et al. (2008). Field Crops Research, 108(1), 1–13.

**Hierro (Fe) y Manganeso (Mn)**

*   En suelos con pH > 7.5 (frecuentes en vertisoles del Chaco), la disponibilidad de Fe y Mn se reduce drásticamente.
*   Producen clorosis internerval en hojas jóvenes → patrón correlacionado con mapa de pH del suelo.

### 5.3 Fitotoxicidad por herbicidas

*   **Deriva por viento:** franja de daño en el borde del lote con gradiente de intensidad, siguiendo la dirección del viento en el momento de aplicación.
*   **Sobredosis diferencial (falla de consola):** franjas del ancho del equipo, alternando zonas de daño y normales.
*   Firma espectral: NDVI cae bruscamente, NDRE muy bajo, bordes del polígono más nítidos que en enfermedades.
*   El sistema debe cruzar con el historial de intervenciones (RFGL-03) para elevar la probabilidad de esta causa cuando hubo aplicaciones recientes.

### 5.4 Compactación de suelo

*   Patrón lineal si sigue las líneas de trabajo; en manchones si es de origen histórico (cabeceras, caminos internos).
*   NDVI moderadamente bajo, estable entre campañas (no desaparece sin labranza).
*   AgroNexo puede identificarla como causa probable cuando: el patrón lineal coincide con el interfilare de la maquinaria, el bajo NDVI persiste en el historial de vuelos anteriores (RFGL-03), y no hay correlación con datos climáticos.
*   Fuente: Lipiec, J. & Hatano, R. (2003). Geoderma, 116(1-2), 107–136.
* * *

## 6\. Implicancias para el sistema AgroNexo

### 6.1 Requisitos impactados por esta investigación

| Requisito | Implicancia |
| ---| --- |
| RFMA-04 Detección de anomalías | El sistema debe clasificar anomalías no solo por valor de índice sino por forma geométrica del polígono |
| RFDR-01 Motor de reglas | La tabla patrón→causa (sección 2) es el insumo principal de este módulo |
| RFDR-02 Zonificación de manejo | Las causas con mismo patrón en zonas contiguas deben agruparse en una unidad de manejo única |
| RFDR-03 Estimación de severidad | La severidad se estima como diferencia de índice entre zona afectada y promedio del lote |
| RFDR-04 Registro de criterio técnico | El agrónomo debe poder seleccionar o modificar la causa probable sugerida por el sistema |
| RFGL-03 Historial de intervenciones | Imprescindible para distinguir patrones persistentes (edáficos/nematodos) de episódicos (enfermedades) |

### 6.2 Ambigüedades irresolubles solo por imagen — límites del sistema

El sistema debe comunicar activamente sus limitaciones diagnósticas:

1. **Estrés hídrico vs. deficiencia de N vs. enfermedad foliar temprana:** los tres producen NDVI y NDRE bajos con patrones difusos. Sin contexto climático y análisis foliar, no es posible distinguirlos con certeza.
2. **Nematodos vs. variabilidad edáfica:** ambos producen manchones de posición fija y bajo NDVI crónico. Solo se distinguen con muestras de suelo.
3. **Roya asiática temprana vs. mancha ojo de rana:** en estadios tempranos pueden producir patrones similares. El NDRE ayuda a priorizar la roya, pero la confirmación visual es necesaria.
4. **Fitotoxicidad vs. enfermedad de bordes:** ambas pueden presentar franjas en el borde del lote. El historial de aplicaciones es el dato discriminante.

**Tipos de mensaje que el sistema debe emitir (sugerencia para RFDR-04):**

*   "Diagnóstico probable con alta confianza": patrón + índice + contexto consistentes con una sola causa.
*   "Diagnóstico ambiguo — se requiere verificación en campo": dos o más causas con igual verosimilitud.
*   "Patrón no clasificable — factor edáfico permanente probable": patrón persistente que no responde a ninguna causa tratable.

### 6.3 Métricas de forma para el motor de reglas

Para clasificar patrones, el sistema necesita calcular descriptores geométricos sobre los polígonos vectorizados. Calculables con **Shapely** (ya en el stack del proyecto):

```python
# Circularidad: cercana a 1 → circular (enfermedad focal)
circularidad = (4 * pi * area) / perimetro**2

# Elongación: alta → lineal (compactación, maquinaria)
elongacion = eje_mayor / eje_menor

# Densidad de fragmentos: alta → patrón disperso (plagas, granizo)
densidad = num_poligonos / area_total
```

Métodos de Shapely a usar: `minimum_rotated_rectangle`, `convex_hull`, relaciones área/perímetro.
* * *

## 7\. Bibliografía completa

### Desde el ERS del proyecto (Drive):

*   INTA EEA Las Breñas — citada en contexto NEA
*   DJI Mavic 3 Multispectral — especificaciones técnicas del sensor
*   Rouse, J.W. et al. (1974). _Monitoring Vegetation Systems in the Great Plains with ERTS_. — NDVI original
*   FAO. _Agricultura de precisión y uso eficiente de insumos agrícolas_.

### Bibliografía adicional:

*   Whelan, B.M. & McBratney, A.B. (2000). _The "null hypothesis" of precision agriculture management_. Precision Agriculture, 2(3), 265–279.
*   Carmona, M. & Gally, M. (2004). _Roya de la soja: guía práctica para su reconocimiento y manejo_. Facultad de Agronomía UBA.
*   Salvagiotti, F. et al. (2008). _Nitrogen uptake, fixation and response to fertilization in soybeans_. Field Crops Research, 108(1), 1–13.
*   Gitelson, A.A. et al. (2006). _Relationships between gross primary production, green LAI, and canopy chlorophyll content_. Remote Sensing of Environment, 144, 65–72.
*   Lipiec, J. & Hatano, R. (2003). _Quantification of compaction effects on soil physical properties and crop growth_. Geoderma, 116(1-2), 107–136.
*   Borrás, L. et al. (2003). _Soybean stem elongation and flood tolerance_. Field Crops Research, 83(2), 143–151.
*   Landa, B.B. et al. (2006). _Influence of temperature on plant-parasitic nematode spatial patterns_. Phytopathology, 96(1), 97–104.
*   Wrather, J.A. & Koenning, S.R. (2006). _Estimates of disease effects on soybean yields in the United States_. Journal of Nematology, 38(2), 173–180.
*   Ploper, L.D. et al. (2010). _Principales enfermedades de la soja en Argentina_. INTA EEA Manfredi / AAPRESID.
*   Bragachini, M. et al. (2012). _Agricultura de precisión: siembra variable y prescripción de insumos_. INTA PRECOP.
*   Vigna, M. & Gigón, R. (2014). _Malezas resistentes en Argentina: diagnóstico y estrategias_. INTA EEA Bordenave.
*   INTA SINAVIMO (2024). Monitoreo de plagas y enfermedades. [https://www.sinavimo.gob.ar](https://www.sinavimo.gob.ar)
*   INTA EEA Sáenz Peña (2021). _Nematodos parásitos de cultivos en el Chaco: diagnóstico y estrategias de manejo_.
*   INTA EEA Las Breñas (2019). _Manejo del anegamiento en cultivos extensivos del Chaco semiárido_.
*   INTA EEA Las Breñas (2018). _Caracterización de suelos problemáticos en el Chaco semiárido_.

# Stack Tecnológico

# Stack Tecnológico — AgroNexo
## Arquitectura general
El sistema sigue una **arquitectura monolítica modular** organizada en cuatro capas bien diferenciadas: Frontend, Backend (capa de aplicación), Procesamiento y Datos. Toda la infraestructura corre sobre Docker, lo que garantiza portabilidad y reproducibilidad del entorno.
La separación entre el Backend y el Worker GIS es la decisión de diseño más importante: el procesamiento de archivos GeoTIFF (que puede tomar minutos y consumir mucha memoria) ocurre de forma asíncrona en workers independientes, sin bloquear la API principal ni degradar la experiencia del usuario.
![](https://t90171211803.p.clickup-attachments.com/t90171211803/9ff27aeb-5ff3-443d-8959-b30afe661cbf/image.png)
* * *
## Capas y tecnologías
### Frontend

| Tecnología | Rol |
| ---| --- |
| React | Framework principal de UI |
| Leaflet | Visualización de mapas y capas GIS |
| Tailwind CSS | Sistema de estilos y diseño visual |

**React** fue elegido por su ecosistema maduro, la facilidad para manejar estado complejo (resultados de análisis, capas de mapa, polling de procesamiento) y la disponibilidad de librerías especializadas para este dominio.
**Leaflet** (vía React-Leaflet) es la solución estándar de código abierto para mapas interactivos en web. Permite renderizar polígonos GeoJSON con estilos por clase, superponer capas raster de índices (NDVI como pseudocolor) y mostrar popups con estadísticas por zona. Es liviano y no requiere API key externa a diferencia de Google Maps o Mapbox.
**Tailwind CSS** permite construir interfaces consistentes y responsivas sin escribir CSS custom, lo que es importante para un equipo pequeño que necesita moverse rápido.
El Frontend se comunica con el Backend exclusivamente mediante **REST API + GeoJSON**. El GeoJSON es el formato estándar para intercambiar geometrías georreferenciadas entre backend y mapa, lo que elimina conversiones innecesarias.
* * *
### Capa de Aplicación — Backend

| Tecnología | Rol |
| ---| --- |
| FastAPI | Framework web y API REST |
| Redis | Broker de mensajes y caché |
| Celery | Cola de tareas asíncronas |

**FastAPI** fue elegido sobre Django REST Framework o Flask por tres razones concretas: generación automática de documentación OpenAPI/Swagger, validación de datos con Pydantic sin configuración extra, y rendimiento asíncrono nativo con async/await. Para un sistema que maneja uploads de archivos grandes y polling frecuente de estado, esto es relevante.
FastAPI concentra: autenticación (JWT), gestión de lotes y vuelos, coordinación de análisis, generación de reportes y el motor de diagnóstico (lógica de reglas agronómicas + integración futura con LLM).
**Redis** cumple un doble rol en el sistema: actúa como broker de mensajes para Celery (comunica el backend con los workers) y como caché de estado temporal (permite que el frontend haga polling del progreso de un análisis sin consultar la base de datos en cada request). Ambos roles conviven en la misma instancia usando bases de datos internas separadas.
**Celery** es el orquestador de tareas asíncronas. Cuando un usuario sube un GeoTIFF y solicita un análisis, FastAPI no lo procesa directamente: encola la tarea en Redis y Celery la distribuye a los workers disponibles. Esto permite paralelizar múltiples análisis, reintentar tareas fallidas automáticamente y no bloquear la API principal durante el procesamiento.
* * *
### Capa de Procesamiento — Worker GIS

| Tecnología | Rol |
| ---| --- |
| GDAL | Abstracción de datos geoespaciales |
| Rasterio | Lectura y escritura de archivos raster |
| NumPy | Operaciones matemáticas pixel a pixel |
| GeoPandas | Manipulación y exportación de datos vectoriales |
| Shapely | Operaciones geométricas sobre polígonos |

Este bloque se ejecuta dentro de los **workers Celery**, completamente separado del proceso de FastAPI. Es el núcleo técnico del sistema.
**GDAL** es la librería base de todo el ecosistema geoespacial open source. Rasterio la usa internamente para leer GeoTIFF, reproyectar coordenadas y vectorizar rasters. No se usa directamente en el código de la aplicación, pero es una dependencia fundamental.
**Rasterio** es la interfaz Python estándar para trabajar con archivos raster georreferenciados. Permite leer bandas espectrales individualmente, acceder a metadatos (CRS, resolución, extensión), aplicar enmascaramiento de zonas sin datos y vectorizar el raster clasificado mediante `rasterio.features.shapes()`. Se usa para GeoTIFF de hasta 1 GB mediante windowed reading (lectura por tiles) para no cargar el archivo completo en memoria.
**NumPy** realiza los cálculos de índices de vegetación como operaciones matriciales sobre arrays de píxeles. El cálculo de NDVI, por ejemplo, opera sobre dos matrices (banda NIR y banda RED) simultáneamente, lo que es órdenes de magnitud más rápido que un bucle pixel a pixel. También maneja el enmascaramiento de valores nodata y la división por cero.
**GeoPandas** trabaja con los polígonos resultantes de la vectorización: calcula áreas en hectáreas, aplica filtros por área mínima para eliminar ruido, exporta en GeoJSON (para la API) y en Shapefile comprimido en `.zip` (para uso en maquinaria agrícola). Extiende Pandas con soporte geoespacial nativo.
**Shapely** realiza las operaciones geométricas sobre los polígonos: simplificación con el algoritmo Douglas-Peucker (para reducir vértices sin perder la forma de la zona), validación de geometrías y análisis espacial (cálculo de compacidad, circularidad y detección de clusters de zonas afectadas).
* * *
### Capa de Datos

| Tecnología | Rol |
| ---| --- |
| PostgreSQL + PostGIS | Base de datos relacional con extensión espacial |
| MinIO | Almacenamiento de archivos (S3-compatible) |

**PostgreSQL** es la base de datos relacional principal. Almacena usuarios, permisos, lotes, vuelos, índices calculados, metadatos e historial de análisis. Se eligió sobre MySQL por su mejor soporte de tipos de datos complejos y por la disponibilidad de PostGIS.
**PostGIS** es la extensión espacial de PostgreSQL. Permite almacenar geometrías (polígonos de zonas clasificadas) como tipos de datos nativos, realizar consultas espaciales eficientes (intersección, contención, distancia) y mantener índices GiST que aceleran las búsquedas geoespaciales. Es el estándar de la industria para bases de datos espaciales open source.
La separación de responsabilidades es clara: PostGIS guarda los **metadatos y vectores** (quién, qué lote, qué fecha, qué polígonos, qué estadísticas), mientras que MinIO guarda los **archivos binarios** (ortomosaicos originales, mapas generados, reportes PDF, Shapefiles exportados).
**MinIO** es un servidor de almacenamiento de objetos compatible con la API de Amazon S3, desplegable en infraestructura propia. Se eligió porque los GeoTIFF pueden pesar varios cientos de megabytes y los reportes generados (PDFs, Shapefiles, mapas de prescripción) no deben ocupar espacio en la base de datos relacional. Organiza los archivos en la estructura `usuario/lote/vuelo/` y genera URLs firmadas de acceso temporario para que el frontend pueda descargar archivos directamente sin pasar por el backend.
* * *
### Infraestructura

| Tecnología | Rol |
| ---| --- |
| Docker / Docker Compose | Contenedores y orquestación local |

**Docker** empaqueta cada componente del sistema (FastAPI, Worker GIS, Redis, PostgreSQL+PostGIS, MinIO) en contenedores independientes con sus dependencias. Esto garantiza que el entorno de desarrollo sea idéntico al de producción, elimina los problemas de "funciona en mi máquina" y simplifica el despliegue.
**Docker Compose** orquesta todos los contenedores localmente, define la red interna entre servicios, gestiona variables de entorno y volúmenes persistentes para la base de datos y el almacenamiento de archivos.
En la etapa de producción (R7) se añadirá **Nginx** como reverse proxy y gateway de entrada, encargándose de SSL/TLS, compresión y ruteo de tráfico hacia los distintos servicios.
* * *
## Resumen de decisiones de diseño

| Decisión | Alternativa descartada | Razón |
| ---| ---| --- |
| FastAPI sobre Django REST | Django REST Framework | Validación automática con Pydantic, async nativo, documentación OpenAPI sin configuración |
| Celery + Redis para procesamiento | Procesamiento sincrónico en FastAPI | Los GeoTIFF grandes bloquearían la API; necesidad de reintentos y paralelismo |
| PostGIS para vectores | Archivos GeoJSON en disco | Consultas espaciales, índices GiST, historial y trazabilidad de análisis |
| MinIO para archivos | Sistema de archivos local | Escalabilidad, URLs firmadas, separación de responsabilidades con la BD |
| Rasterio sobre GDAL directo | GDAL Python bindings | API más pythónica, mejor manejo de contextos y memoria |
| React sobre Vue/Angular | Vue.js | Ecosistema más amplio, librerías GIS más maduras (React-Leaflet) |

# Investigación fumigación localizada

Técnicas de prescripción diferenciada. Normativa vigente e integración con sistemas GIS.

La digitalización del agro ha transformado por completo la forma en que intervenimos en los lotes. La posibilidad de realizar una fumigación localizada y aplicar técnicas de prescripción diferenciada (también conocida como Aplicación Variable o _VRA - Variable Rate Application_) es uno de los mayores hitos de la Agricultura de Precisión.
A continuación, profundizamos en cómo se estructuran estas técnicas, el marco normativo que las regula y cómo se integran con los Sistemas de Información Geográfica (GIS).
## 1\. Técnicas de Prescripción Diferenciada
La prescripción diferenciada consiste en aplicar la dosis exacta de un insumo (herbicidas, fungicidas, fertilizantes) en el lugar y momento adecuados, rompiendo con la vieja costumbre de tratar el lote de forma homogénea. Existen dos enfoques principales para implementarla:
### A. Prescripción basada en Mapas (Offline)
Es el método más utilizado. Se realiza un análisis previo en la oficina técnica para generar un mapa de prescripción que luego se carga en el monitor de la maquinaria agrícola.
*   Fuentes de información: Se combinan índices como el NDVI (para vigor y densidad biomasa), el NDRE (para cultivos densos), mapas de rendimiento de campañas anteriores, muestreos de suelo y altimetría.
*   Fungicidas: Como mencionaba el documento, se zonifica el lote según el índice de vegetación para aplicar dosis completas en focos de infección o preventivas diferenciadas según la densidad foliar.
*   Herbicidas (Maleza dirigida): Se procesan imágenes satelitales de alta resolución o vuelos de drones semanas antes de la senescencia o en postcosecha para identificar manchones de malezas, generando un mapa de prescripción que le dice a la pulverizadora exactamente dónde abrir los botalones.
### B. Prescripción basada en Sensores en Tiempo Real (Online)
No requiere un mapa previo. La maquinaria cuenta con sensores ópticos activos montados directamente sobre el botalón de aplicación.
*   Funcionamiento: Los sensores (como _WeedSeeker_ o _WEED-IT_) emiten su propia luz y miden la reflectancia del suelo milisegundo a milisegundo. Al detectar el pulso característico de la clorofila de una maleza, envían una señal ultra rápida a las electrobálvulas de los picos pulverizadores, abriéndose únicamente sobre la maleza.
*   Ahorro: Esta técnica permite ahorrar hasta un 60% a 90% de producto químico en barbechos, reduciendo drásticamente el impacto ambiental y los costos operativos.
## 2\. Integración con Sistemas GIS y Flujo de Trabajo
Para que los datos recolectados en el espacio se traduzcan en una orden mecánica para la pulverizadora, se sigue un flujo de trabajo GIS muy estructurado:

```css
[Datos Satélite/Dron] ➔ [Procesamiento GIS/Zonificación] ➔ [Exportación SHP/ISO-XML] ➔ [Monitor del Tractor/VRA]
```

1. Adquisición y Preprocesamiento: Se descargan las imágenes (por ejemplo, de Sentinel-2 o Landsat) y se calculan los índices correspondientes ($NDVI$, $EVI$, $NDRE$).
2. Zonificación (Clasificación): En un software GIS (como QGIS, ArcGIS o plataformas agronómicas como Auravant, Agricolus, etc.) se agrupan los píxeles con valores similares mediante algoritmos de _clustering_ (ej. K-means). Esto divide el lote en zonas de "Alto", "Medio" y "Bajo" potencial o presencia.
3. Asignación de Dosis: El agrónomo asigna manualmente la cantidad de principio activo (L/ha) o caldo que corresponde a cada zona basándose en su criterio técnico.
4. Exportación de Archivos: El mapa resultante se exporta en formatos compatibles con las computadoras de campo. Los formatos estándar de la industria son:
    *   Shapefile (`.shp`): El formato clásico de vectores GIS.
    *   ISO-XML: El estándar global para la interoperabilidad de maquinaria agrícola (ISOBUS), que permite que tractores y pulverizadoras de diferentes marcas entiendan el mismo archivo de prescripción de forma directa.
## 3\. Normativa Vigente (Uso Seguro y Responsable)
El uso de tecnologías de precisión facilita enormemente el cumplimiento de las normativas vigentes, ya que disminuye la deriva y evita la sobreaplicación. En el contexto regulatorio (tomando como referencia el marco general argentino y de América Latina), destacan los siguientes pilares obligatorios:
*   Registro Obligatorio ante Autoridades (SENASA): Todo producto fitosanitario o agroquímico a aplicar debe estar estrictamente registrado y homologado por las autoridades competentes para el cultivo específico. Está prohibida la tenencia o dosificación de productos vencidos o prohibidos.
*   Receta Agronómica Digital (RAD) / Recomendación Técnica: Es obligatorio que toda aplicación esté respaldada por una receta emitida y firmada por un Ingeniero Agrónomo matriculado (Asesor Fitosanitario). La ventaja de la prescripción diferenciada es que la receta digital puede adjuntar directamente el mapa de GIS como justificación técnica de las dosis aplicadas.
*   Zonas de Exclusión y Amortiguamiento (Buffer Zones): Las normativas (provinciales y municipales) establecen distancias mínimas para aplicaciones terrestres y aéreas respecto a zonas urbanas, escuelas rurales y cursos de agua. Mediante el software GIS, se pueden programar zonas de "cero aplicación" (exclusiones) en el mapa de prescripción, asegurando que la pulverizadora se apague automáticamente de forma georreferenciada al acercarse a estas áreas sensibles, eliminando el error humano.
*   Gestión de Envases y Residuos: Leyes como la de Gestión de Envases Vacíos de Fitosanitarios exigen el triple lavado obligatorio, la perforación de los envases y su canalización a través de Centros de Almacenamiento Transitorios (CAT) para evitar la contaminación de recursos hídricos.
La combinación de plataformas GIS, índices de vegetación e inteligencia artificial aplicada a la maquinaria no sólo maximiza el rendimiento económico del lote, sino que se ha convertido en la herramienta principal para demostrar la sustentabilidad y el cumplimiento legal de cara a las crecientes exigencias socioambientales.

# Especificación APIs REST (OpenAPI)

# Especificación de APIs REST (OpenAPI) — AgroNexo

**Sprint:** Sprint 2 · R1 · Discovery & Arquitectura
**Asignado:** Matias Machado | **Fecha límite:** 21/06/2026 | **Estimación:** 10h
**Backend:** FastAPI · `app/auth` · `app/lotes` · `app/ingesta` · `app/diagnostico` · `app/reportes`
> **URL Base:** `/api/v1`
* * *

## 1\. Introducción

Este documento especifica los endpoints de la API REST de AgroNexo, alineados con la **Arquitectura de Módulos y Responsabilidades**. Sirve como contrato entre el backend (FastAPI) y el frontend (React), y como referencia para las tareas de implementación del R2 · Backend Core.

### ¿Qué es una API REST y para qué sirve en AgroNexo?

Pensá en AgroNexo como un restaurante. El **frontend** (la pantalla que ve el usuario en el navegador) es el salón donde están los clientes. El **backend** (FastAPI) es la cocina donde se prepara todo — se calculan los índices NDVI, se generan los mapas, se aplica el motor de diagnóstico. La **API REST** es el mozo: el único canal oficial que puede ir y venir entre el salón y la cocina, llevando pedidos y trayendo resultados.

El frontend **nunca** habla directamente con la base de datos (Supabase/PostGIS), ni con el almacenamiento de archivos (MinIO), ni con el procesador de imágenes (Worker GIS). Todo pasa obligatoriamente por la API. Esto tiene una razón muy concreta: si el día de mañana cambia la base de datos, o se agrega una app móvil, o se integra un tercero, la API sigue siendo la misma interfaz — solo cambia lo que hay adentro.

### ¿Cómo hace un "pedido" el frontend?

Cada pedido se llama **request** (solicitud) y tiene tres partes fundamentales:

**1\. El método HTTP** — dice qué tipo de acción querés hacer sobre un recurso:

| Método | Significado | Ejemplo en AgroNexo |
| ---| ---| --- |
| `GET` | Quiero leer algo, sin modificar nada | "Mostrame mis lotes" |
| `POST` | Quiero crear algo nuevo | "Creá un nuevo lote" / "Subí este GeoTIFF" |
| `PUT` | Quiero reemplazar completamente un recurso | "Reemplazá todos los datos de este lote" |
| `PATCH` | Quiero modificar solo una parte de un recurso | "Agregá este comentario al diagnóstico" |
| `DELETE` | Quiero eliminar un recurso | "Borrá este lote" |

**2\. La ruta** — dice _sobre qué recurso específico_ querés actuar. La ruta es como una dirección:

```sql
GET    /api/v1/lotes              → traeme TODOS mis lotes
GET    /api/v1/lotes/abc-123      → traeme SOLO el lote con ID abc-123
POST   /api/v1/lotes              → creá un nuevo lote
PUT    /api/v1/lotes/abc-123      → actualizá el lote abc-123
DELETE /api/v1/lotes/abc-123      → borrá el lote abc-123
```

El `/api/v1` al principio es un prefijo que indica "versión 1 de la API". Si en el futuro la API cambia de forma incompatible, se haría `/api/v2` sin romper lo anterior. Los `{lote_id}`, `{vuelo_id}`, etc. entre llaves son **parámetros de ruta** — se reemplazan con el ID real del recurso en cada request.

**3\. El body** — cuando creás o modificás algo, mandás los datos en el cuerpo del pedido, en formato **JSON**:

```json
{
  "nombre": "Lote Norte",
  "cultivo": "soja",
  "estadio_fenologico": "R3",
  "area_ha": 42.5
}
```

Para los uploads de archivos (como el GeoTIFF), se usa `multipart/form-data` — el mismo mecanismo que usa un formulario web cuando subís un archivo.

### ¿Qué responde el backend?

Siempre devuelve dos cosas: un **código de estado HTTP** (número que dice si salió bien o qué tipo de error ocurrió) y un **body de respuesta** con los datos en JSON (o un archivo en el caso de exportaciones).

### ¿Qué es el JWT y por qué cada endpoint lo requiere?

JWT (JSON Web Token) es un sistema de identificación. Cuando un usuario hace login, el backend genera un token — una cadena larga de texto codificada — que contiene quién es el usuario y cuándo expira el acceso. En **cada request** el frontend manda ese token en el header:

```erlang
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

El backend lo verifica criptográficamente e identifica al usuario. Esto garantiza que cada usuario vea **solo sus propios lotes y análisis**. Si el token expiró (30 minutos), el backend devuelve `401 Unauthorized` y el frontend debe pedir uno nuevo usando el `refresh_token` (que dura 7 días).

### El flujo completo del sistema

```python
1. Login
   POST /api/v1/auth/login
   → recibe access_token + refresh_token

2. Crear el lote
   POST /api/v1/lotes  (con el polígono del campo en GeoJSON)
   → recibe ID del lote

3. Subir el GeoTIFF del dron
   POST /api/v1/lotes/{lote_id}/vuelos  (archivo + metadatos del vuelo)
   → el backend valida, guarda en MinIO, devuelve ID del vuelo

4. Iniciar el procesamiento
   POST /api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/analisis
   → el backend encola en Celery y devuelve 202 inmediatamente

5. Consultar el progreso cada 10 segundos
   GET .../analisis/{analisis_id}/estado
   → "procesando 65%... Calculando NDVI..."
   → "completado"

6. Ver el diagnóstico
   GET .../analisis/{analisis_id}/diagnostico
   → zonas detectadas, causas probables, dosis recomendada por zona

7. Descargar el Shapefile para la máquina
   GET /api/v1/analisis/{analisis_id}/reportes/shapefile
   → archivo .zip listo para la consola del tractor
```

### Convenciones del documento

*   **Base URL:** `/api/v1` — todos los endpoints llevan este prefijo
*   **Autenticación:** `Authorization: Bearer <token>` (JWT) en endpoints marcados como "JWT"
*   **Formato:** `Content-Type: application/json`, excepto uploads (`multipart/form-data`)
*   **IDs:** UUID v4 en todos los recursos · **Fechas:** ISO 8601 (`"2026-06-12T10:30:00Z"`)
*   **`access_token`** expira en 30 minutos (RNF-09) · **`refresh_token`** en 7 días
* * *

## 2\. Módulos de la API

La API está dividida en 5 módulos, cada uno con su propia carpeta en el backend. Esta división no es arbitraria: cada módulo tiene una responsabilidad única y bien delimitada, lo que facilita el trabajo en equipo y el mantenimiento futuro.

### ¿Por qué separar en módulos?

En FastAPI, cada módulo es un **router** — un conjunto de endpoints agrupados bajo un prefijo de ruta. El archivo principal `main.py` simplemente los registra:

```python
app.include_router(auth_router,        prefix="/api/v1/auth")
app.include_router(lotes_router,       prefix="/api/v1/lotes")
app.include_router(ingesta_router)
app.include_router(diagnostico_router)
app.include_router(reportes_router)
```

Si mañana hay que cambiar la lógica del diagnóstico, solo se toca `app/diagnostico/` — nada más. Esto es **bajo acoplamiento**: los módulos son independientes entre sí.

### ¿Qué son los "RNF", "RFGL", etc.?

Son los identificadores de requisitos definidos en el ERS:

*   **RNF** = Requisito No Funcional (seguridad, performance, disponibilidad)
*   **RFGL** = Requisito Funcional de Gestión de Lotes
*   **RFME** = Requisito Funcional de Manejo de Imágenes
*   **RFMA** = Requisito Funcional de Módulo de Análisis
*   **RFDR** = Requisito Funcional de Diagnóstico y Recomendaciones
*   **RFSA** = Requisito Funcional de Salidas y Archivos

Cada endpoint existe porque hay un requisito que lo justifica.

| Módulo API | Carpeta backend | Responsabilidad | Prefijo de rutas | Req. principales |
| ---| ---| ---| ---| --- |
| Auth | `app/auth/` | Registro, login, JWT, sesiones | `/api/v1/auth` | RNF-05..09 |
| Gestión de Lotes | `app/lotes/` | CRUD lotes + sub-recursos vuelos + historial | `/api/v1/lotes` | RFGL-01..05, RFME-01 |
| Ingesta y Validación | `app/ingesta/` | Upload GeoTIFF → MinIO, validación, encolar Celery, polling | `/api/v1/lotes/{id}/vuelos/{id}/analisis` | RFME-01..04, RFMA-01..04 |
| Diagnóstico | `app/diagnostico/` | Resultados Worker, motor de reglas, prescripción | `/api/v1/lotes/{id}/vuelos/{id}/analisis/{id}` | RFDR-01..05, RFMP-02..04 |
| Reportes y Exportación | `app/reportes/` | PDF, Shapefile, ISO-XML, Orden de Trabajo, Certificación | `/api/v1/analisis/{id}/reportes` | RFSA-01..04, RNF-26 |

* * *

## 3\. Especificación por módulo

### 3.1 Módulo Auth — `app/auth/`

Gestiona el ciclo de vida de la autenticación: quién puede entrar al sistema, con qué permisos, y por cuánto tiempo.
> **Requisitos:** RNF-05, RNF-06, RNF-07, RNF-08, RNF-09, RFGL-01

#### ¿Qué hace este módulo y por qué es el más importante?

Auth es el guardián de toda la API. Antes de que cualquier otro módulo procese un request, el **middleware de autenticación** verifica que el token JWT sea válido. Si no lo es, el request ni siquiera llega al módulo de Lotes o Diagnóstico — se corta antes.

En código FastAPI, esto se implementa como una **dependencia** que se inyecta en cada endpoint protegido:

```python
@router.get("/lotes")
async def listar_lotes(current_user: User = Depends(get_current_user)):
    # Si el token es inválido, get_current_user lanza 401 antes de llegar acá
    return lotes_service.listar(user_id=current_user.id)
```

#### ¿Cómo funciona el ciclo de tokens?

```css
1. register  → se crea la cuenta
2. login     → recibe access_token (30min) + refresh_token (7 días)
3. requests  → manda access_token en cada header Authorization
4. a los 30min → frontend detecta 401 → llama a /auth/refresh
5. a los 7 días → refresh_token expira → usuario debe hacer login de nuevo
6. logout    → refresh_token se invalida en la base de datos
```

| Método | Ruta | Descripción | Auth | Códigos |
| ---| ---| ---| ---| --- |
| `POST` | `/api/v1/auth/register` | Registrar nuevo usuario | Público | 201, 400, 409 |
| `POST` | `/api/v1/auth/login` | Autenticar usuario, obtener tokens JWT | Público | 200, 401, 422 |
| `POST` | `/api/v1/auth/refresh` | Renovar access token con refresh token | Público | 200, 401 |
| `POST` | `/api/v1/auth/logout` | Invalidar sesión activa del usuario | JWT | 204, 401 |
| `GET` | `/api/v1/auth/me` | Obtener perfil del usuario autenticado | JWT | 200, 401 |

**POST** **`/api/v1/auth/register`**

Crea una cuenta nueva. El backend hashea la contraseña con bcrypt — nunca se almacena en texto plano. Si el email ya existe devuelve `409 Conflict` (no `400`) para distinguir "datos inválidos" de "recurso ya existente".

```json
// Request Body
{ "nombre": "Matias Machado", "email": "mati@agronexo.com", "password": "miContraseña123" }

// Response 201 Created
{ "id": "3f2a1b4c-...", "nombre": "Matias Machado", "email": "mati@agronexo.com", "created_at": "2026-06-12T10:30:00Z" }
```

**POST** **`/api/v1/auth/login`**

Verifica las credenciales y genera el par de tokens. El `access_token` se usa en todos los requests posteriores.

```json
// Request Body
{ "email": "mati@agronexo.com", "password": "miContraseña123" }

// Response 200 OK
{ "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "refresh_token": "dGhpcyBpcyBh...", "token_type": "bearer" }
```

**POST** **`/api/v1/auth/refresh`**

Renueva el access\_token sin que el usuario tenga que hacer login. El frontend lo llama automáticamente cuando detecta un `401`.

```json
// Request Body
{ "refresh_token": "dGhpcyBpcyBh..." }

// Response 200 OK
{ "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...nuevo...", "expires_in": 1800 }
```

**POST** **`/api/v1/auth/logout`** → `204 No Content` (sin body)

**GET** **`/api/v1/auth/me`** — el frontend lo llama al cargar la app para saber quién está logueado.

```json
// Response 200 OK
{ "id": "3f2a1b4c-...", "nombre": "Matias Machado", "email": "mati@agronexo.com", "created_at": "2026-06-12T10:30:00Z" }
```

* * *

### 3.2 Módulo Gestión de Lotes — `app/lotes/`

Administra el inventario de lotes agrícolas con sus límites geográficos, contexto agronómico e historial de intervenciones. Los vuelos son sub-recursos del lote.
> **Requisitos:** RFGL-01, RFGL-02, RFGL-03, RFGL-04, RFME-03, RNF-19

#### ¿Qué es un lote en AgroNexo?

Un lote es la unidad básica de trabajo: un campo agrícola delimitado geográficamente. En la base de datos se almacena con:

*   **Datos agronómicos:** cultivo (soja, maíz...), estadio fenológico (V3, R1, R3...) — necesarios para que el motor de diagnóstico aplique las reglas correctas para ese cultivo en ese momento del ciclo.
*   **Geometría (PostGIS):** el polígono que delimita el campo en formato `GEOMETRY(Polygon, 4326)`. El `4326` es el sistema de coordenadas WGS84, el mismo que usa Google Maps. PostGIS puede calcular el área automáticamente y superponer capas de análisis.
*   **Historial:** cada vuelo, análisis o aplicación se registra como una intervención vinculada al lote.

#### ¿Qué es GeoJSON?

GeoJSON es el estándar para representar formas geográficas en JSON. Un polígono de lote se ve así:

```json
{
  "type": "Polygon",
  "coordinates": [[
    [-60.6753, -27.4693],
    [-60.6701, -27.4693],
    [-60.6701, -27.4741],
    [-60.6753, -27.4741],
    [-60.6753, -27.4693]
  ]]
}
```

Cada par `[longitud, latitud]` es un punto. El primero y el último son iguales para cerrar el polígono.

#### ¿Qué es el soft delete?

Cuando el usuario "borra" un lote, no se elimina el registro de la base de datos — solo se marca con un campo `deleted_at`. Esto preserva el historial de análisis y diagnósticos vinculados, y permite recuperar el lote si fue borrado por error.

#### ¿Por qué los vuelos son sub-recursos de lotes?

Porque un vuelo siempre pertenece a un lote específico. La ruta `/lotes/{lote_id}/vuelos` refleja esta jerarquía: "dame los vuelos de _este_ lote". En la base de datos, la tabla `vuelos` tiene una foreign key `lote_id` apuntando a `lotes.id`.

| Método | Ruta | Descripción | Auth | Códigos |
| ---| ---| ---| ---| --- |
| `GET` | `/api/v1/lotes` | Listar todos los lotes del usuario | JWT | 200, 401 |
| `POST` | `/api/v1/lotes` | Crear nuevo lote con geometría GeoJSON | JWT | 201, 400, 401, 422 |
| `GET` | `/api/v1/lotes/{lote_id}` | Obtener detalle de un lote | JWT | 200, 401, 403, 404 |
| `PUT` | `/api/v1/lotes/{lote_id}` | Actualizar nombre, cultivo, estadio | JWT | 200, 400, 401, 403, 404 |
| `DELETE` | `/api/v1/lotes/{lote_id}` | Eliminar lote (soft delete) | JWT | 204, 401, 403, 404 |
| `GET` | `/api/v1/lotes/{lote_id}/historial` | Línea de tiempo de intervenciones | JWT | 200, 401, 403, 404 |
| `GET` | `/api/v1/lotes/{lote_id}/vuelos` | Listar vuelos de un lote | JWT | 200, 401, 403, 404 |
| `GET` | `/api/v1/lotes/{lote_id}/vuelos/{vuelo_id}` | Detalle y metadatos de un vuelo | JWT | 200, 401, 403, 404 |

**POST** **`/api/v1/lotes`**

El backend calcula automáticamente el área en hectáreas usando PostGIS (`ST_Area`) a partir del polígono enviado.

```json
// Request Body
{
  "nombre": "Lote Norte",
  "cultivo": "soja",
  "estadio_fenologico": "R3",
  "geometry": { "type": "Polygon", "coordinates": [[[-60.6753, -27.4693], [-60.6701, -27.4693], [-60.6701, -27.4741], [-60.6753, -27.4741], [-60.6753, -27.4693]]] },
  "srid": 4326
}

// Response 201 Created
{ "id": "abc-123", "nombre": "Lote Norte", "cultivo": "soja", "area_ha": 42.5, "geometry": {...}, "created_at": "2026-06-12T10:30:00Z" }
```

**GET** **`/api/v1/lotes/{lote_id}/historial`** — línea de tiempo completa del lote

```json
// Response 200 OK
{
  "lote_id": "abc-123",
  "intervenciones": [
    { "tipo": "vuelo", "fecha": "2026-05-10T08:00:00Z", "referencia_id": "vuelo-xyz", "descripcion": "Vuelo multiespectral 80m" },
    { "tipo": "analisis", "fecha": "2026-05-10T09:15:00Z", "referencia_id": "analisis-qrs", "descripcion": "NDVI + NDRE — 35% área con anomalía" },
    { "tipo": "aplicacion", "fecha": "2026-05-12T06:00:00Z", "referencia_id": "cert-mnop", "descripcion": "Aplicación zona norte — 28% ahorro" }
  ]
}
```

**GET** **`/api/v1/lotes/{lote_id}/vuelos/{vuelo_id}`**

Las `bandas_detectadas` son clave: el sistema verifica que el GeoTIFF tenga la banda NIR porque sin ella no se puede calcular NDVI. El `crs` EPSG:32720 es la proyección estándar para la zona de Argentina.

```json
// Response 200 OK
{
  "id": "vuelo-xyz", "lote_id": "abc-123", "fecha_vuelo": "2026-05-10T08:00:00Z",
  "sensor": "Multiespectral", "altitud_m": 80,
  "bandas_detectadas": ["RED", "GREEN", "BLUE", "NIR"],
  "crs": "EPSG:32720",
  "preview_url": "https://minio.agronexo.com/previews/vuelo-xyz.jpg",
  "estado": "valido"
}
```

* * *

### 3.3 Módulo Ingesta y Validación — `app/ingesta/`

Recibe el GeoTIFF del dron vía upload HTTP, valida metadatos (bandas, CRS, integridad), lo almacena en MinIO y encola la tarea de procesamiento en Celery. Expone el endpoint de polling para que el frontend muestre el progreso.
> **Requisitos:** RFME-01, RFME-02, RFME-04, RFMA-01..04, RNF-04, RNF-15, RNF-17

#### ¿Qué es un GeoTIFF?

Un GeoTIFF es una imagen de dron o satélite en formato TIFF con metadatos geográficos embebidos: sabe exactamente dónde está en el mundo, en qué proyección cartográfica, y cuántos metros de terreno representa cada píxel. A diferencia de un JPEG normal, puede tener múltiples bandas espectrales — en AgroNexo necesitamos al menos RED y NIR para calcular NDVI.

#### ¿Qué es MinIO y por qué se usa para los GeoTIFF?

MinIO es un servidor de almacenamiento de objetos compatible con Amazon S3. Los GeoTIFF pueden pesar entre 500 MB y 1 GB — demasiado para guardarlos en una base de datos relacional. MinIO los almacena como objetos con una URL de acceso firmada (con token temporal) para que solo el usuario autorizado pueda descargar el archivo.

Ruta en MinIO: `usuario/{user_id}/lote/{lote_id}/vuelo/{vuelo_id}/ortomosaico.tif`

#### ¿Qué es Celery y por qué se usa procesamiento asíncrono?

Celery es un sistema de colas de tareas. Procesar un GeoTIFF puede tardar entre 30 segundos y varios minutos. Si el backend esperara ese tiempo antes de responder, el frontend pensaría que la conexión falló.

La solución es asíncrona: el backend recibe el request, encola la tarea en Redis, responde inmediatamente con `202 Accepted`, y el Worker GIS procesa en segundo plano. El frontend hace polling cada 10 segundos hasta que la tarea termine.

```gherkin
Frontend       Backend (FastAPI)      Redis        Worker GIS
   |                   |                  |               |
   |-- POST /analisis->|                  |               |
   |                   |-- encolar ------>|               |
   |<-- 202 Accepted---|                  |-- ejecutar -->|
   |                   |                  |               |
   |-- GET /estado --->|                  |               |
   |<-- "35%" ---------|<-- leer Redis ---|<-- update 35% |
   |-- GET /estado --->|                  |               |
   |<-- "completado" --|<-- leer Redis ---|<-- "done" ----|
```

| Método | Ruta | Descripción | Auth | Códigos |
| ---| ---| ---| ---| --- |
| `POST` | `/api/v1/lotes/{lote_id}/vuelos` | Upload GeoTIFF → MinIO + registrar vuelo | JWT | 201, 400, 401, 413, 422 |
| `POST` | `/api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/analisis` | Encolar análisis en Celery (Worker GIS) | JWT | 202, 400, 401, 404, 409 |
| `GET` | `/api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/analisis/{analisis_id}/estado` | Polling de estado (cada 10s) | JWT | 200, 401, 404 |

**POST** **`/api/v1/lotes/{lote_id}/vuelos`** — `multipart/form-data`

El proceso interno: 1) verificar que no supere 1 GB → 2) abrir con Rasterio y verificar bandas y CRS → 3) generar preview low-res → 4) subir a MinIO → 5) guardar en tabla `vuelos` → 6) responder `201`.

```yaml
// Request: multipart/form-data
archivo_geotiff:  [archivo .tif, máx 1 GB — RNF-17]
fecha_vuelo:      "2026-05-10T08:00:00Z"
sensor:           "Multiespectral"
altitud_m:        80
condiciones:      "Viento 5 km/h, sin nubes" (opcional)
```

```json
// Response 201 Created
{
  "id": "vuelo-xyz", "lote_id": "abc-123", "sensor": "Multiespectral",
  "bandas_detectadas": ["RED", "GREEN", "BLUE", "NIR"], "crs": "EPSG:32720",
  "preview_url": "https://minio.agronexo.com/previews/vuelo-xyz-preview.jpg",
  "estado": "valido"
}
```

**POST** **`/api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/analisis`** — Encolar procesamiento

El `409 Conflict` se devuelve si ya existe un análisis "encolado" o "procesando" para ese vuelo.

**Sobre los índices:** NDVI mide salud del cultivo (RED vs NIR). NDRE es más sensible en estadios avanzados. SAVI corrige el efecto del suelo en lotes con baja cobertura. ExG es para cultivos sin banda NIR.
> **Sobre el método umbral:** "otsu" calcula automáticamente los umbrales estadísticos. "manual" permite que el técnico los defina.

```json
// Request Body
{
  "indices": ["NDVI", "NDRE", "SAVI", "ExG"],
  "metodo_umbral": "otsu",
  "area_minima_m2": 100,
  "simplificar_poligonos": true
}

// Response 202 Accepted
{ "analisis_id": "analisis-qrs", "estado": "encolado", "task_id": "cel-task-a1b2c3d4" }
```

**GET** **`.../analisis/{analisis_id}/estado`** — Polling de progreso

```json
// Response 200 OK
{
  "analisis_id": "analisis-qrs",
  "estado": "procesando",
  "progreso_pct": 65,
  "etapa_actual": "Vectorizando zonas NDVI...",
  "iniciado_en": "2026-05-10T09:00:00Z",
  "completado_en": null,
  "error": null
}
```

* * *

### 3.4 Módulo Diagnóstico — `app/diagnostico/`

Lee los resultados del Worker GIS desde PostGIS y aplica el motor de reglas agronómicas: índice × cultivo × estadio → causas probables y recomendaciones con dosis variable. Permite al profesional adjuntar un comentario técnico.
> **Requisitos:** RFDR-01..05, RFMP-02, RFMP-03, RFMP-04, RFGL-04, RFGL-05

#### ¿Qué es el motor de reglas agronómicas?

Es la lógica central de AgroNexo — la que convierte números (NDVI = 0.31 en zona X) en conocimiento accionable ("posible estrés hídrico, aplicar riego"). Es una tabla de reglas del estilo:

```java
SI cultivo = "soja"
   Y estadio = "R3"
   Y NDVI_zona < 0.35
ENTONCES causas_probables = ["Estrés hídrico", "Déficit de nitrógeno"]
         recomendacion = "Aplicar riego 20mm + fertilizante UAN 32%"
         confianza = 82%
```

Estas reglas se construyen a partir de bibliografía agronómica (INTA, facultades). Para el MVP es determinista — en versiones futuras podría integrarse el módulo LLM para casos no cubiertos por las reglas.

#### ¿Qué son las "zonas" del análisis?

El Worker GIS no devuelve solo un promedio — devuelve **polígonos georreferenciados** que delimitan áreas homogéneas del lote. Por ejemplo: "esta zona de 3.7 ha en el sector noreste tiene NDVI = 0.31 (bajo)". Cada zona tiene su polígono exacto en GeoJSON, que el frontend puede pintar en el mapa.

#### ¿Qué es la prescripción de dosis variable?

En lugar de aplicar la misma dosis a todo el lote, la agricultura de precisión aplica **dosis variables por zona**: más donde hay problema, menos donde el cultivo está sano. Esto reduce el uso de agroquímicos y es el valor central del sistema.

| Método | Ruta | Descripción | Auth | Códigos |
| ---| ---| ---| ---| --- |
| `GET` | `/api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/analisis/{analisis_id}` | Resultados geoespaciales (zonas, estadísticas) | JWT | 200, 401, 403, 404 |
| `GET` | `/api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/analisis/{analisis_id}/diagnostico` | Diagnóstico agronómico (motor de reglas) | JWT | 200, 401, 403, 404 |
| `PATCH` | `/api/v1/diagnostico/{diagnostico_id}/comentario` | Adjuntar comentario técnico (RFDR-04) | JWT | 200, 400, 401, 403, 404 |
| `GET` | `/api/v1/lotes/{lote_id}/vuelos/{vuelo_id}/analisis/{analisis_id}/prescripcion` | Zonas con dosis variable | JWT | 200, 401, 403, 404 |

**GET** **`.../analisis/{analisis_id}`** **— Resultados del Worker GIS**

```json
// Response 200 OK
{
  "id": "analisis-qrs", "estado": "completado",
  "indices_calculados": ["NDVI", "NDRE"],
  "zonas": [
    { "id": "zona-001", "indice": "NDVI", "categoria": "anomalia", "severidad": "alta", "valor_promedio": 0.31, "area_ha": 3.7, "geometry": { "type": "MultiPolygon", "coordinates": [...] } },
    { "id": "zona-002", "indice": "NDVI", "categoria": "alto", "severidad": null, "valor_promedio": 0.72, "area_ha": 38.8, "geometry": { "type": "MultiPolygon", "coordinates": [...] } }
  ],
  "estadisticas": { "ndvi_promedio": 0.48, "area_afectada_ha": 3.7, "area_total_ha": 42.5, "ahorro_estimado_pct": 28.9 }
}
```

**GET** **`.../analisis/{analisis_id}/diagnostico`** **— Motor de reglas**

El `confianza_pct` indica cuántas reglas aplicaron — una confianza baja significa caso atípico que conviene que un técnico revise.

```json
// Response 200 OK
{
  "analisis_id": "analisis-qrs",
  "zonas_diagnostico": [{
    "zona_id": "zona-001", "categoria": "anomalia", "severidad": "alta",
    "causas_probables": ["Estrés hídrico", "Déficit de nitrógeno"],
    "recomendacion": "Aplicar riego 20mm + fertilizante UAN 32% en sector norte",
    "dosis_sugerida_l_ha": 2.5, "confianza_pct": 82
  }],
  "resumen": "Anomalía severa en 3.7 ha del sector noreste (8.7% del lote). Causa probable: estrés hídrico en estadio R3.",
  "comentario_tecnico": null,
  "generado_en": "2026-05-10T09:20:00Z"
}
```

**PATCH** **`/api/v1/diagnostico/{diagnostico_id}/comentario`** — RFDR-04

Se usa `PATCH` (no `PUT`) porque solo se modifica un campo. Este comentario aparece en el reporte PDF como validación profesional.

```json
// Request Body
{ "comentario_tecnico": "Confirmado estrés hídrico. Priorizar sector norte. Validado: Ing. Agr. Juan Pérez, 12/06/2026." }
```

**GET** **`.../analisis/{analisis_id}/prescripcion`**

```json
// Response 200 OK
{
  "analisis_id": "analisis-qrs",
  "zonas_prescripcion": [
    { "zona_id": "zona-001", "dosis_l_ha": 2.5, "area_ha": 3.7, "geometry": {...} },
    { "zona_id": "zona-002", "dosis_l_ha": 0.0, "area_ha": 38.8, "geometry": {...} }
  ],
  "area_total_prescrita_ha": 3.7,
  "ahorro_estimado_pct": 28.9
}
```

* * *

### 3.5 Módulo Reportes y Exportación — `app/reportes/`

Genera todos los entregables finales. No recalcula nada — consume los resultados de PostGIS y MinIO, y los transforma en los formatos que necesita el usuario o la maquinaria.
> **Requisitos:** RFSA-01, RFSA-02, RFSA-03, RFSA-04, RNF-26

#### ¿Por qué hay tantos formatos?

Cada entregable sirve a un usuario distinto con un objetivo distinto:

*   **Shapefile (.zip):** formato estándar GIS. Las consolas de tractores John Deere, Case IH, New Holland leen Shapefiles directamente para guiar la aplicación variable.
*   **ISO-XML (ISOBUS):** norma ISO 11783 para maquinaria agrícola inteligente. Permite a la pulverizadora ajustar automáticamente las boquillas por zona sin intervención del operador. Es el entregable de mayor valor comercial.
*   **PDF ejecutivo:** para el productor y el técnico. Incluye mapas, estadísticas de ahorro y diagnóstico. No es para la máquina — es para la reunión con el cliente.
*   **Orden de Trabajo:** documento formal que el operador recibe antes de salir al campo. Incluye dosis, restricciones climáticas y medidas de seguridad.
*   **Certificación:** una vez hecha la aplicación, el operador carga el log de la consola (que registra automáticamente dónde y cuánto aplicó). El sistema compara prescrito vs aplicado y emite un certificado — valioso para auditorías ambientales.

| Método | Ruta | Descripción | Auth | Códigos |
| ---| ---| ---| ---| --- |
| `GET` | `/api/v1/analisis/{analisis_id}/reportes/shapefile` | Shapefile (.zip) para consolas agrícolas | JWT | 200, 401, 403, 404 |
| `GET` | `/api/v1/analisis/{analisis_id}/reportes/iso-xml` | ISO-XML (ISOBUS) para maquinaria | JWT | 200, 401, 403, 404 |
| `GET` | `/api/v1/analisis/{analisis_id}/reportes/pdf` | Reporte ejecutivo PDF | JWT | 200, 202, 401, 404 |
| `POST` | `/api/v1/analisis/{analisis_id}/reportes/orden-trabajo` | Generar Orden de Trabajo | JWT | 201, 400, 401, 404 |
| `POST` | `/api/v1/analisis/{analisis_id}/reportes/certificacion` | Log aplicación real vs prescripción | JWT | 201, 400, 401, 404 |

**GET** **`.../reportes/shapefile`**

El backend lee las zonas de PostGIS, las convierte a Shapefile usando `gdal_polygonize` y las comprime en ZIP. La respuesta es el archivo directamente.

```dart
// Response 200 OK
Content-Type: application/zip
Content-Disposition: attachment; filename="prescripcion_analisis-qrs.zip"
// Incluye: .shp (geometrías) · .dbf (atributos) · .prj (sistema de coordenadas) · .shx (índice)
```

**GET** **`.../reportes/iso-xml`** — RNF-26

Convierte la prescripción al formato XML de la norma ISO 11783 (ISOBUS). Entendido por la mayoría de consolas de maquinaria agrícola moderna.

**GET** **`.../reportes/pdf`** — puede devolver 202

Si el PDF ya fue generado (cacheado en MinIO) devuelve `200`. Si es la primera vez, lo genera en segundo plano y devuelve `202` — el frontend vuelve a consultar en unos segundos.

**POST** **`.../reportes/orden-trabajo`**

```json
// Request Body
{ "operador": "Carlos Rodríguez", "equipo": "Pulverizadora Jacto Uniport 2500", "fecha_planificada": "2026-06-15", "notas_adicionales": "No aplicar si viento > 15 km/h." }

// Response 201 Created
{ "orden_id": "orden-pqr", "pdf_url": "https://minio.agronexo.com/ordenes/orden-pqr.pdf?token=...", "generada_en": "2026-06-12T11:00:00Z" }
```

**POST** **`.../reportes/certificacion`** — cierre del ciclo completo

```haskell
// Request: multipart/form-data
archivo_log:       [archivo .shp o .csv del log de la pulverizadora]
fecha_aplicacion:  "2026-06-15T06:30:00Z"
operador:          "Carlos Rodríguez"
```

```json
// Response 201 Created
{ "certificacion_id": "cert-stu", "diferencia_area_pct": 4.2, "diferencia_dosis_pct": 1.8, "conforme": true }
```

* * *

## 4\. Referencia de códigos HTTP

Los códigos HTTP comunican el resultado de cada operación. El primer dígito indica la categoría:

*   **2xx** = Éxito (el servidor procesó el request correctamente)
*   **4xx** = Error del cliente (el problema está en lo que mandó el frontend)
*   **5xx** = Error del servidor (algo falló internamente)

La diferencia entre 4xx y 5xx es importante para el debugging: si el error es 4xx, hay que revisar lo que manda el frontend; si es 5xx, hay que revisar el backend.

| Código | Significado en AgroNexo |
| ---| --- |
| `200 OK` | Solicitud exitosa. La respuesta contiene los datos pedidos. |
| `201 Created` | Recurso creado exitosamente. Se devuelve el recurso creado en el body. |
| `202 Accepted` | Tarea aceptada y encolada en Celery. El procesamiento ocurre en segundo plano. |
| `204 No Content` | Operación exitosa que no necesita devolver datos (logout, delete). |
| `400 Bad Request` | Datos inválidos — campo faltante, formato incorrecto, GeoTIFF sin banda NIR. |
| `401 Unauthorized` | Token JWT ausente, expirado o con firma inválida. Hacer login o refresh. |
| `403 Forbidden` | El token es válido pero el recurso no pertenece a este usuario. |
| `404 Not Found` | El recurso no existe o fue eliminado (soft delete). |
| `409 Conflict` | Ya existe un análisis en curso para ese vuelo. |
| `413 Payload Too Large` | El GeoTIFF supera el límite de 1 GB (RNF-17). |
| `422 Unprocessable Entity` | Pydantic rechazó el request: los tipos de datos no coinciden con el esquema. |
| `500 Internal Server Error` | Error interno. Se loguea con `correlation_id` para poder rastrearlo. |

**Esquema de error estándar** — todos los errores devuelven el mismo formato:

```json
{
  "detail": "El GeoTIFF no contiene la banda NIR requerida para calcular NDVI.",
  "error_code": "INVALID_GEOTIFF_MISSING_NIR_BAND",
  "correlation_id": "7f3a2b1c-9d4e-4f5a-b6c7-8d9e0f1a2b3c"
}
```

El `correlation_id` es un UUID generado por request. Con ese ID se puede encontrar exactamente qué pasó en los logs del backend cuando un usuario reporta un error.
* * *

## 5\. Notas de implementación

### 5.1 Jerarquía de rutas y módulos

Las rutas anidadas (`/lotes/{id}/vuelos/{id}/analisis/{id}/...`) reflejan la jerarquía real del dominio y sirven como capa extra de seguridad: el backend verifica que el usuario tiene acceso al lote padre antes de acceder al análisis hijo.

Para el módulo de reportes, la ruta usa el atajo `/api/v1/analisis/{id}/reportes` sin repetir la jerarquía completa, porque el `analisis_id` es globalmente único (UUID) y el backend puede resolver el lote y el vuelo a partir de él.

### 5.2 Procesamiento asíncrono (Celery + Redis)

*   `POST /analisis` devuelve **202 Accepted** con `task_id`. El backend nunca espera al Worker GIS.
*   El Worker GIS actualiza el progreso en Redis en tiempo real. El endpoint `/estado` lee Redis y lo devuelve al frontend.
*   El frontend hace **polling cada 10 segundos** (RNF-04). Es una elección deliberada para el MVP: polling es stateless y no requiere mantener conexiones WebSocket abiertas.
*   Reintentos automáticos con backoff exponencial (RNF-15): 30s → 2min → 10min. Tras 3 fallos: estado "fallido".
*   Estados posibles: `encolado → procesando → completado | fallido`

**Polling (Sondeo):** Es el acto de preguntar periódicamente
**State stateless (Sin estado):** El servidor no necesita recordar quién está conectado.
### 5.3 Upload de GeoTIFF (módulo Ingesta)

*   FastAPI maneja el archivo con `UploadFile` en streaming — no lo carga completo en memoria para soportar hasta 1 GB sin problema.
*   El límite de 1 GB (RNF-17) se valida con middleware **antes** de que el archivo llegue al endpoint — si supera el límite, se corta la conexión con `413` inmediatamente.
*   Validaciones sobre el GeoTIFF: presencia de bandas NIR y RED, CRS (Sistema de Referencia de Coordenadas) definido, archivo no corrupto (Rasterio puede abrirlo sin error).

### 5.4 Esquema de error estándar

FastAPI y Pydantic generan automáticamente la validación a partir de los modelos Python. Si el frontend manda un JSON con tipos incorrectos (ej: `altitud_m: "ochenta"` en lugar de `80`), Pydantic devuelve `422` con el detalle exacto de qué campo falló, sin necesidad de código de validación manual.

# Arquitectura de Módulos y Responsabilidades

# Arquitectura de Módulos y Responsabilidades — AgroNexo
## 1\. Introducción
Este documento define los módulos del sistema AgroNexo, sus responsabilidades, las relaciones entre ellos y su mapeo con los requisitos funcionales de la ERS. Complementa el documento de Stack Tecnológico (que describe _qué tecnologías_ se usan y por qué) con la definición de _qué hace cada parte del sistema_.

La arquitectura sigue el patrón de **monolito modular con worker desacoplado**: todos los módulos del backend comparten el mismo proceso y la misma base de datos, pero están organizados internamente con responsabilidades aisladas. El Worker GIS es el único componente que se ejecuta como proceso separado, conectado mediante una cola de tareas.

* * *
## 2\. Capas del sistema
El sistema se organiza en cuatro capas, cada una con un rol definido:

| Capa | Responsabilidad | Comunicación |
| ---| ---| --- |
| Frontend | Interfaz de usuario, visualización de mapas y resultados | REST API + GeoJSON hacia el Backend |
| Backend (Aplicación) | Lógica de negocio, autenticación, coordinación de procesamiento | HTTP desde Frontend, Celery hacia Worker, SQL hacia Datos |
| Procesamiento (Worker GIS) | Cálculo de índices, vectorización, análisis espacial | Recibe tareas de Celery, lee/escribe en la Capa de Datos |
| Datos | Persistencia de metadatos, geometrías y archivos binarios | Accedida por Backend y Worker |

* * *
## 3\. Módulos del sistema
### 3.1 Módulo de Autenticación y Seguridad
**Capa:** Backend (FastAPI)

**Responsabilidad:** Gestionar el acceso al sistema, garantizar el aislamiento de datos entre usuarios y proteger las comunicaciones.

**Qué hace:**
*   Registro y login de usuarios con JWT
*   Validación de tokens en cada request protegida
*   Expiración automática de sesiones inactivas (30 minutos)
*   Aislamiento de datos por usuario (multi-tenencia)
*   Validación y sanitización de entradas contra inyecciones y XSS

**Qué NO hace:**
*   No gestiona roles diferenciados (productor vs prestador) en el MVP — todos los usuarios autenticados tienen las mismas capacidades
*   No implementa OAuth ni SSO

**Requisitos que cubre:**

| ID | Requisito |
| ---| --- |
| RNF-05 | Autenticación de usuarios |
| RNF-06 | Control de acceso por usuario |
| RNF-07 | Cifrado de comunicaciones (HTTPS) |
| RNF-08 | Validación de entradas |
| RNF-09 | Gestión de sesiones |
| RFGL-01 | Multi-tenencia de datos |

* * *
### 3.2 Módulo de Gestión de Lotes
**Capa:** Backend (FastAPI)

**Responsabilidad:** Administrar la información de los lotes agrícolas del usuario, incluyendo sus límites geográficos, historial de vuelos y contexto agronómico.

**Qué hace:**
*   CRUD de lotes con límites geográficos (polígonos almacenados en PostGIS)
*   Registro de vuelos asociados a cada lote (fecha, condiciones, sensor utilizado)
*   Registro de contexto agrológico: tipo de cultivo, estadio fenológico, condiciones climáticas
*   Mantenimiento de línea de tiempo de intervenciones (vuelos, análisis, aplicaciones)
*   Gestión de hasta 50 lotes por usuario sin degradación

**Qué NO hace:**
*   No procesa archivos GeoTIFF — los recibe, los almacena en MinIO y delega el procesamiento al Worker
*   No realiza cálculos espaciales complejos — usa PostGIS para almacenamiento y consultas básicas

**Requisitos que cubre:**

| ID | Requisito |
| ---| --- |
| RFME-03 | Registro de contexto agrológico |
| RFGL-02 | Inventario de lotes con límites geográficos |
| RFGL-03 | Historial de intervenciones |
| RFGL-04 | Gestión de capas (superposición de análisis por fecha) |
| RNF-19 | Procesamiento de múltiples lotes (hasta 50) |

* * *
### 3.3 Módulo de Ingesta y Validación
**Capa:** Backend (FastAPI)

**Responsabilidad:** Recibir los archivos GeoTIFF del usuario, validar su integridad y metadatos, almacenarlos en MinIO y encolar el procesamiento.

**Qué hace:**
*   Recepción de archivos GeoTIFF mediante upload HTTP
*   Validación de metadatos: presencia de bandas espectrales válidas (RGB/NIR), CRS definido, integridad del archivo
*   Almacenamiento del archivo original en MinIO con estructura `usuario/lote/vuelo/`
*   Generación de vista previa low-res para confirmación visual antes de procesar
*   Encolamiento de la tarea de procesamiento en Redis/Celery
*   Soporte para archivos de hasta 1 GB

**Qué NO hace:**
*   No procesa el archivo — solo lo valida y lo almacena
*   No calcula índices ni genera polígonos

**Requisitos que cubre:**

| ID | Requisito |
| ---| --- |
| RFME-01 | Carga de archivos ráster (GeoTIFF) |
| RFME-02 | Validación de metadatos (bandas, CRS) |
| RFME-04 | Visualización de integridad (vista previa low-res) |
| RFMP-05 | Persistencia de datos (archivos fuente) |
| RNF-17 | Soporte de archivos de hasta 1 GB |

* * *
### 3.4 Módulo de Procesamiento Geoespacial (Worker GIS)
**Capa:** Procesamiento (Worker Celery)

**Responsabilidad:** Ejecutar todo el pipeline de análisis geoespacial: lectura de rasters, cálculo de índices de vegetación, clasificación, vectorización y exportación de resultados.

Este es el núcleo técnico del sistema. Se ejecuta como proceso Celery independiente del backend.

**Qué hace:**
*   Lectura del GeoTIFF desde MinIO con Rasterio (windowed reading para archivos grandes)
*   Reproyección cartográfica al sistema de coordenadas local (UTM) si es necesario
*   Cálculo de índices de vegetación: NDVI, NDRE, SAVI, ExG según bandas disponibles
*   Umbralización dinámica para clasificar píxeles en categorías de vigor/anomalía
*   Soporte para calibración manual y automática de umbrales (método de Otsu)
*   Detección de anomalías: áreas con valores atípicos que sugieran estrés o plagas
*   Vectorización: conversión de píxeles clasificados en polígonos georeferenciados (gdal\_polygonize)
*   Simplificación de polígonos con Douglas-Peucker para reducir vértices
*   Filtrado de ruido: eliminación de polígonos menores a un área mínima configurable
*   Zonificación: agrupación de áreas contiguas con necesidades similares
*   Cálculo de estadísticas por zona: área en hectáreas, índice promedio, severidad
*   Cálculo de ahorro de insumos (área total vs área prescrita)
*   Almacenamiento de resultados: polígonos en PostGIS, archivos generados en MinIO
*   Reporte de progreso en Redis para que el frontend muestre avance en tiempo real

**Qué NO hace:**
*   No atiende requests HTTP — solo ejecuta tareas encoladas por Celery
*   No genera diagnósticos en lenguaje natural — solo produce datos estructurados
*   No genera PDFs ni reportes finales — produce los datos que otros módulos consumen

**Requisitos que cubre:**

| ID | Requisito |
| ---| --- |
| RFMA-01 | Procesamiento de índices de vegetación |
| RFMA-02 | Umbralización dinámica |
| RFMA-03 | Calibración de umbrales (manual y Otsu) |
| RFMA-04 | Detección de anomalías |
| RFMP-01 | Reproyección cartográfica |
| RFMP-02 | Extracción de geometrías (vectorización) |
| RFMP-03 | Generalización / simplificación de polígonos |
| RFMP-04 | Filtrado de ruido (área mínima) |
| RFMP-05 | Persistencia de resultados |
| RFDR-02 | Zonificación de manejo |
| RFDR-03 | Estimación de severidad |
| RFGL-05 | Análisis de eficiencia (ahorro de insumos) |
| RNF-02 | Procesamiento en menos de 5 minutos (hasta 500 MB) |
| RNF-04 | Retroalimentación de progreso cada 10 segundos |
| RNF-15 | Recuperación ante fallos (reintentos Celery) |

* * *
### 3.5 Módulo de Diagnóstico
**Capa:** Backend (FastAPI)

**Responsabilidad:** Interpretar los resultados del procesamiento geoespacial y generar un diagnóstico comprensible que asocie los datos técnicos con acciones agronómicas concretas.

**Qué hace:**
*   Motor de reglas que cruza: índice calculado + tipo de cultivo + estadio fenológico + contexto del lote
*   Asociación de niveles de índice con acciones recomendadas (dosis variable por zona)
*   Vinculación de cada diagnóstico con el vuelo y lote correspondiente (trazabilidad)
*   Permite al profesional adjuntar justificación o comentario técnico al diagnóstico

**Qué NO hace (por ahora):**
*   No genera texto en lenguaje natural — produce diagnósticos estructurados basados en reglas
*   La integración con LLM para generación de texto está prevista como mejora futura, no como parte del MVP

**Requisitos que cubre:**

| ID | Requisito |
| ---| --- |
| RFDR-01 | Motor de reglas (índice → acción recomendada) |
| RFDR-04 | Registro de criterio técnico |
| RFDR-05 | Trazabilidad de vuelo |

* * *
### 3.6 Módulo de Reportes y Exportación
**Capa:** Backend (FastAPI)

**Responsabilidad:** Generar todos los entregables del sistema: reportes PDF, archivos de prescripción para maquinaria y órdenes de trabajo.

**Qué hace:**
*   Generación de Reporte Ejecutivo en PDF: mapas, estadísticas de ahorro, diagnóstico
*   Exportación de prescripciones en formatos compatibles con maquinaria (Shapefile, GeoJSON)
*   Generación de Orden de Trabajo con dosis, restricciones ambientales e instrucciones de seguridad
*   Carga y contraste de log de aplicación real vs prescripción original

**Qué NO hace:**
*   No calcula los datos — los consume de PostGIS y MinIO, generados por el Worker y el módulo de Diagnóstico
*   No envía los reportes por email — los deja disponibles para descarga

**Requisitos que cubre:**

| ID | Requisito |
| ---| --- |
| RFSA-01 | Exportación de prescripción (Shapefile, ISO-XML) |
| RFSA-02 | Generación de Orden de Trabajo |
| RFSA-03 | Reporte Ejecutivo (PDF) |
| RFSA-04 | Certificación de aplicación (log real vs prescripción) |
| RNF-26 | Formatos de exportación estándar |

* * *
### 3.7 Frontend
**Capa:** Frontend (React)

**Responsabilidad:** Proveer la interfaz de usuario para todas las operaciones del sistema, incluyendo la visualización de mapas interactivos con los resultados del análisis.

**Qué hace:**
*   Dashboards con resumen de lotes, análisis recientes y estado de procesamiento
*   Mapas interactivos con Leaflet: polígonos GeoJSON con estilos por clase, capas superpuestas por fecha
*   Subida de archivos GeoTIFF con barra de progreso
*   Polling de estado de procesamiento con indicadores visuales
*   Visualización de diagnósticos y estadísticas por zona
*   Descarga de reportes PDF y archivos de prescripción
*   Interfaz responsiva para desktop y tablet

**Qué NO hace:**
*   No procesa datos geoespaciales en el browser
*   No almacena estado persistente — toda la información viene de la API

**Requisitos que cubre:**

| ID | Requisito |
| ---| --- |
| RNF-01 | Tiempo de carga menor a 3 segundos |
| RNF-04 | Retroalimentación visual del progreso |
| RNF-10 | Curva de aprendizaje baja |
| RNF-11 | Mensajes de error comprensibles |
| RNF-12 | Consistencia de la interfaz |
| RNF-13 | Accesibilidad básica |
| RNF-20 | Compatibilidad con Chrome, Firefox, Edge |
| RNF-21 | Diseño responsivo |

* * *
## 4\. Relaciones entre módulos
### 4.1 Flujo principal: upload → análisis → resultado

```plain
Usuario sube GeoTIFF
 ↓
[Ingesta y Validación]
 - valida metadatos
 - guarda en MinIO
 - encola tarea
 ↓
[Worker GIS]
 - lee de MinIO
 - calcula índices
 - vectoriza
 - guarda polígonos en PostGIS
 - guarda archivos en MinIO
 ↓
[Diagnóstico]
 - lee polígonos y estadísticas de PostGIS
 - aplica reglas según cultivo y estadio
 - genera diagnóstico estructurado
 ↓
[Reportes y Exportación]
 - genera PDF con mapas y diagnóstico
 - exporta Shapefile para maquinaria
 - genera Orden de Trabajo
 ↓
[Frontend]
 - muestra mapas con polígonos
 - muestra diagnóstico
 - permite descarga de archivos
```

### 4.2 Matriz de dependencias entre módulos

| Módulo | Depende de | Es consumido por |
| ---| ---| --- |
| Autenticación | — | Todos los módulos (middleware) |
| Gestión de Lotes | Autenticación | Ingesta, Diagnóstico, Reportes, Frontend |
| Ingesta y Validación | Autenticación, Gestión de Lotes | Worker GIS |
| Worker GIS | Ingesta (indirectamente, vía cola) | Diagnóstico, Reportes |
| Diagnóstico | Worker GIS (resultados), Gestión de Lotes (contexto) | Reportes, Frontend |
| Reportes y Exportación | Diagnóstico, Worker GIS (datos) | Frontend |
| Frontend | Todos los módulos del Backend (vía API REST) | — |

* * *
## 5\. Estructura de carpetas propuesta

```plain
agronexo/
├── app/
│   ├── main.py                  # Punto de entrada FastAPI
│   ├── config.py                # Configuración con Pydantic BaseSettings
│   ├── dependencies.py          # Dependencias compartidas (DB, auth)
│   │
│   ├── auth/                    # Módulo de Autenticación
│   │   ├── router.py            # Endpoints: login, register, refresh
│   │   ├── schemas.py           # Pydantic models
│   │   ├── service.py           # Lógica de negocio
│   │   └── security.py          # JWT, hashing
│   │
│   ├── lotes/                   # Módulo de Gestión de Lotes
│   │   ├── router.py            # Endpoints: CRUD lotes, vuelos
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── models.py            # Modelos SQLAlchemy + PostGIS
│   │
│   ├── ingesta/                 # Módulo de Ingesta y Validación
│   │   ├── router.py            # Endpoints: upload, estado, preview
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── validators.py        # Validación de GeoTIFF
│   │
│   ├── diagnostico/             # Módulo de Diagnóstico
│   │   ├── router.py            # Endpoints: consultar diagnóstico
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── reglas.py            # Motor de reglas agronómicas
│   │
│   ├── reportes/                # Módulo de Reportes y Exportación
│   │   ├── router.py            # Endpoints: generar PDF, exportar shp
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── templates/           # Templates HTML para WeasyPrint
│   │
│   └── models/                  # Modelos compartidos
│       ├── base.py              # Base declarativa SQLAlchemy
│       └── database.py          # Conexión a PostgreSQL
│
├── worker/                      # Worker GIS (proceso Celery separado)
│   ├── celery_app.py            # Configuración Celery
│   ├── tasks.py                 # Definición de tareas
│   ├── pipeline/
│   │   ├── lectura.py           # Lectura de GeoTIFF con Rasterio
│   │   ├── indices.py           # Cálculo de NDVI, NDRE, SAVI, ExG
│   │   ├── clasificacion.py     # Umbralización y detección de anomalías
│   │   ├── vectorizacion.py     # Raster → polígonos con GDAL
│   │   ├── simplificacion.py    # Douglas-Peucker, filtrado de ruido
│   │   └── exportacion.py       # Guardado en PostGIS y MinIO
│   └── utils/
│       ├── progreso.py          # Reporte de progreso a Redis
│       └── crs.py               # Utilidades de reproyección
│
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.worker
└── requirements.txt
```

* * *
## 6\. Mapeo completo: Requisitos → Módulos

| Grupo ERS | IDs | Módulo responsable |
| ---| ---| --- |
| Entrada y validación | RFME-01 a RFME-04 | Ingesta y Validación |
| Análisis y procesamiento | RFMA-01 a RFMA-04 | Worker GIS |
| Procesamiento geoespacial | RFMP-01 a RFMP-05 | Worker GIS + Ingesta (persistencia) |
| Diagnóstico y prescripción | RFDR-01 a RFDR-05 | Diagnóstico + Worker GIS (zonificación, severidad) |
| Gestión del lote | RFGL-01 a RFGL-05 | Gestión de Lotes + Autenticación (multi-tenencia) + Worker GIS (eficiencia) |
| Salida | RFSA-01 a RFSA-04 | Reportes y Exportación |
| Rendimiento | RNF-01 a RNF-04 | Frontend (carga) + Worker GIS (procesamiento) |
| Seguridad | RNF-05 a RNF-09 | Autenticación |
| Usabilidad | RNF-10 a RNF-13 | Frontend |
| Disponibilidad | RNF-14 a RNF-16 | Infraestructura (Docker) + Worker GIS (reintentos Celery) |
| Escalabilidad | RNF-17 a RNF-19 | Ingesta (archivos grandes) + Worker GIS (concurrencia) + Gestión de Lotes |
| Portabilidad | RNF-20 a RNF-22 | Frontend |
| Mantenibilidad | RNF-23 a RNF-25 | Todos (arquitectura modular, documentación, logs) |
| Interoperabilidad | RNF-26 a RNF-28 | Reportes (formatos) + Worker GIS (CRS, sensores) |

# Validación bibliográfica INTA

# Referencias
[https://drive.google.com/file/d/15UKX4NxhpxE6cya7D\_TlrNvZYNrm2GBb/view?usp=sharing](https://drive.google.com/file/d/15UKX4NxhpxE6cya7D_TlrNvZYNrm2GBb/view?usp=sharing)[https://drive.google.com/file/d/1Hc4UuLnfjc3wD86zQNZK776AzYwbNGdG/view?usp=sharing](https://drive.google.com/file/d/1Hc4UuLnfjc3wD86zQNZK776AzYwbNGdG/view?usp=sharing)

# **Características de imágenes compuestas de valor máximo a partir de datos temporales de AVHRR**

> _Los datos del AVHRR (Radiómetro Avanzado de Muy Alta Resolución) son mediciones satelitales multiespectrales utilizadas para analizar la temperatura de la superficie terrestre y marina, la nubosidad, la cobertura de nieve, y el índice de vegetación. Cuentan con un registro histórico continuo desde 1979_

Este artículo evalúa los aspectos técnicos de una metodología de procesamiento que utiliza datos satelitales en banda visible y cercana al infrarrojo del Advanced Very High Resolution Radiometer (AVHRR) para estudiar procesos dinámicos de la vegetación terrestre mientras minimiza varios problemas asociados con los satélites de observación de la Tierra de onda corta.

**Metodología de Composición (MVC)**

El cálculo del NDVI de una sola fecha suele estar "contaminado" por diversos factores. La técnica de Composición de Valor Máximo (MVC) que describe el estudio es esencial para obtener un NDVI preciso porque:
*   Selecciona las mejores condiciones: Al examinar píxel por píxel durante varios días y retener solo el valor más alto, se asegura de elegir el momento con la atmósfera más clara y la mejor iluminación.
*   Reduce efectos atmosféricos: Los aerosoles y el vapor de agua tienden a reducir los valores de NDVI. Al buscar el valor máximo, el proceso selecciona automáticamente los datos con menor atenuación atmosférica.
*   Minimiza errores geométricos: El NDVI varía según el ángulo de visión. Las fuentes indican que los valores máximos suelen ocurrir cerca del nadir (vertical del satélite), lo que reduce las distorsiones causadas por la visión oblicua y las sombras

La técnica se basa en el Índice de Vegetación de Diferencia Normalizada (NDVI), que se calcula como (_NIR_−_VIS_)/(_NIR_+_VIS_). Este índice mide la capacidad fotosintética de la cubierta terrestre. El proceso MVC funciona de la siguiente manera:
*   Se procesan series de datos satelitales multitemporales y georreferenciados para obtener imágenes de NDVI.
*   Píxel por píxel, se examinan los valores de NDVI de todas las fechas y se retiene únicamente el valor más alto para la imagen final.
*   Esta técnica aprovecha que el NDVI de la vegetación verde es consistentemente más alto que el de otros componentes como el suelo desnudo, las nubes, la nieve o el agua

**Beneficios de la Técnica**

El procedimiento MVC ofrece mejoras significativas al seleccionar los datos bajo las mejores condiciones posibles:
*   Reducción de Nubes: Al procesar múltiples días, aumenta la probabilidad de obtener una observación libre de nubes para cada píxel.
*   Efectos Atmosféricos: Minimiza la influencia de aerosoles y vapor de agua, ya que estos suelen reducir el valor del NDVI. Al elegir el valor máximo, se seleccionan las condiciones atmosféricas más claras.
*   Geometría de Visión: Tiende a seleccionar píxeles observados cerca del nadir (vertical del satélite), lo que reduce el camino óptico a través de la atmósfera y minimiza los efectos de reflectancia direccional de la superficie.
*   Ángulo Solar: Ayuda a reducir los efectos de sombras y ángulos solares bajos que disminuyen los valores de NDVI

**Limitaciones y Desafíos**

A pesar de sus ventajas, el estudio identifica varios problemas asociados:
*   Contaminación por Nubes Residuales: Las nubes delgadas o cirros pueden no ser eliminadas completamente solo con el MVC, por lo que se recomienda el uso de máscaras térmicas (usando el canal 4 o 5 del AVHRR) para descartar píxeles fríos que representen nubes.
*   Anomalías en el Desierto: En ciertas áreas del Sahara, la estratificación del NDVI falla debido a la mineralogía del suelo y la baja humedad, lo que genera valores de NDVI inusualmente altos en zonas sin vegetación.
*   Efecto del Terminador: Cerca de la línea del crepúsculo (latitudes altas en invierno), se generan valores de NDVI falsamente elevados debido a la dispersión atmosférica y los largos caminos ópticos cuando el sol está muy bajo (ángulos cenitales mayores a 80°).
*   Registro Espacial: La precisión de la imagen compuesta depende de un alineamiento perfecto entre las fechas. Un error en el registro (desplazamiento de píxeles) puede difuminar los límites de la vegetación o asignar valores altos a áreas adyacentes incorrectas

# Teledetección

**Capítulo 4: Comportamiento espectral de las cubiertas terrestres**

# El Latido Verde de la Tierra

## 📘 Índice de Capítulos: El Latido Verde de la Tierra
### Capítulo 1: El Viejo Mensajero de la Estación
*   De qué se trata: Presentamos el punto de partida histórico. Conocemos a Don G. West (WSGI), un viejo jefe de correos ferroviario, metódico y confiable, pero que solo puede procesar una carta a la vez. El pueblo está creciendo, los campos exigen respuestas rápidas y las cartas se empiezan a acumular en su escritorio, colapsando el sistema de comunicación tradicional de la región.
### Capítulo 2: El Relevo de la Medianoche
*   De qué se trata: Ante el colapso de las comunicaciones, llega un joven dinámico al pueblo: Ashton "Ace" Gordon (ASGI). Ace implementa un sistema revolucionario de mensajería simultánea. No espera a que una respuesta vuelva para enviar el siguiente mensaje; coordina hilos de información en tiempo real, permitiendo que el pueblo empiece a hablar simultáneamente con los satélites en el cielo y las máquinas en la tierra sin perder un solo milisegundo.
### Capítulo 3: La Vigía del Firmamento
*   De qué se trata: Entra en escena Selene Sentinel (Satélites de Teledetección / Sentinel-2). Ella vive en la órbita alta y sobrevuela la región cada 5 días, observando el mundo en frecuencias invisibles para los humanos (Infrarrojo Cercano y Rojo). Selene toma fotografías gigantescas llenas de secretos sobre el suelo y el agua, y las envía a la estación de Ace a la velocidad de la luz.
### Capítulo 4: Los Traductores del Espectro
*   De qué se trata: Los datos de Selene son indescifrables a simple vista. Aquí se presentan los Hermanos Espectrales (Los Índices de Vegetación), un grupo de analistas biológicos:
    *   Savi, el menor, que limpia el ruido del suelo marrón cuando las plántulas de soja apenas asoman (V1-V3).
    *   Ned (NDVI), el líder carismático, que mide la fuerza de la biomasa verde en pleno crecimiento.
    *   Glenn (GNDVI), el especialista óptico, que aparece cuando Ned se satura para mirar la clorofila profunda en el llenado de granos.
    *   Milo (NDMI), el hidrólogo, obsesionado con detectar el estrés hídrico y la falta de agua en las hojas.
### Capítulo 5: La Arquitecta del Caos y el Inspector del Puerto
*   De qué se trata: Para procesar todo este flujo biológico y satelital en la tierra, conocemos a los dos ingenieros principales que Ace contrató en la estación base:
    *   Stella (Starlette): Una ingeniera de logística ultrarrápida, experta en construir autopistas digitales y desviar el tráfico de datos hacia donde corresponde.
    *   Dan (Pydantic): El inspector de aduanas e higienista de datos. Dan intercepta cada reporte de campo; si un dato viene corrupto, mal tipeado o con formatos extraños, lo rebota en la frontera para proteger la integridad de la base de datos.
### Capítulo 6: El Director de la Orquesta Verde
*   De qué se trata: Aparece el protagonista central, Fabian "Fast" API (FastAPI). Fabian no construye las carreteras ni inspecciona los paquetes personalmente (para eso tiene a Stella y Dan), pero unifica a todo el equipo. Crea un centro de control unificado, escribe los manuales de estrategia interactivos de forma automática (Swagger Docs) y permite que los traductores espectrales y los mensajeros asincrónicos trabajen como un solo ser vivo hiperveloz.
### Capítulo 7: El Cartógrafo Digital y las Reglas de Inyección
*   De qué se trata: La información procesada por Fabian debe convertirse en mapas de acción. Entra en escena Gideon (Sistemas GIS), un cartógrafo analítico que dibuja líneas de prescripción variable sobre los lotes de soja. En este capítulo, Fabian inyecta sus reglas lógicas temporales (la máquina de estados fenológicos) en los mapas de Gideon, definiendo alertas automáticas si el NDVI cae o si aparecen malezas inesperadas en la senescencia.
### Capítulo 8: El Brazo de Hierro y la Frontera Invisible
*   De qué se trata: El clímax de la historia. Conocemos al gigante mecánico, Val (VRA - Maquinaria de Aplicación Variable), una pulverizadora inteligente conectada a los mapas de Gideon. Mientras Val avanza por el lote aplicando dosis milimétricas de fitosanitarios basándose en el pulso de los índices, el sistema automatizado de Fabian apaga los motores instantáneamente al rozar las zonas de amortiguamiento y exclusión legal, salvando el ecosistema circundante y demostrando el triunfo de la agricultura de precisión.