# Lanzador de la app de escritorio (prototipo)

Abre una ventana de Electron que arranca Postgres, la API y el worker de AgroNexo, espera a que la API responda y muestra la aplicación. Al cerrar la ventana frena todo en orden (worker, API, Postgres).

**Es la fase 1 del lanzador.** Todavía no es el instalador: usa los programas ya empaquetados de la carpeta `trabajo-escritorio\` (fuera del repo, ver su `LEEME.md`). Se puede apuntar a otra ubicación con la variable `AGRONEXO_PROTOTIPO_DIR`.

## Cómo probarlo

Requiere Node 24 y no se puede correr como administrador (Postgres no arranca con permisos elevados).

```bash
cd escritorio/electron
npm ci
node node_modules/electron/install.js
npm start
```

El segundo comando descarga el binario de Electron (unos 200 MB, desde GitHub, verificado con `checksums.json`): esta versión no lo baja sola al instalar. Hay que repetirlo en cada máquina nueva.

La primera vez crea la base de datos en `%APPDATA%\AgroNexo (prototipo)\`, que también guarda los archivos (`archivos\`), los registros (`logs\`) y los secretos (`secretos.json`). Para entrar a la app, el usuario es `admin@agronexo.com` y la contraseña es el valor `adminPassword` de `secretos.json`. Para empezar de cero, cerrar la app y borrar esa carpeta. (`pg_ctl stop` no hace falta: la app detiene Postgres al cerrar. Si la app se cierra a la fuerza, el próximo arranque detiene el Postgres que haya quedado.)

## Seguridad

- La ventana corre aislada: `contextIsolation` y `sandbox` activos, sin `nodeIntegration`, sin permisos del navegador, y solo puede mostrar la API local (cualquier otra navegación o ventana nueva se bloquea).
- Postgres y la API escuchan solo en `127.0.0.1`, en puertos libres elegidos al azar.
- Postgres usa autenticación `scram-sha-256`. La contraseña de la base, la clave JWT y la contraseña del usuario son aleatorias, se generan en el primer arranque y no aparecen en los registros.
- Los programas se lanzan sin shell, con los argumentos como lista.
- Electron está fijado a una versión exacta y `package-lock.json` va en el repo. Instalar siempre con `npm ci`.

## Armar el instalador

Genera `dist\AgroNexo (prototipo) Setup 0.0.0.exe` (unos 430 MB) con el motor adentro. Necesita la carpeta `trabajo-escritorio\` con `pg-min\` (Postgres sin pgAdmin, documentación ni StackBuilder), y `motor2\dist\` con la API y el worker empaquetados. La ruta va relativa a esta carpeta (electron-builder no acepta absolutas en `extraResources`):

```powershell
$env:AGRONEXO_MOTOR_DIR='../../../trabajo-escritorio'
npm run dist
```

El instalador es por usuario (no pide administrador: Postgres no arranca con permisos elevados) y todavía **no está firmado**, así que Windows avisa de "editor desconocido". Al desinstalar pregunta si se borran también los datos (por defecto no, decisión D7; ver `instalador\installer.nsh`). `npm audit` marca 15 avisos moderados, todos de `minimatch` dentro de electron-builder: es una herramienta de armado que corre solo en la PC de desarrollo y no viaja en la app.

## Qué falta (fases siguientes)

Rotación de los registros, sesión automática sin login, política de contenido (CSP) y `fuses` de Electron para el paquete final, ícono propio, firma de código, probar el instalador y el desinstalador en una Windows limpia y cambiar las DLL de GTK por una versión más nueva.
