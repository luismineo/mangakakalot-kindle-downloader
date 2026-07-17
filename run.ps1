#Requires -Version 5.1
<#
.SYNOPSIS
    Baixa um manga e converte para o formato do Kindle.

.DESCRIPTION
    Modo interativo por padrao: pergunta a URL, a faixa de capitulos e o perfil
    do dispositivo. Passando os parametros, roda direto, sem perguntar nada.

.PARAMETER Url
    URL da pagina principal do manga.

.PARAMETER Profile
    Perfil de dispositivo do KCC (padrao: KPW6, Kindle Paperwhite).

.PARAMETER Chapters
    Faixa de capitulos, ex.: "1-10" ou "15.5". Vazio = todos.

.PARAMETER Workers
    Downloads simultaneos (padrao: 6). Acima de 8 o site tende a responder 429.

.PARAMETER Verbose
    Liga o log DEBUG, com o tempo gasto em cada etapa de cada capitulo.

.EXAMPLE
    .\run.ps1
    Modo interativo.

.EXAMPLE
    .\run.ps1 -Url "https://www.mangakakalot.gg/manga/exemplo" -Chapters "1-10"
    Modo direto.

.NOTES
    Se a politica de execucao bloquear, rode:
        powershell -ExecutionPolicy Bypass -File run.ps1
#>

[CmdletBinding()]
param(
    [string]$Url,
    [string]$Profile = "KPW6",
    [string]$Chapters,
    [int]$Workers = 6
)

$ErrorActionPreference = "Stop"

function Write-Ok($Text)   { Write-Host "  [ok]   $Text" -ForegroundColor Green }
function Write-Warn($Text) { Write-Host "  [!]    $Text" -ForegroundColor Yellow }
function Write-Fail($Text) { Write-Host "  [x]    $Text" -ForegroundColor Red }
function Write-Info($Text) { Write-Host "         $Text" -ForegroundColor DarkGray }

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"

Write-Host ""
Write-Host "==================================================" -ForegroundColor Magenta
Write-Host "  Mangakakalot Kindle Downloader" -ForegroundColor Magenta
Write-Host "==================================================" -ForegroundColor Magenta
Write-Host ""

# --- Ambiente ----------------------------------------------------------------
if (-not (Test-Path $venvPython)) {
    Write-Warn "Ambiente virtual nao encontrado."
    Write-Info "O projeto ainda nao foi configurado."
    Write-Host ""
    $answer = Read-Host "  Rodar o setup.ps1 agora? (S/N)"
    if ($answer -match '^[SsYy]') {
        & (Join-Path $projectRoot "setup.ps1")
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
        Write-Host ""
    }
    else {
        Write-Fail "Rode o setup.ps1 antes de continuar."
        exit 1
    }
}

# --- URL ---------------------------------------------------------------------
while ([string]::IsNullOrWhiteSpace($Url)) {
    Write-Host "  URL do manga" -ForegroundColor White
    Write-Info "ex.: https://www.mangakakalot.gg/manga/nome-do-manga"
    $Url = (Read-Host "  >").Trim()

    if ([string]::IsNullOrWhiteSpace($Url)) {
        Write-Fail "A URL nao pode ser vazia."
    }
    elseif ($Url -notmatch '^https?://') {
        Write-Fail "A URL precisa comecar com http:// ou https://"
        $Url = ""
    }
    Write-Host ""
}

# --- Capitulos ---------------------------------------------------------------
if (-not $PSBoundParameters.ContainsKey('Chapters')) {
    Write-Host "  Faixa de capitulos" -ForegroundColor White
    Write-Info "ex.: 1-10 ou 15.5   |   Enter = todos os capitulos"
    $Chapters = (Read-Host "  >").Trim()
    Write-Host ""
}

# --- Perfil ------------------------------------------------------------------
if (-not $PSBoundParameters.ContainsKey('Profile')) {
    Write-Host "  Perfil do dispositivo" -ForegroundColor White
    Write-Info "KPW6 = Paperwhite  |  K11 = Kindle 11  |  KO = Oasis  |  KS = Scribe"
    Write-Info "Enter = KPW6"
    $answer = (Read-Host "  >").Trim()
    if (-not [string]::IsNullOrWhiteSpace($answer)) { $Profile = $answer }
    Write-Host ""
}

# --- Resumo ------------------------------------------------------------------
Write-Host "--------------------------------------------------" -ForegroundColor DarkGray
Write-Host "  URL:       $Url"
if ([string]::IsNullOrWhiteSpace($Chapters)) {
    Write-Host "  Capitulos: todos"
}
else {
    Write-Host "  Capitulos: $Chapters"
}
Write-Host "  Perfil:    $Profile"
Write-Host "  Workers:   $Workers"
Write-Host "--------------------------------------------------" -ForegroundColor DarkGray
Write-Host ""

# --- Execucao ----------------------------------------------------------------
$arguments = @("src\main.py", "-u", $Url, "-p", $Profile, "-w", $Workers)
if (-not [string]::IsNullOrWhiteSpace($Chapters)) {
    $arguments += @("-cr", $Chapters)
}
if ($VerbosePreference -eq "Continue") {
    $arguments += "-v"
}

$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
& $venvPython $arguments
$exitCode = $LASTEXITCODE
$stopwatch.Stop()

$elapsed = [math]::Round($stopwatch.Elapsed.TotalSeconds, 1)

Write-Host ""
switch ($exitCode) {
    0 {
        Write-Host "==================================================" -ForegroundColor Green
        Write-Ok "Concluido em ${elapsed}s."
        Write-Info "Arquivos em: downloads\"
        Write-Host "==================================================" -ForegroundColor Green
    }
    2 {
        Write-Fail "Faixa de capitulos invalida: '$Chapters'"
        Write-Info "Use algo como 1-10 ou 15.5"
    }
    130 {
        Write-Warn "Interrompido pelo usuario apos ${elapsed}s."
        Write-Info "O progresso foi salvo: rodar de novo continua de onde parou."
    }
    default {
        Write-Fail "Processo terminou com erro (codigo $exitCode) apos ${elapsed}s."
        Write-Info "Detalhes em: pipeline.log"
        Write-Info "Os capitulos ja concluidos foram salvos; rodar de novo retoma."
    }
}
Write-Host ""

exit $exitCode
