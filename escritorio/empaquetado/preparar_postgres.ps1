# Recorta Postgres+PostGIS (de 1,2 GB a unos 400 MB) y le agrega las librerias de Visual C++.
# Sin ellas Postgres no arranca en una Windows limpia. Uso: .\preparar_postgres.ps1 [-Base <carpeta>]
param([string]$Base = (Join-Path $PSScriptRoot "..\..\..\trabajo-escritorio"))
$ErrorActionPreference = "Stop"
$Base = (Resolve-Path $Base).Path
$origen = "$Base\pg\pgsql"; $destino = "$Base\pg-min\pgsql"; $vcrt = "$Base\vcrt"
foreach ($ruta in "$origen\bin\postgres.exe", "$vcrt\vcruntime140.dll", "$vcrt\vcruntime140_1.dll", "$vcrt\msvcp140.dll") {
    if (-not (Test-Path $ruta)) { throw "Falta $ruta. Ver el README." }
}
# pgAdmin, StackBuilder, documentacion, headers y las DLL wx (de pgAdmin) no se usan.
robocopy $origen $destino /E /XD "pgAdmin 4" StackBuilder doc include /XF "wx*.dll" "stackbuilder*" ecpg.exe pgbench.exe /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy fallo ($LASTEXITCODE)" }
Copy-Item "$vcrt\*.dll" "$destino\bin\" -Force
"{0:N0} MB en {1}" -f ((Get-ChildItem $destino -Recurse -File | Measure-Object Length -Sum).Sum / 1MB), $destino
