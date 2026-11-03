# Armar la app de escritorio desde cero

Scripts para generar el `Setup.exe` de AgroNexo en Windows. El repo guarda solo el código: los programas grandes (Postgres, la API y el worker empaquetados, el entorno de Python) se generan en una **carpeta de trabajo** fuera del repo y nunca se suben a Git.

Por defecto la carpeta de trabajo es `trabajo-escritorio\`, al lado de la carpeta del repo (`Proyecto\trabajo-escritorio` si el repo está en `Proyecto\Agronexo`). Todos los scripts aceptan `-Base <otra carpeta>`.

## Para qué sirve (y para qué no)

Editar el código **no** requiere nada de esto: se sigue trabajando con Docker (`docker compose up`) como siempre. Estos scripts sirven para que cualquier integrante del equipo pueda **volver a armar el `Setup.exe`** después de cambiar código, sin depender de la PC de una sola persona.

La preparación del entorno (pasos 1 a 5) se probó desde cero en un Windows limpio (Windows Sandbox) con `preparar_entorno.ps1`. Armar el motor y el instalador (pasos 6 y 7) se probó con el entorno de una PC ya preparada. Si algo falla, anotarlo en `docs/release-v4.0.0.md`.

## Qué hace falta

- Windows 10 u 11 de 64 bits, con **PowerShell** (no hace falta ser administrador).
- **Python 3.14** (comando `py -3.14`), **Node 24** y Git.
- Unos 8 GB libres en la carpeta de trabajo.

## Pasos

Se hacen una sola vez, salvo el 6 y el 7, que se repiten cada vez que cambia el código.

**Atajo para los pasos 1 a 5:** un solo comando que baja e instala todo (Python 3.14, Postgres con PostGIS, las librerías de Visual C++ y GTK) y recorta Postgres. Descarga unos 500 MB y tarda unos 40 minutos la primera vez; si se corre de nuevo, salta lo que ya está hecho. Si faltan las librerías de Visual C++ o hay que instalar GTK, puede pedir permisos de administrador.

```powershell
.\preparar_entorno.ps1
```

Si preferís hacerlo a mano, o algo falla, los pasos de abajo explican qué hace cada parte.

**1. Entorno de Python** (con las versiones exactas de `requirements-empaquetado.txt`; no son las de Docker porque `pydantic 2.10.4` no tiene rueda para Python 3.14):

```powershell
py -3.14 -m venv ..\..\..\trabajo-escritorio\venv
..\..\..\trabajo-escritorio\venv\Scripts\python -m pip install -r requirements-empaquetado.txt
```

**2. Postgres con PostGIS** (versiones usadas: Postgres 16.15 y PostGIS 3.6.2): bajar de EDB el zip de binarios de Postgres 16 para Windows x64, descomprimirlo en `trabajo-escritorio\pg\` de modo que quede `pg\pgsql\bin\postgres.exe`, y copiar encima el bundle de PostGIS para Postgres 16.

**3. Librerías de Visual C++** (Postgres no arranca en una Windows limpia sin ellas): copiar `vcruntime140.dll`, `vcruntime140_1.dll` y `msvcp140.dll` desde `C:\Windows\System32` a `trabajo-escritorio\vcrt\`.

**4. GTK para el PDF:** instalar *GTK3 Runtime* (versión 3.24.31 de tschoonj, `gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe`, en https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer) y correr:

```powershell
.\preparar_gtk.ps1
```

Copia solo las ~26 DLL que necesita WeasyPrint a `trabajo-escritorio\gtk\`.

**5. Postgres recortado** (de 1,2 GB a unos 400 MB: saca pgAdmin, StackBuilder y documentación, y agrega las librerías del paso 3):

```powershell
.\preparar_postgres.ps1
```

**6. Frontend y motor** (la API y el worker; tarda unos 5 minutos):

```powershell
cd ..\..\frontend; npm ci; npm run build; cd ..\escritorio\empaquetado
.\armar_motor.ps1
```

`armar_motor.ps1` usa el código de la rama que tengas activa. Con `-Que api` o `-Que worker` arma solo uno.

**7. Instalador:**

```powershell
.\armar_instalador.ps1
```

El resultado queda en `escritorio\electron\dist\AgroNexo (prototipo) Setup 0.0.0.exe` (unos 430 MB). Es por usuario, sin administrador y sin firmar: Windows muestra "editor desconocido" y hay que elegir "Ejecutar de todas formas".

## Cuándo repetir qué

| Cambió | Volver a correr |
|---|---|
| Código de `app/`, `workers/` o `migrations/` | paso 6 y 7 |
| Solo el frontend | `npm run build` en `frontend\`, y pasos 6 (`-Que api`) y 7 |
| Solo el lanzador (`escritorio\electron`) | paso 7 |

## Probarlo en una Windows limpia

Windows Sandbox (necesita 10 GB de RAM) con una carpeta que contenga el `Setup.exe` y las pruebas de `trabajo-escritorio\sandbox_scripts`. Las decisiones y los resultados están en `docs/decisiones-app-escritorio.md` y `docs/release-v4.0.0.md`.

## Qué no cubre

No firma el instalador, no actualiza las DLL de GTK (la versión es de 2022) ni genera instaladores para otros sistemas: el alcance es académico y el programa no se reparte.
