#Requires -Version 5.1
<#
.SYNOPSIS
    Empacota e publica um release do Mangakakalot Kindle Downloader no GitHub.

.DESCRIPTION
    Grava a versao e o canal em src\version.py (fonte unica de verdade, lida
    tanto pela CLI quanto pela GUI), reconstroi o executavel via build.ps1,
    empacota dist\MangakakalotDownloader\ num zip nomeado com a versao e
    publica esse zip como GitHub Release via gh CLI.

    Nao commita, nao cria tag local nem faz push: o "gh release create" cria a
    tag no remoto, apontando para o commit atual, sem tocar no historico local.

.PARAMETER Version
    Versao no formato SemVer, ex.: 0.1.0

.PARAMETER Channel
    Canal do release, ex.: dev, pre, stable

.PARAMETER SkipBuild
    Pula o build.ps1 e reaproveita o dist\MangakakalotDownloader\ existente.

.PARAMETER Publish
    Publica o release direto. Sem isso, o release fica como draft no GitHub.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File release.ps1 -Version 0.1.0 -Channel pre
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version,

    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[a-zA-Z0-9]+$')]
    [string]$Channel,

    [switch]$SkipBuild,
    [switch]$Publish
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

function Test-Executable($Name) {
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$versionFile = Join-Path $projectRoot "src\version.py"
$distDir = Join-Path $projectRoot "dist\MangakakalotDownloader"
$exePath = Join-Path $distDir "MangakakalotDownloader.exe"
$releaseDir = Join-Path $projectRoot "release"
$zipName = "mkl-dl-kcc_$Version-$Channel.zip"
$zipPath = Join-Path $releaseDir $zipName
$tag = "v$Version-$Channel"

Write-Host ""
Write-Host "==================================================" -ForegroundColor Magenta
Write-Host "  Mangakakalot Kindle Downloader  -  Release" -ForegroundColor Magenta
Write-Host "==================================================" -ForegroundColor Magenta
Write-Info "Versao: $Version   Canal: $Channel   Tag: $tag"

$totalSteps = 5

# --- 1. gh CLI -----------------------------------------------------------------
Write-Step 1 $totalSteps "Verificando o gh CLI (GitHub)"

$gh = Test-Executable "gh"
if ($gh) {
    Write-Ok "gh encontrado."
    Write-Info $gh
}
else {
    Write-Fail "gh nao encontrado."
    Write-Info "O gh cria o release e envia o zip como asset."

    $answer = Read-Host "         Instalar o gh agora via winget? (S/N)"
    if ($answer -match '^[SsYy]') {
        if (Test-Executable "winget") {
            & winget install --id GitHub.cli -e --accept-source-agreements --accept-package-agreements
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                        [System.Environment]::GetEnvironmentVariable("Path", "User")
            $gh = Test-Executable "gh"
        }
        else {
            Write-Fail "winget tambem nao esta disponivel."
        }
    }

    if (-not $gh) {
        Write-Fail "gh nao instalado. Veja https://cli.github.com/"
        exit 1
    }
    Write-Ok "gh instalado com sucesso."
}

& gh auth status 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Fail "gh nao esta autenticado."
    Write-Info "Rode 'gh auth login' e tente de novo."
    exit 1
}
Write-Ok "gh autenticado."

# --- 2. Fonte da verdade: src\version.py ----------------------------------------
Write-Step 2 $totalSteps "Atualizando src\version.py"

if (-not (Test-Path $versionFile)) {
    Write-Fail "Arquivo nao encontrado: $versionFile"
    exit 1
}

$content = [System.IO.File]::ReadAllText($versionFile)
$versionPattern = '(?m)^VERSION = "[^"]*"$'
$channelPattern = '(?m)^CHANNEL = "[^"]*"$'

if ($content -notmatch $versionPattern) {
    Write-Fail "Nao encontrei uma linha 'VERSION = ""...""' em $versionFile"
    exit 1
}
if ($content -notmatch $channelPattern) {
    Write-Fail "Nao encontrei uma linha 'CHANNEL = ""...""' em $versionFile"
    exit 1
}

$newContent = $content -replace $versionPattern, "VERSION = `"$Version`""
$newContent = $newContent -replace $channelPattern, "CHANNEL = `"$Channel`""
[System.IO.File]::WriteAllText($versionFile, $newContent, (New-Object System.Text.UTF8Encoding($false)))

Write-Ok "src\version.py atualizado ($Version-$Channel)."

# --- 3. Build --------------------------------------------------------------------
Write-Step 3 $totalSteps "Gerando o executavel"

if ($SkipBuild) {
    Write-Warn "Build pulado (-SkipBuild)."
    if (-not (Test-Path $exePath)) {
        Write-Fail "Nenhum build existente em $exePath"
        Write-Info "Rode sem -SkipBuild, ou rode .\build.ps1 antes."
        exit 1
    }
    Write-Ok "Reaproveitando build existente."
}
else {
    & (Join-Path $projectRoot "build.ps1") -Clean
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "O build.ps1 falhou."
        exit 1
    }
    if (-not (Test-Path $exePath)) {
        Write-Fail "O build terminou, mas o executavel nao foi encontrado em $exePath"
        exit 1
    }
    Write-Ok "Executavel gerado."
}

# --- 4. Empacotar ------------------------------------------------------------------
Write-Step 4 $totalSteps "Empacotando o zip"

New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}
Compress-Archive -Path (Join-Path $distDir "*") -DestinationPath $zipPath -Force

$sizeMb = [math]::Round((Get-Item $zipPath).Length / 1MB, 1)
Write-Ok "Zip gerado ($sizeMb MB)."
Write-Info $zipPath

# --- 5. Release no GitHub -----------------------------------------------------------
Write-Step 5 $totalSteps "Publicando o release no GitHub"

$ghArgs = @("release", "create", $tag, $zipPath, "--title", "$Version-$Channel", "--generate-notes")
if (-not $Publish) {
    $ghArgs += "--draft"
}

& gh @ghArgs
if ($LASTEXITCODE -ne 0) {
    Write-Fail "gh release create falhou (a tag '$tag' ja existe?)."
    exit 1
}
Write-Ok "Release criado."

# --- Resumo --------------------------------------------------------------------------
Write-Host ""
Write-Host "  Release concluido" -ForegroundColor White
Write-Host "  ------------------" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Zip:" -ForegroundColor White
Write-Host "    $zipPath" -ForegroundColor Cyan
Write-Host ""
if ($Publish) {
    Write-Ok "Release publicado (tag $tag)."
}
else {
    Write-Warn "Release criado como DRAFT (tag $tag)."
    Write-Info "Publique manualmente no GitHub, ou rode de novo com -Publish."
}
Write-Host ""
