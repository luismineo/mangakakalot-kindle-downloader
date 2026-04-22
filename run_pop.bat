@echo off
set VENV_PATH=E:\dev\manga-dl\.venv\Scripts\python.exe

if not exist "%VENV_PATH%" (
    echo [ERROR] Virtual environment not found at %VENV_PATH%
    echo Please check the path or create the venv.
    pause
    exit /b
)

set /p MANGA_URL="Enter Manga URL: "
set /p RANGE="Enter Chapter Range (ex: 1-10) or leave empty: "
set /p PROFILE="Enter KCC Profile (default KPW6): "

if "%PROFILE%"=="" set PROFILE=KPW6

if "%RANGE%"=="" (
    "%VENV_PATH%" src\main.py -u "%MANGA_URL%" -p %PROFILE%
) else (
    "%VENV_PATH%" src\main.py -u "%MANGA_URL%" -cr %RANGE% -p %PROFILE%
)

pause
