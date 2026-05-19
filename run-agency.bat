@echo off
REM Groq Multi-Agent Agency Platform — Windows launcher

echo.
echo ========================================
echo   Autonomous Multi-Agent AI Agency
echo   Groq + FastAPI + Docker Sandbox
echo ========================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    echo Install Python 3.11+ from https://www.python.org/
    pause
    exit /b 1
)

if not exist "venv-agency" (
    echo Creating virtual environment...
    python -m venv venv-agency
)

echo Activating virtual environment...
call venv-agency\Scripts\activate.bat

echo Installing agency dependencies...
pip install -r requirements-agency.txt --quiet

docker version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo WARNING: Docker is not in PATH. QA sandbox will run in simulation mode.
    echo Install Docker Desktop and enable Linux containers for full QA loops.
    echo.
)

echo.
echo Starting API server at http://localhost:8000
echo Open the dashboard: http://localhost:8000/
echo Press Ctrl+C to stop.
echo.

python -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
REM Use "python -m uvicorn" — bare "uvicorn" may not be on PATH (same as Render).

pause
