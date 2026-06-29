@echo off
setlocal enabledelayedexpansion

:: ============================================================================
::   AITIS Platform - Setup (Install Dependencies & Run Migrations)
::   Double-click this file to set up the project for the first time
:: ============================================================================

cd /d "%~dp0"

:: Use venv if available
set "VENV_PYTHON=p:\AITIS\.venv\Scripts\python.exe"
set "VENV_PIP=p:\AITIS\.venv\Scripts\pip.exe"
set "VENV_ALEMBIC=p:\AITIS\.venv\Scripts\alembic.exe"

echo.
echo ============================================================================
echo   AITIS Platform - Setup
echo ============================================================================
echo.

echo [1/4] Setting up backend...
echo        - Installing Python dependencies...
cd /d "%~dp0backend"

if exist "%VENV_PIP%" (
    "%VENV_PIP%" install -q -r requirements.txt
) else (
    pip install -q -r requirements.txt
)
if errorlevel 1 (
    echo ERROR: Failed to install backend dependencies
    pause
    exit /b 1
)

echo        - Running database migrations...
if exist "%VENV_ALEMBIC%" (
    "%VENV_ALEMBIC%" upgrade head
) else (
    alembic upgrade head
)

cd /d "%~dp0"

echo.
echo [2/4] Setting up frontend...
echo        - Installing Node dependencies...
cd /d "%~dp0frontend\apps\web"
call npm install --silent
if errorlevel 1 (
    echo ERROR: Failed to install frontend dependencies
    pause
    exit /b 1
)

cd /d "%~dp0"

echo.
echo ============================================================================
echo   Setup Complete!
echo ============================================================================
echo.
echo Next steps:
echo   1. Run start-both.bat to start both servers
echo   2. OR run start-backend.bat for backend only
echo   3. OR run start-frontend.bat for frontend only
echo.
echo Access points:
echo   - Frontend: http://localhost:3000
echo   - Backend API: http://localhost:8000
echo   - API Docs: http://localhost:8000/docs
echo.
pause
endlocal
