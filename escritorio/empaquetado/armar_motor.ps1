# Arma la API y el worker como programas sueltos (PyInstaller, sin Python instalado en destino).
# Uso: .\armar_motor.ps1 [-Que api|worker|ambos] [-Base <carpeta de trabajo>]
# Usa el codigo del repo tal como esta en la rama actual. Ver README.md de esta carpeta.
param(
    [ValidateSet("api", "worker", "ambos")][string]$Que = "ambos",
    [string]$Base = (Join-Path $PSScriptRoot "..\..\..\trabajo-escritorio")
)
$ErrorActionPreference = "Stop"
$Base = (Resolve-Path $Base).Path
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$py = "$Base\venv\Scripts\python.exe"
if (-not (Test-Path $py)) { throw "Falta $Base\venv. Ver el paso 1 del README." }
if (-not (Test-Path "$repo\frontend\dist\index.html")) { throw "Falta frontend\dist. Correr 'npm ci; npm run build' en frontend\." }
if ($Que -ne "worker" -and -not (Test-Path "$Base\gtk")) { throw "Falta $Base\gtk. Correr preparar_gtk.ps1." }

# Solo para que los modulos puedan importarse al analizar: no se guardan en los programas.
$env:PYTHONPATH = $repo
$azar = -join ((1..24) | ForEach-Object { '{0:x}' -f (Get-Random -Maximum 16) })
$env:POSTGRES_HOST = "127.0.0.1"; $env:POSTGRES_DB = "agronexo"; $env:POSTGRES_USER = "agronexo"; $env:POSTGRES_PASSWORD = $azar
$env:CELERY_BROKER_URL = "sqla+postgresql+psycopg2://agronexo:${azar}@127.0.0.1/agronexo"
$env:CELERY_RESULT_BACKEND = "db+postgresql+psycopg2://agronexo:${azar}@127.0.0.1/agronexo"
$env:STORAGE_BACKEND = "disk"; $env:STORAGE_PATH = "$Base\archivos_motor"
$env:JWT_SECRET_KEY = $azar + $azar

$salida = "$Base\motor2\dist"
$comunes = @(
    "--noconfirm", "--clean", "--onedir", "--distpath", $salida, "--paths", $repo,
    "--collect-submodules", "celery", "--collect-submodules", "kombu", "--collect-submodules", "billiard",
    "--collect-submodules", "sqlalchemy.dialects.postgresql",
    "--hidden-import", "asyncpg", "--hidden-import", "psycopg2"
)

function Armar($nombre) {
    $trabajo = @("--workpath", "$Base\motor2\build_$nombre", "--specpath", "$Base\motor2\spec")
    if ($nombre -eq "api") {
        $propios = @(
            "--name", "agronexo-api",
            "--add-data", "$repo\app\reportes\templates;app\reportes\templates",
            "--add-data", "$repo\app\ordenes_trabajo\templates;app\ordenes_trabajo\templates",
            "--add-data", "$repo\migrations;migrations",
            "--collect-submodules", "uvicorn", "--collect-submodules", "alembic",
            "--hidden-import", "multipart", "--hidden-import", "python_multipart", "--hidden-import", "email_validator",
            "$repo\escritorio\api.py"
        )
    } else {
        $propios = @(
            "--name", "agronexo-worker", "--collect-submodules", "workers",
            "--collect-all", "rasterio", "--collect-all", "pyproj", "--collect-all", "pyogrio",
            "--collect-all", "skimage", "--collect-submodules", "scipy",
            "$repo\escritorio\worker.py"
        )
    }
    & $py -m PyInstaller @comunes @trabajo @propios
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller fallo armando $nombre" }
    $carpeta = "$salida\agronexo-$nombre"
    if ($nombre -eq "api") {
        # Fuera del programa a proposito: el frontend y GTK se reemplazan sin volver a armar todo.
        foreach ($extra in "frontend", "gtk") { Remove-Item "$carpeta\$extra" -Recurse -Force -ErrorAction SilentlyContinue }
        Copy-Item "$repo\frontend\dist" "$carpeta\frontend" -Recurse
        Copy-Item "$Base\gtk" "$carpeta\gtk" -Recurse
    }
    "{0}: {1:N0} MB en {2}" -f $nombre, ((Get-ChildItem $carpeta -Recurse -File | Measure-Object Length -Sum).Sum / 1MB), $carpeta
}

if ($Que -in "api", "ambos") { Armar "api" }
if ($Que -in "worker", "ambos") { Armar "worker" }
