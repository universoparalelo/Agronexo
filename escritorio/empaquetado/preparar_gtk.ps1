# Copia a <Base>\gtk solo las DLL de GTK que necesita WeasyPrint (unas 26, ~11 MB) y la
# configuracion de fuentes. Requiere GTK3 Runtime instalado (ver README).
# Uso: .\preparar_gtk.ps1 [-Instalacion <carpeta de GTK>] [-Base <carpeta>]
param(
    [string]$Instalacion = "C:\Program Files\GTK3-Runtime Win64",
    [string]$Base = (Join-Path $PSScriptRoot "..\..\..\trabajo-escritorio")
)
$ErrorActionPreference = "Stop"
$Base = (Resolve-Path $Base).Path
$py = "$Base\venv\Scripts\python.exe"
if (-not (Test-Path "$Instalacion\bin")) { throw "No hay GTK en $Instalacion. Ver el README." }
$destino = "$Base\gtk"
Remove-Item $destino -Recurse -Force -ErrorAction SilentlyContinue
& $py -I "$PSScriptRoot\gtk_cierre.py" "$Instalacion\bin" $destino
if ($LASTEXITCODE -ne 0) { throw "gtk_cierre.py fallo" }
New-Item -ItemType Directory "$destino\etc" -Force | Out-Null
Copy-Item "$Instalacion\etc\fonts" "$destino\etc\fonts" -Recurse
