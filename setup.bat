@echo off
echo Starting Project Setup...

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b
)

:: Create Virtual Environment
echo Creating virtual environment (.venv)...
python -m venv .venv

:: Install dependencies
echo Installing dependencies from requirements.txt...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt

echo.
echo Setup Complete!
echo You can now use run_pop.bat to start downloading.
pause
