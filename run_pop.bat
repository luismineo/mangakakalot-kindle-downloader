@echo off
setlocal enabledelayedexpansion
title Manga Downloader

set VENV_PATH=.venv\Scripts\python.exe

if not exist "%VENV_PATH%" (
    echo [WARNING] Virtual environment not found at %VENV_PATH%
    echo It looks like the project hasn't been set up yet.
    set /p DO_SETUP="Would you like to run setup.bat now? (Y/N): "
    if /i "!DO_SETUP!"=="Y" (
        call setup.bat
        exit /b
    ) else (
        echo Please run setup.bat first.
        pause
        exit /b
    )
)

echo ========================================
echo   Mangakakalot Kindle Downloader
echo ========================================
echo.

:prompt_url
set "MANGA_URL="
set /p MANGA_URL="Enter Manga URL (e.g., https://www.mangakakalot.gg/manga/name-of-the-manga): "
if "%MANGA_URL%"=="" (
    echo [ERROR] URL cannot be empty.
    goto prompt_url
)

set "RANGE="
set /p RANGE="Enter Chapter Range (e.g., 1-10) [Press Enter for ALL chapters]: "

set "PROFILE="
set /p PROFILE="Enter KCC Profile (e.g., KPW6) [Press Enter for default: KPW6]: "
if "%PROFILE%"=="" set PROFILE=KPW6

echo.
echo ========================================
echo Starting download process...
echo URL: %MANGA_URL%
if "%RANGE%"=="" (
    echo Range: All chapters
) else (
    echo Range: %RANGE%
)
echo Profile: %PROFILE%
echo ========================================
echo.

if "%RANGE%"=="" (
    "%VENV_PATH%" src\main.py -u "%MANGA_URL%" -p %PROFILE%
) else (
    "%VENV_PATH%" src\main.py -u "%MANGA_URL%" -cr %RANGE% -p %PROFILE%
)

echo.
if not errorlevel 1 (
    echo ========================================
    echo   Download and Conversion Successful!
    echo ========================================
) else (
    echo ========================================
    echo   [ERROR] Process finished with errors.
    echo ========================================
)
pause
