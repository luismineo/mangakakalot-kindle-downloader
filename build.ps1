#Requires -Version 5.1
<#
.SYNOPSIS
    Gera o executavel do Mangakakalot Kindle Downloader.

.DESCRIPTION
    Empacota o projeto com PyInstaller (--onedir) usando o app.spec. O resultado
    fica em dist\MangakakalotDownloader\.

    O executavel NAO embute Chrome, 7-Zip nem Kindle Previewer 3: eles precisam
    estar instalados na maquina que for usar o programa.

.PARAMETER Clean
    Apaga build\ e dist\ antes de comecar.

.PARAMETER SkipTest
    Nao roda a verificacao pos-build do executavel.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File build.ps1 -Clean
#>

[CmdletBinding()]
param(
    [switch]$Clean,
    [switch]$SkipTest
)

$ErrorActionPreference = "Stop"

function Write-Step($Number, $Total, $Text) {
    Write-Host ""
    Write-Host "[$Number/$Total] $Text" -ForegroundColor Cyan
}
function Write-Ok($Text)   { Write-Host "  [ok]   $Text" -ForegroundColor Green }
function Write-Warn($Text) { Write-Host "  [!]    $Text" -ForegroundColor Yellow }
function Write-Fail($Text) { Write-Host "  [x]    $Text" -ForegroundColor Red }
function Write-Info($Text) { Write-Host "         $Text" -ForegroundColor DarkGray }

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
$distDir = Join-Path $projectRoot "dist\MangakakalotDownloader"
$exePath = Join-Path $distDir "MangakakalotDownloader.exe"

Write-Host ""
Write-Host "==================================================" -ForegroundColor Magenta
Write-Host "  Mangakakalot Kindle Downloader  -  Build" -ForegroundColor Magenta
Write-Host "==================================================" -ForegroundColor Magenta

$totalSteps = 4

# --- 1. Pre-requisitos -------------------------------------------------------
Write-Step 1 $totalSteps "Verificando o ambiente de build"

if (-not (Test-Path $venvPython)) {
    Write-Fail "Ambiente virtual nao encontrado. Rode o setup.ps1 primeiro."
    exit 1
}
Write-Ok "Ambiente virtual encontrado."

& $venvPython -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Warn "PyInstaller nao instalado. Instalando as dependencias de build..."
    & uv pip install -r requirements-dev.txt --python $venvPython
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Falha ao instalar o PyInstaller."
        exit 1
    }
}
$pyiVersion = & $venvPython -c "import PyInstaller; print(PyInstaller.__version__)"
Write-Ok "PyInstaller $pyiVersion"

# --- 2. Limpeza --------------------------------------------------------------
Write-Step 2 $totalSteps "Preparando os diretorios"

if ($Clean) {
    foreach ($dir in @("build", "dist")) {
        if (Test-Path $dir) {
            Remove-Item -Recurse -Force $dir
            Write-Info "removido: $dir\"
        }
    }
    Write-Ok "Limpeza concluida."
}
else {
    Write-Info "Build incremental (use -Clean para recomecar do zero)."
}

# --- 3. Build ----------------------------------------------------------------
Write-Step 3 $totalSteps "Empacotando com o PyInstaller (leva alguns minutos)"

& $venvPython -m PyInstaller app.spec --noconfirm --log-level WARN
if ($LASTEXITCODE -ne 0) {
    Write-Fail "O PyInstaller falhou."
    exit 1
}

if (-not (Test-Path $exePath)) {
    Write-Fail "O build terminou, mas o executavel nao foi encontrado em $exePath"
    exit 1
}

$sizeMb = [math]::Round((Get-ChildItem $distDir -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB, 1)
Write-Ok "Executavel gerado ($sizeMb MB no total)."
Write-Info $exePath

# --- 4. Verificacao ----------------------------------------------------------
Write-Step 4 $totalSteps "Verificando o executavel"

if ($SkipTest) {
    Write-Warn "Verificacao pulada (-SkipTest)."
}
else {
    # O --help exercita o congelado de verdade: se algum import quebrou no bundle,
    # ele falha aqui, e nao so quando o usuario tentar baixar algo.
    $helpOutput = & $exePath --help
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "O executavel falhou ao rodar --help (exit $LASTEXITCODE)."
        Write-Info "Rode '$exePath --help' para ver o erro."
        exit 1
    }
    if ($helpOutput -match "--gui") {
        Write-Ok "O executavel responde ao --help com a CLI intacta."
    }
    else {
        Write-Fail "O --help respondeu, mas a saida veio inesperada."
        exit 1
    }
}

# --- Resumo ------------------------------------------------------------------
Write-Host ""
Write-Host "  Build concluido" -ForegroundColor White
Write-Host "  ---------------" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Pasta a distribuir:" -ForegroundColor White
Write-Host "    $distDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Uso:" -ForegroundColor White
Write-Host "    MangakakalotDownloader.exe --gui" -ForegroundColor Cyan
Write-Host "    MangakakalotDownloader.exe -u ""<URL>"" -p KPW6" -ForegroundColor Cyan
Write-Host ""
Write-Warn "A maquina de destino ainda precisa de: Google Chrome, 7-Zip e"
Write-Info "Kindle Previewer 3 (este ultimo so para MOBI/AZW3)."
Write-Host ""
