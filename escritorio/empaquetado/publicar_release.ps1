# Sube a GitHub Releases el instalador que dejo armar_instalador.ps1, junto con los dos
# archivos que necesita la actualizacion automatica (latest.yml y el .blockmap).
# Uso: .\publicar_release.ps1 [-Notas <archivo .md>] [-Publicar]
# Sin -Publicar queda como borrador: las apps instaladas no lo ven hasta publicarlo en la web.
param(
    [string]$Notas,
    [switch]$Publicar
)
$ErrorActionPreference = "Stop"
$electron = (Resolve-Path (Join-Path $PSScriptRoot "..\electron")).Path
$version = (Get-Content "$electron\package.json" -Raw | ConvertFrom-Json).version
$tag = "v$version"
$dist = "$electron\dist"
$archivos = @(
    "$dist\AgroNexo-Setup-$version.exe",
    "$dist\AgroNexo-Setup-$version.exe.blockmap",
    "$dist\latest.yml"
)

# PowerShell 5.1 con "Stop" toma como error cualquier linea que gh escriba en stderr (avisos,
# progreso, "release not found"): se lo corre en "Continue" y se mira solo el codigo de salida.
function Invocar-GitHub {
    $ErrorActionPreference = "Continue"
    $script:salidaGh = @(& gh.exe @args 2>&1 | ForEach-Object { "$_" })
    $script:codigoGh = $LASTEXITCODE
}

if (-not (Get-Command gh.exe -ErrorAction SilentlyContinue)) { throw "Falta gh (GitHub CLI): https://cli.github.com" }
Invocar-GitHub auth status
if ($codigoGh -ne 0) { throw "gh no tiene sesion iniciada: correr 'gh auth login'" }

foreach ($a in $archivos) {
    if (-not (Test-Path $a)) { throw "Falta $a. Armar primero el instalador con armar_instalador.ps1" }
}
# Si latest.yml es de otra corrida, las apps bajarian un instalador que no coincide.
if (-not (Select-String -Path "$dist\latest.yml" -Pattern "^version: $([regex]::Escape($version))$" -Quiet)) {
    throw "latest.yml no corresponde a la version $version. Volver a armar el instalador."
}

# La release apunta a un tag que ya tiene que estar en GitHub (sale de main, por PR).
$remoto = git ls-remote --tags origin "refs/tags/$tag"
if (-not $remoto) {
    throw "El tag $tag no esta en GitHub. Crearlo desde main: git tag -a $tag -m 'Release $tag'; git push origin $tag"
}
Invocar-GitHub release view $tag
if ($codigoGh -eq 0) { throw "Ya existe una release $tag en GitHub. Subir la version en package.json o borrarla a mano." }

$opciones = @($tag) + $archivos + @("--verify-tag", "--title", "AgroNexo $tag")
if ($Notas) { $opciones += @("--notes-file", (Resolve-Path $Notas).Path) } else { $opciones += @("--generate-notes") }
if (-not $Publicar) { $opciones += "--draft" }

"Subiendo $tag ({0:N0} MB)..." -f ((Get-Item $archivos[0]).Length / 1MB)
Invocar-GitHub release create @opciones
$salidaGh
if ($codigoGh -ne 0) { throw "gh release create fallo" }
if ($Publicar) { "Publicada: las apps instaladas la van a ofrecer en su proximo arranque." }
else { "Borrador creado: revisarlo y publicarlo desde la web (Edit > Publish release)." }
