#Requires -Version 5.1
<#
.SYNOPSIS
    Configura o ambiente do Mangakakalot Kindle Downloader.

.DESCRIPTION
    Valida as dependencias externas, cria o ambiente virtual com `uv` e instala
    os pacotes Python. O Python NAO precisa estar instalado no sistema: o uv
    baixa e gerencia o 3.12 sozinho.

.PARAMETER Force
    Recria o ambiente virtual do zero, mesmo que ja exista.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File setup.ps1

.NOTES
    Se a politica de execucao bloquear o script, rode com -ExecutionPolicy Bypass
    (como no exemplo) ou libere a sessao com:
        Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#>

[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# ---------------------------------------------------------------- helpers ----

function Write-Title($Text) {
    Write-Host ""
    Write-Host "  $Text" -ForegroundColor White
    Write-Host "  $('-' * $Text.Length)" -ForegroundColor DarkGray
}

function Write-Step($Number, $Total, $Text) {
    Write-Host ""
    Write-Host "[$Number/$Total] $Text" -ForegroundColor Cyan
}

function Write-Ok($Text)   { Write-Host "  [ok]   $Text" -ForegroundColor Green }
function Write-Warn($Text) { Write-Host "  [!]    $Text" -ForegroundColor Yellow }
function Write-Fail($Text) { Write-Host "  [x]    $Text" -ForegroundColor Red }
function Write-Info($Text) { Write-Host "         $Text" -ForegroundColor DarkGray }

function Test-Executable($Name) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Find-FirstPath([string[]]$Candidates) {
    foreach ($path in $Candidates) {
        $expanded = [Environment]::ExpandEnvironmentVariables($path)
        if (Test-Path $expanded) { return $expanded }
    }
    return $null
}

# ------------------------------------------------------------------- main ----

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

Write-Host ""
Write-Host "==================================================" -ForegroundColor Magenta
Write-Host "  Mangakakalot Kindle Downloader  -  Setup" -ForegroundColor Magenta
Write-Host "==================================================" -ForegroundColor Magenta

$totalSteps = 4
$blockers = @()
$warnings = @()

# --- 1. uv -------------------------------------------------------------------
Write-Step 1 $totalSteps "Verificando o uv (gerenciador de pacotes e Python)"

$uv = Test-Executable "uv"
if ($uv) {
    $uvVersion = (& uv --version) -join ""
    Write-Ok "$uvVersion"
    Write-Info $uv
}
else {
    Write-Fail "uv nao encontrado."
    Write-Info "O uv gerencia o ambiente e baixa o proprio Python 3.12."

    $answer = Read-Host "         Instalar o uv agora via winget? (S/N)"
    if ($answer -match '^[SsYy]') {
        if (Test-Executable "winget") {
            & winget install --id astral-sh.uv -e --accept-source-agreements --accept-package-agreements
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                        [System.Environment]::GetEnvironmentVariable("Path", "User")
            $uv = Test-Executable "uv"
        }
        else {
            Write-Fail "winget tambem nao esta disponivel."
        }
    }

    if (-not $uv) {
        $blockers += "uv nao instalado. Veja https://docs.astral.sh/uv/getting-started/installation/"
        Write-Info "Alternativa: irm https://astral.sh/uv/install.ps1 | iex"
    }
    else {
        Write-Ok "uv instalado com sucesso."
    }
}

# --- 2. Dependencias externas ------------------------------------------------
Write-Step 2 $totalSteps "Verificando as dependencias externas"

# Chrome: necessario para o undetected_chromedriver burlar o Cloudflare.
$chrome = Find-FirstPath @(
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
)
if ($chrome) {
    $chromeVersion = (Get-Item $chrome).VersionInfo.ProductVersion
    Write-Ok "Google Chrome $chromeVersion"
}
else {
    $blockers += "Google Chrome nao encontrado (necessario para o bypass do Cloudflare). https://www.google.com/chrome/"
    Write-Fail "Google Chrome nao encontrado."
}

# 7-Zip: o KCC o invoca para montar os arquivos do ebook.
$sevenZip = Find-FirstPath @(
    "C:\Program Files\7-Zip\7z.exe",
    "C:\Program Files (x86)\7-Zip\7z.exe"
)
if ($sevenZip) {
    Write-Ok "7-Zip"
    Write-Info $sevenZip
}
else {
    $blockers += "7-Zip nao encontrado (o KCC precisa dele para gerar o ebook). https://www.7-zip.org/"
    Write-Fail "7-Zip nao encontrado."
}

# Kindle Previewer: exigido pelo KCC apenas para compilar MOBI/AZW3.
$previewer = Find-FirstPath @(
    "%LOCALAPPDATA%\Amazon\Kindle Previewer 3\Kindle Previewer 3.exe",
    "%UserProfile%\Kindle Previewer 3\Kindle Previewer 3.exe"
)
if ($previewer) {
    Write-Ok "Kindle Previewer 3"
}
else {
    $warnings += "Kindle Previewer 3 nao encontrado: a saida MOBI/AZW3 vai falhar (EPUB continua funcionando)."
    Write-Warn "Kindle Previewer 3 nao encontrado."
    Write-Info "Necessario para MOBI/AZW3. https://www.amazon.com/Kindle-Previewer/b?node=21381691011"
}

if ($blockers.Count -gt 0) {
    Write-Title "Setup interrompido"
    foreach ($b in $blockers) { Write-Fail $b }
    Write-Host ""
    exit 1
}

# --- 3. Ambiente virtual -----------------------------------------------------
Write-Step 3 $totalSteps "Preparando o ambiente virtual (.venv)"

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

if ($Force -and (Test-Path ".venv")) {
    Write-Warn "-Force: removendo o .venv existente."
    Remove-Item -Recurse -Force ".venv"
}

if (Test-Path $venvPython) {
    $existing = (& $venvPython --version) -join ""
    Write-Ok "Ambiente virtual ja existe ($existing)"
}
else {
    Write-Info "Criando o ambiente com Python 3.12 (o uv baixa se necessario)..."
    & uv venv --python 3.12
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Falha ao criar o ambiente virtual."
        exit 1
    }
    Write-Ok "Ambiente virtual criado."
}

# --- 4. Dependencias Python --------------------------------------------------
Write-Step 4 $totalSteps "Instalando as dependencias Python"

# O --python aponta o alvo explicitamente. Sem isso o uv pode instalar noutro
# ambiente e deixar o .venv vazio, sem erro aparente.
& uv pip install -r requirements.txt --python $venvPython
if ($LASTEXITCODE -ne 0) {
    Write-Fail "Falha ao instalar as dependencias."
    exit 1
}

# Verificacao real: confirma que os pacotes criticos importam de fato, em vez de
# confiar so no codigo de saida do instalador.
$check = & $venvPython -c "import undetected_chromedriver, selenium, bs4, PIL, requests, PySide6; print('ok')" 2>$null
if ($check -ne "ok") {
    Write-Fail "As dependencias foram instaladas mas nao importam corretamente."
    exit 1
}
Write-Ok "Todas as dependencias instaladas e verificadas."

# --- Resumo ------------------------------------------------------------------
Write-Title "Setup concluido"

foreach ($w in $warnings) { Write-Warn $w }

Write-Host ""
Write-Host "  Proximo passo:" -ForegroundColor White
Write-Host "    .\run.ps1" -ForegroundColor Cyan
Write-Host "         modo interativo (pergunta URL, capitulos e perfil)"
Write-Host ""
Write-Host "    .\.venv\Scripts\python.exe src\main.py -u ""<URL>"" -p KPW6" -ForegroundColor Cyan
Write-Host "         modo CLI direto"
Write-Host ""
