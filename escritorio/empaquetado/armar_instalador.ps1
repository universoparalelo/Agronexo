# Arma el Setup.exe con electron-builder, con el motor adentro.
# Uso: .\armar_instalador.ps1 [-Base <carpeta de trabajo>]. Resultado: escritorio\electron\dist\
param([string]$Base = (Join-Path $PSScriptRoot "..\..\..\trabajo-escritorio"))
$ErrorActionPreference = "Stop"
$Base = (Resolve-Path $Base).Path
$electron = (Resolve-Path (Join-Path $PSScriptRoot "..\electron")).Path
foreach ($ruta in "$Base\pg-min\pgsql\bin\postgres.exe", "$Base\motor2\dist\agronexo-api\agronexo-api.exe", "$Base\motor2\dist\agronexo-worker\agronexo-worker.exe") {
    if (-not (Test-Path $ruta)) { throw "Falta $ruta. Ver el README." }
}
# electron-builder no acepta rutas absolutas en extraResources: va relativa a escritorio\electron.
$rel = [Uri]::UnescapeDataString(([Uri]"$electron\").MakeRelativeUri([Uri]"$Base\").ToString()).TrimEnd("/")
$env:AGRONEXO_MOTOR_DIR = $rel
Push-Location $electron
try {
    if (-not (Test-Path "node_modules\electron-builder")) { npm ci; if ($LASTEXITCODE -ne 0) { throw "npm ci fallo" } }
    npm run dist
    if ($LASTEXITCODE -ne 0) { throw "npm run dist fallo" }
} finally { Pop-Location }
Get-ChildItem "$electron\dist" -Filter *.exe | ForEach-Object { "{0}: {1:N0} MB" -f $_.FullName, ($_.Length / 1MB) }
