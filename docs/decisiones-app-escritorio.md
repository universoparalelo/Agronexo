# Decisiones: AgroNexo como app de escritorio (camino B)

Registro de las decisiones y preguntas que se van discutiendo, en orden. Contexto técnico: `opciones-app-escritorio.md` (fuera del repo) y `spike-escritorio/INFORME.md`.

**Principio (D8):** la app funciona con y sin internet; las funciones que necesitan conexión se habilitan cuando la hay.

## Decididas

| # | Fecha | Decisión | Consecuencia |
|---|---|---|---|
| D1 | 2026-10-29 | **El instalador de escritorio reemplaza el despliegue en servidor.** | La HU-R4-06 (servidor, HTTPS, firewall) deja de aplicar y pasa a ser "distribución del instalador". Falta reflejarlo en `docs/release-v4.0.0.md`. Docker sigue para desarrollo y CI. |
| D2 | 2026-10-29 | **Almacenamiento en disco, sin MinIO, en el instalador de escritorio.** | Se reemplaza el backend de `app/core/storage.py` por una carpeta en `%APPDATA%\AgroNexo\`. Las URLs firmadas pasan a ser un endpoint de la API con token que vence. Ya no hace falta resolver la licencia ni el binario de `minio.exe`. |
| D3 | 2026-10-29 | **MinIO se elimina por completo del proyecto**, también de Docker y CI (ajusta D2, que dejaba MinIO en Docker/CI). Se hace **en dos pasos**: primero el backend de disco con MinIO todavía disponible; cuando todo esté verde en CI, se quita MinIO. | Se van el servicio de MinIO del `docker-compose.yml`, la dependencia `minio`, sus variables de entorno y el problema de las imágenes oficiales. Docker necesita un volumen compartido entre API y worker. Los tests que dependen de MinIO (`test_celery_integracion.py`, `test_exportacion_api.py`) pasan a usar una carpeta temporal. También cambian `docker-compose.prod.yml`, el CI, `README.md` y `.env.example`. Se pierde la compatibilidad con S3. Aún no se implementó nada. |
| D4 | 2026-10-29 | **Sesión automática, sin pantalla de login** (opción A de Q3). | Se mantiene un usuario local en la base, que se crea con la migración `0006` leyendo `ADMIN_EMAIL` y `ADMIN_PASSWORD` del entorno. El lanzador genera una contraseña aleatoria por instalación, la guarda en AppData e inicia sesión solo; el usuario nunca ve un login. Se conserva la verificación del token. Hay que definir cómo el frontend recibe la sesión (ver Q3). Aún no se implementó nada. |
| D5 | 2026-10-29 | **Backup con "Exportar todo" e "Importar"** (opción 1 de Q4): un solo `.zip` con el volcado de la base y los archivos. | Al desinstalar: ver D7. La copia automática antes de actualizar se decidió en D11. Aún no se implementó nada. |
| D6 | 2026-10-29 | **Mapas: fondo neutro cuando no hay internet** (opción 3 de Q5, ajustada por D8): solo los polígonos de lotes y zonas sobre un color liso; con internet se sigue mostrando el mapa base como hoy. | Se aplica a los 7 componentes que hoy bajan mapa base de internet. Con internet siguen aplicando los términos de uso de OpenStreetMap y Esri para el uso desde una app de escritorio (a verificar). Sumar caché de tiles para uso sin conexión queda como mejora posible. Aún no se implementó nada. |
| D7 | 2026-10-29 | **Al desinstalar, el desinstalador pregunta si se quieren borrar los datos** (opción 2 de Q6). La casilla "borrar también mis datos" viene **desmarcada por defecto**. | Por defecto se conservan la base y los archivos, así que reinstalar recupera todo. Hay que implementarlo en el desinstalador (NSIS u otro). Aún no se implementó nada. |
| D8 | 2026-10-29 | **La app funciona con y sin internet.** Cuando hay conexión, las funciones que la necesitan se habilitan; cuando no, quedan deshabilitadas con un aviso (D9) y el resto funciona igual. No se asume que el usuario nunca tendrá internet, ni que la tendrá en el primer arranque. | Funciones que dependen de internet: mapas base (sin conexión, fondo neutro, D6), búsqueda de direcciones (Nominatim), imágenes satelitales (`desde-satelite`) y, en el futuro, las actualizaciones de la app. Todo lo demás (análisis de GeoTIFF propios, diagnóstico, reportes, backup) funciona sin conexión. Hay que definir cómo detecta la app que hay conexión y cómo se comporta la interfaz sin conexión (D9). Aún no se implementó nada. |
| D9 | 2026-10-29 | **Sin internet, las funciones que lo necesitan quedan deshabilitadas y, al pasar el mouse por encima, muestran un aviso de que no hay conexión** (opción 1 de Q8; primero se había elegido ocultarlas y se cambió el mismo día). Además, un indicador general visible ("Sin conexión" o "Modo sin conexión") que se muestra mientras no haya internet (decidido el mismo día); el texto exacto y el lugar en pantalla se definen al implementar. | Se aplica a la búsqueda de direcciones y a las imágenes satelitales (`desde-satelite`); el mapa base cae solo al fondo neutro (D6). Así el usuario sabe que la función existe y por qué no está disponible. Al volver la conexión se habilitan solas. En pantallas táctiles no hay "pasar el mouse": conviene que el aviso también se pueda ver de otra forma (por ejemplo al tocar la opción). Falta definir cómo detecta el frontend que hay conexión (`navigator.onLine` por sí solo no es confiable). Aún no se implementó nada. |
| D10 | 2026-10-29 | **Pantalla de bienvenida en el primer arranque que pide nombre y correo** (Q7). | Aparece una sola vez. **No es un login:** no pide contraseña y la sesión sigue siendo automática (D4). El correo no se verifica y la pantalla no depende de internet (D8). Ese usuario es la identidad bajo la que se guardan los datos y la que aparece en reportes y órdenes de trabajo. Pendiente de diseño: la migración `0006` siembra el usuario antes de que nadie escriba el correo (pedirlo antes de migrar y pasarlo como `ADMIN_EMAIL`, o sembrar uno provisorio y actualizarlo con `/auth/me`); y qué pasa con la bienvenida cuando se importa un backup (D5), cuyo usuario ya existe. Aún no se implementó nada. |
| D11 | 2026-10-29 | **Copia automática de la base antes de cada actualización de la app** (Q9), como red de seguridad ante migraciones que salgan mal. | Se guardan solo las últimas 2 o 3 copias para no llenar el disco (propuesta de Claude; cantidad exacta sin definir). Se hace antes de correr `alembic upgrade head`. Pendiente: dónde se guarda la copia (¿dentro de la carpeta de datos?), cómo se restaura y si cubre también los archivos o solo la base. Aún no se implementó nada. |
| D12 | 2026-10-29 | **Alcance de la primera versión del instalador** (Q10): crear un lote y subir un GeoTIFF propio; calcular índices y ver el mapa de zonas; ver el diagnóstico y generar el reporte PDF; backup con Exportar e Importar. | **Quedan para después:** imágenes satelitales (`desde-satelite`), actualizaciones automáticas de la app y caché de mapas. Incluye lo ya decidido: pantalla de bienvenida (D10), almacenamiento en disco (D2/D3), modo sin conexión (D8/D9) y copia antes de actualizar (D11), que son parte de que la app funcione. Fechas, sprint y responsables siguen sin definir. |

### Detalle de D2
- **Para qué sirve el almacenamiento:** guarda el GeoTIFF original, los índices, las zonas GeoJSON, los PDF y el avatar/logo.
- **Por qué disco:** MinIO obligaba a resolver su licencia (hasta donde sé, AGPL; sin verificar) y a conseguir un `minio.exe` redistribuible estable (el `docker-compose.yml` registra que dejó de publicar imágenes oficiales), además de un proceso más para el lanzador.
- **Alcance del cambio:** `app/core/storage.py` es el único módulo que importa `minio` (~10 funciones: `upload_geotiff`, `upload_geotiff_stream`, `upload_bytes`, `upload_file`, `download_geotiff`, `download_geotiff_to_file`, `download_bytes`, `object_exists`, `presigned_url`).
- **Cuidados:** impedir que una clave salga de la carpeta de datos (rutas con `..`); revisar quién usa `presigned_url` (avatar, logo, reportes); tests del backend de disco y del endpoint de descarga; los tests que hoy dependen de MinIO siguen en CI.
- **Esfuerzo estimado (sin verificar):** 1 a 2 días con tests, en una rama `feat/almacenamiento-en-disco` con su PR.
- **No verificado:** la auditoría anota que una de las subidas carga el archivo completo en RAM; no se revisó cuál usa cada endpoint.

## En discusión

### Q2. Lanzador: ¿Electron o Tauri?
- **Electron (recomendado por Claude):** JavaScript (el equipo ya lo sabe), Chromium propio con versión fija, `printToPDF` como salida si GTK resulta caro, madurez muy alta. En contra: instalador ~140 MB más pesado (poco frente a ~1 GB de Postgres, GDAL y PDF) y hay que actualizar Electron periódicamente por seguridad.
- **Tauri:** ~5–10 MB, usa el WebView2 del sistema (varía por máquina), el lanzador se escribe en Rust. En contra: toolchain de Rust y build tools de Visual Studio, menor madurez, no resuelve el PDF (habría que empaquetar GTK) y un mapa de Leaflet probablemente se vea igual pero no es garantizable.
- **Estado:** sin decidir (2026-10-29). Según el documento de opciones, la elección puede tomarse tarde porque el trabajo difícil es idéntico con ambos.

### Q3. Login en una app de un solo usuario
- **Idea planteada:** sacar el login (2026-10-29), todavía sin decidir cómo.
- **Opción A, sesión automática (recomendada por Claude):** se mantiene un usuario local en la base (el admin que ya se siembra) y la app entra sola con su token, sin pantalla de login. El backend casi no cambia: lotes, avatar, logo, perfil y preferencias siguen colgando del usuario. Se mantiene la verificación del token, porque la API escucha en `127.0.0.1` y otros programas de la PC podrían llamarla.
- **Opción B, quitar la autenticación por completo:** hay que tocar todos los endpoints protegidos y el modelo (los datos están ligados a `usuario_id`, incluso la clave de los archivos). Es un cambio grande y deja la API abierta a cualquier programa local.
- **Opción C, mantener el login como hoy:** sin cambios, pero un usuario único tendría que ingresar credenciales cada vez.
- **Cómo se crea el usuario (verificado en `migrations/versions/0006_seed_usuario_default.py`):** al correr las migraciones se inserta un usuario con `ADMIN_EMAIL` y `ADMIN_PASSWORD` tomados del entorno. Si esas variables no están, siembra `admin@agronexo.com` / `password123`, las credenciales de desarrollo. **En el instalador siempre hay que definirlas, con contraseña aleatoria por instalación**, para no distribuir una contraseña conocida. La migración usa `ON CONFLICT DO NOTHING`, así que solo siembra la primera vez.
- **Pendiente de diseño:** cómo recibe el frontend la sesión sin login (por ejemplo, que el lanzador llame a `/auth/login` con las credenciales guardadas y entregue el token a la ventana, o un endpoint local que emita el token). Se define al implementarlo.
- **Estado:** decidida, opción A (D4).

### Q4. Backup y restauración de los datos locales
- **Qué hay que resguardar:** la base de datos (lotes, vuelos, diagnósticos, usuario) y la carpeta de archivos (GeoTIFF originales, resultados, PDF) en `%APPDATA%\AgroNexo\`. El documento de opciones advierte que los GeoTIFF originales no se pueden recalcular.
- **Riesgo:** si la PC se rompe o se reinstala Windows, se pierde todo lo del usuario. Con la base de datos y los archivos en un solo equipo, no hay copia.
- **Opciones (se pueden combinar):** (1) botones "Exportar todo" e "Importar" que generan y restauran un solo `.zip` con el volcado de la base y los archivos; (2) carpeta de datos que el usuario copia a mano, con la app cerrada, porque copiar la base mientras corre no es seguro; (3) copia automática de la base antes de cada actualización o migración.
- **Qué pasa al desinstalar:** ver D7. **Copia antes de actualizar:** ver D11.
- **Estado:** decidida, opción 1 (D5). Al desinstalar: se pregunta si borrar los datos, casilla desmarcada por defecto (D7, opción 2 de Q6; las otras eran conservar siempre o borrar siempre).

### Q5. Mapas base sin internet
- **Situación:** 7 componentes del frontend bajan el mapa base de internet: Esri World Imagery en `MapaDibujoLote.jsx`, `MapaNEA.jsx` y `ModalCargaGeoTIFF.jsx`; OpenStreetMap en `MapaIndice.jsx`, `MapaZonas.jsx`, `MiniMapaLote.jsx` y `ModalLimites.jsx`. Sin conexión el fondo desaparece. La búsqueda de direcciones (Nominatim) y las imágenes satelitales (`desde-satelite`) quedan como funciones "solo con conexión".
- **Opciones:** (1) caché de tiles de la zona de cada lote, (2) mapa liviano incluido en el instalador, (3) fondo neutro con solo polígonos.
- **Estado:** decidida, opción 3 como respaldo sin conexión (D6), ajustada por D8: con internet se muestra el mapa base como hoy, y sin internet cae al fondo neutro. Mejora posible más adelante: opción 1 (caché de tiles).
- **Pendiente:** definir qué color de fondo usar y si la vista de dibujo del límite del lote (`MapaDibujoLote.jsx`) necesita algún apoyo sin mapa.

### Q7. Correo del usuario en el primer arranque
- **Idea planteada (2026-10-29):** que el usuario ponga su correo la primera vez y esa sea la cuenta bajo la que se guardan sus datos, en vez del `admin@agronexo.com` genérico.
- **Interpretación de Claude (confirmada por el usuario):** pantalla de bienvenida única, solo la primera vez, que pide nombre y correo. No es un login: no pide contraseña ni se vuelve a mostrar, y la sesión sigue siendo automática (D4). El correo no se verifica, porque no hay internet, y es solo la identidad del perfil, para reportes y órdenes de trabajo.
- **A favor:** perfil personalizado desde el inicio; al restaurar un backup en otra PC (D5) el usuario reconoce su cuenta.
- **Detalle de diseño pendiente:** la migración `0006` siembra el usuario antes de que nadie lo escriba. Opciones: pedir el correo antes de las migraciones y pasarlo como `ADMIN_EMAIL`, o sembrar un usuario provisorio y actualizarlo después con el perfil (`/auth/me`).
- **Nota por D8:** no se puede contar con internet en el primer arranque (el instalador puede haberse copiado de un pendrive y abrirse en el campo). Además ya no hay servidor propio (D1) que mande un código de verificación al correo. La pantalla de bienvenida no debe depender de la conexión.
- **Estado:** confirmada por el usuario el 2026-10-29 (D10).

### Q8. Qué ve el usuario sin internet en las funciones que lo necesitan
- **Opciones:** (1) funciones deshabilitadas con aviso "Requiere conexión a internet"; (2) funciones ocultas; (3) indicador general "Sin conexión" más funciones deshabilitadas (recomendada por Claude).
- **Primera elección:** opción 2, ocultas.
- **Cambio (mismo día):** el usuario pidió que la opción se vea deshabilitada y que al pasar el mouse diga que no hay internet, o que se informe que no hay conexión (opción 1, con aviso). Motivo: ocultarlas hacía que el usuario no supiera que existían.
- **Indicador general:** sí, se agrega un aviso visible de "Sin conexión" / "Modo sin conexión" mientras no haya internet (opción 3 de las originales, combinada con la 1).
- **Estado:** decidida (D9): funciones deshabilitadas con aviso al pasar el mouse, más indicador general de modo sin conexión.

### Q6. Qué pasa al desinstalar
- **Opciones:** (1) conservar siempre los datos, (2) preguntar al desinstalar si borrarlos, (3) borrar siempre.
- **Estado:** decidida, opción 2 con la casilla desmarcada por defecto (D7).

### Q9. Copia automática antes de actualizar
- **Qué es:** guardar una copia de la base justo antes de correr las migraciones de una versión nueva, para poder volver atrás si salen mal.
- **Estado:** decidida, sí (D11).

### Q10. Alcance de la primera versión
- **Propuesta:** lote + GeoTIFF propio, índices y mapa de zonas, diagnóstico y PDF, backup Exportar/Importar. Para después: imágenes satelitales, actualizaciones automáticas, caché de mapas.
- **Estado:** decidida (D12).

## Abiertas (de la sección 16 de `opciones-app-escritorio.md`)

- Electron o Tauri (recomendado: Electron). Ligada al PDF: si GTK resulta caro de empaquetar, `printToPDF` de Electron es la salida.
- Cómo recibe el frontend la sesión automática (se define al implementar).
- Fechas, sprint y responsables de la primera versión (el alcance ya se decidió en D12).
- Consulta de marcas antes de invertir en nombre y firma de código.
- Quién aprueba la rama del spike.

## Estado del spike (2026-10-29)

Criterios 1 a 5 pasan, el 6 queda parcial; la decisión go / no-go formal sigue pendiente. Detalle en `spike-escritorio/INFORME.md`. Pendientes técnicos principales: probar las DLL de GTK junto a un ejecutable, revisar los `os.unlink` de `workers/gis/tasks.py`, unificar `pydantic` y Python.

## Historial de preguntas y respuestas

- **¿Qué eran A y B?** A: escritorio + Docker local (1 a 2 semanas, exige Docker Desktop). B: instalador autocontenido sin Docker (varias semanas). Se evaluó B con el spike.
- **¿Se puede hacer B?** Sí, ningún criterio del spike lo bloquea; queda trabajo de empaquetado (DLL de GTK, fuente DejaVu, versiones de dependencias, borrado de archivos, lanzador, instalador, firma). No se probó el instalador armado ni se validó la estimación de tiempo.
- **¿Por qué GTK es "caro" de empaquetar?** WeasyPrint depende de unas 27 DLL de GTK/Pango que tienen que ir junto al `.exe` (en una app congelada ignora `WEASYPRINT_DLL_DIRECTORIES`), más la configuración de fuentes. La alternativa `printToPDF` de Electron obliga a reescribir los dos generadores de PDF.
- **¿Qué beneficio tiene seguir con MinIO?** Cero cambios de código, ya probado en CI, URLs firmadas ya funcionando y compatibilidad con S3. En contra: proceso extra, licencia y disponibilidad del binario. Ver Q1.
- **¿Se puede cambiar a disco?** Sí, el cambio está acotado a `app/core/storage.py`.
- **Q1: ¿MinIO o disco?** Se eligió **disco** (D2). Aún no se implementó nada.
- **¿Por qué Docker y CI seguirían con MinIO, no se elimina?** No hacía falta mantenerlo: se propuso así solo para acotar el cambio. Con D1 no queda uso en producción, mantener dos backends es más código, y probar con disco en CI prueba lo mismo que se entrega. Se decidió eliminarlo por completo en dos pasos (D3).
- **Login (Q3):** se eligió sesión automática (D4). El usuario se crea con la migración `0006` desde `ADMIN_EMAIL` y `ADMIN_PASSWORD`; en el instalador la contraseña es aleatoria por instalación y el usuario nunca la ve (las variables de entorno son internas del lanzador).
- **Datos (Q4):** se eligió "Exportar todo" e "Importar" (D5).
- **Internet (D8):** la app funciona con y sin internet; las funciones online se habilitan con conexión. Cambió D6 (mapa con internet y fondo neutro sin él) y descartó verificar el correo.
- **Cómo avisar sin conexión (Q8):** primero ocultas, luego deshabilitadas con aviso al pasar el mouse más indicador de "Modo sin conexión" (D9).
- **Correo en el primer arranque (Q7):** confirmada la pantalla de bienvenida con nombre y correo (D10).
