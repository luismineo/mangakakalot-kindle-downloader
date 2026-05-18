@echo off
setlocal enabledelayedexpansion
title Manga Downloader Setup

echo ========================================
echo   Mangakakalot Kindle Downloader Setup
echo ========================================
echo.

:: Check for Python
echo [1/3] Checking for Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b
)
for /f "delims=" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo Found !PYTHON_VERSION!
echo.

:: Check for 7-Zip (needed by KCC)
echo [2/3] Checking for 7-Zip (required for KCC)...
if not exist "C:\Program Files\7-Zip\7z.exe" (
    if not exist "C:\Program Files (x86)\7-Zip\7z.exe" (
        echo [WARNING] 7-Zip was not found in the default installation paths.
        echo Kindle Comic Converter ^(KCC^) requires 7-Zip to create MOBI files.
        echo Please ensure it is installed, or the final conversion may fail.
        echo Download: https://www.7-zip.org/
    ) else (
        echo Found 7-Zip ^(x86^).
    )
) else (
    echo Found 7-Zip.
)
echo.

:: Create Virtual Environment
echo [3/3] Setting up Virtual Environment...
if not exist .venv (
    echo Creating virtual environment (.venv)...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b
    )
) else (
    echo Virtual environment already exists.
)

:: Install dependencies
echo Installing/Updating dependencies from requirements.txt...
.venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install some dependencies.
    echo Please check the error messages above.
    pause
    exit /b
)

echo.
echo ========================================
echo   Setup Complete Successfully!
echo ========================================
echo You can now use run_pop.bat to start downloading.
echo.
set /p RUN_NOW="Do you want to run the downloader now? (Y/N): "
if /i "!RUN_NOW!"=="Y" (
    call run_pop.bat
)
