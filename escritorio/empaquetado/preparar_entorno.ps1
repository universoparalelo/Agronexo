# Deja lista una PC para armar el instalador: entorno de Python, Postgres con PostGIS,
# librerias de Visual C++, GTK y el recorte de Postgres. Es lo que antes eran los pasos 1 a 5 del README.
# Uso: .\preparar_entorno.ps1 [-Base <carpeta de trabajo>]
# Se puede correr de nuevo: salta lo que ya esta hecho. Descarga unos 500 MB la primera vez.
param([string]$Base = (Join-Path $PSScriptRoot "..\..\..\trabajo-escritorio"))
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
New-Item -ItemType Directory $Base -Force | Out-Null
$Base = (Resolve-Path $Base).Path
$descargas = "$Base\descargas"
New-Item -ItemType Directory $descargas -Force | Out-Null

$urlPython = "https://www.python.org/ftp/python/3.14.4/python-3.14.4-amd64.exe"
$urlVcredist = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
$urlPostgres ="https://get.enterprisedb.com/postgresql/postgresql-16.15-1-windows-x64-binaries.zip"
$urlPostgis = "https://download.osgeo.org/postgis/windows/pg16/postgis-bundle-pg16-3.6.2x64.zip"
$urlGtk = "https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases/download/2022-01-04/gtk3-runtime-3.24.31-2022-01-04-ts-win64.exe"

function Bajar($url) {
    $archivo = Join-Path $descargas ([IO.Path]::GetFileName($url))
    if (-not (Test-Path $archivo)) {
        Write-Host "   bajando $([IO.Path]::GetFileName($url))"
        Invoke-WebRequest $url -OutFile "$archivo.parcial" -UseBasicParsing
        Move-Item "$archivo.parcial" $archivo
    }
    return $archivo
}

# --- 1) Entorno de Python ---
Write-Host "1) Entorno de Python"
if (-not (Test-Path "$Base\venv\Scripts\python.exe")) {
    $python = "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe"
    if (-not (Test-Path $python)) {
        # Instalacion solo para este usuario, sin administrador y sin tocar el PATH.
        Start-Process (Bajar $urlPython) -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=0", "Include_launcher=0", "Include_test=0" -Wait
        if (-not (Test-Path $python)) { throw "No se pudo instalar Python 3.14" }
    }
    & $python -m venv "$Base\venv"
    if ($LASTEXITCODE -ne 0) { throw "No se pudo crear el entorno de Python" }
}
# pip escribe avisos a la salida de errores; con "Stop" PowerShell 5.1 los toma como fallo aunque pip termine bien.
$ErrorActionPreference = "Continue"
& "$Base\venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r "$PSScriptRoot\requirements-empaquetado.txt"
$codigoPip = $LASTEXITCODE
$ErrorActionPreference = "Stop"
if ($codigoPip -ne 0) { throw "pip install fallo" }

# --- 2) Postgres con PostGIS ---
Write-Host "2) Postgres con PostGIS"
if (-not (Test-Path "$Base\pg\pgsql\bin\postgres.exe")) {
    Remove-Item "$Base\pg" -Recurse -Force -ErrorAction SilentlyContinue
    Expand-Archive (Bajar $urlPostgres) "$Base\pg" -Force
    $bundle = "$Base\pg\postgis-bundle"
    Expand-Archive (Bajar $urlPostgis) $bundle -Force
    $raiz = Get-ChildItem $bundle -Directory | Select-Object -First 1
    foreach ($carpeta in "bin", "lib", "share") {
        robocopy "$($raiz.FullName)\$carpeta" "$Base\pg\pgsql\$carpeta" /E /NFL /NDL /NJH /NJS /NP | Out-Null
        if ($LASTEXITCODE -ge 8) { throw "robocopy fallo copiando PostGIS ($carpeta)" }
    }
    Remove-Item $bundle -Recurse -Force
}
if (-not (Get-ChildItem "$Base\pg\pgsql\share\extension" -Filter "postgis.control")) { throw "PostGIS no quedo instalado en Postgres" }

# --- 3) Librerias de Visual C++ ---
Write-Host "3) Librerias de Visual C++"
New-Item -ItemType Directory "$Base\vcrt" -Force | Out-Null
$dllsVcrt = "vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll"
if ($dllsVcrt | Where-Object { -not (Test-Path "$env:SystemRoot\System32\$_") }) {
    # Una Windows recien instalada no las trae (es justo lo que Postgres necesita): se instala el
    # paquete oficial de Microsoft, que pide permisos de administrador.
    $instalador = Bajar $urlVcredist
    Start-Process $instalador -ArgumentList "/install", "/quiet", "/norestart" -Wait
}
foreach ($dll in $dllsVcrt) {
    if (-not (Test-Path "$env:SystemRoot\System32\$dll")) { throw "Falta $dll en System32 aunque se instalo el paquete de Visual C++" }
    Copy-Item "$env:SystemRoot\System32\$dll" "$Base\vcrt\$dll" -Force
}

# --- 4) GTK para el PDF ---
Write-Host "4) GTK"
if (-not (Test-Path "$Base\gtk\etc\fonts")) {
    $instalacion = "$Base\gtk3-runtime"
    if (-not (Test-Path "$instalacion\bin")) {
        $instalador = Bajar $urlGtk
        # /D tiene que ir ultimo y sin comillas. Es un instalador NSIS: /S no muestra ventanas.
        Start-Process $instalador -ArgumentList "/S", "/D=$instalacion" -Wait
    }
    & "$PSScriptRoot\preparar_gtk.ps1" -Instalacion $instalacion -Base $Base
    if ($LASTEXITCODE -ne 0) { throw "preparar_gtk.ps1 fallo" }
}

# --- 5) Postgres recortado ---
Write-Host "5) Postgres recortado"
if (-not (Test-Path "$Base\pg-min\pgsql\bin\postgres.exe")) {
    & "$PSScriptRoot\preparar_postgres.ps1" -Base $Base
}

Write-Host "Listo. Siguiente: armar_motor.ps1 y armar_instalador.ps1 (ver README.md)."
