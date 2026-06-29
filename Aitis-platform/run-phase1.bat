@echo off
REM ============================================================================
REM AITIS Phase 1 - Quick Start Batch File
REM ============================================================================
REM This script sets up and runs the entire Phase 1 system
REM Requires: Python 3.11+, Node.js 20+
REM ============================================================================

setlocal enabledelayedexpansion
cd /d "%~dp0"

:menu
cls
echo.
echo ============================================================================
echo   AITIS Platform - Phase 1 Quick Start
echo ============================================================================
echo.
echo Choose what to do:
echo   1) Run full setup (backend + frontend + migrations)
echo   2) Setup backend only
echo   3) Setup frontend only
echo   4) Start backend server
echo   5) Start frontend server
echo   6) Start BOTH servers in new windows
echo   7) Run integration tests
echo   0) Exit
echo.

set /p choice="Enter your choice (0-7): "

if "%choice%"=="1" goto full_setup
if "%choice%"=="2" goto backend_only
if "%choice%"=="3" goto frontend_only
if "%choice%"=="4" goto run_backend
if "%choice%"=="5" goto run_frontend
if "%choice%"=="6" goto run_both
if "%choice%"=="7" goto run_tests
if "%choice%"=="0" exit /b 0

echo Invalid choice. Please try again.
pause
goto menu

REM ============================================================================
REM FULL SETUP - Backend + Frontend + Migrations
REM ============================================================================
:full_setup
echo.
echo [STEP 1/4] Setting up backend...
cd /d "%~dp0backend"

echo   - Installing Python dependencies...
pip install -q -r requirements.txt
if errorlevel 1 (
    echo   ERROR: Failed to install backend dependencies
    pause
    goto menu
)

echo   - Installing Alembic...
pip install -q alembic

echo   - Running database migrations...
alembic upgrade head

cd /d "%~dp0"

echo.
echo [STEP 2/4] Setting up frontend...
cd /d "%~dp0frontend\apps\web"

echo   - Installing Node dependencies...
call npm install --silent
if errorlevel 1 (
    echo   ERROR: Failed to install frontend dependencies
    pause
    goto menu
)

cd /d "%~dp0"

echo.
echo [STEP 3/4] Starting backend server...
start "AITIS Backend Server" cmd /k "cd /d "%~dp0backend" && echo. && echo Backend API running at http://localhost:8000 && echo API Docs at http://localhost:8000/docs && echo. && uvicorn app.main:app --reload"
timeout /t 2 /nobreak

echo.
echo [STEP 4/4] Starting frontend server...
start "AITIS Frontend Server" cmd /k "cd /d "%~dp0frontend\apps\web" && echo. && echo Frontend running at http://localhost:3000 && echo. && npm run dev"

echo.
echo ============================================================================
echo   Setup Complete! Services are starting...
echo ============================================================================
echo.
echo Access points:
echo   - Frontend: http://localhost:3000
echo   - Backend API: http://localhost:8000
echo   - API Docs: http://localhost:8000/docs
echo.
echo Two new windows should open. Keep them open to run the services.
echo Press any key to return to menu...
pause
goto menu

REM ============================================================================
REM BACKEND ONLY SETUP
REM ============================================================================
:backend_only
echo.
echo Setting up backend...
cd /d "%~dp0backend"

echo Installing Python dependencies...
pip install -r requirements.txt

echo Installing Alembic...
pip install alembic

echo Running database migrations...
alembic upgrade head

cd /d "%~dp0"
echo.
echo Backend setup complete!
echo Press any key to return to menu...
pause
goto menu

REM ============================================================================
REM FRONTEND ONLY SETUP
REM ============================================================================
:frontend_only
echo.
echo Setting up frontend...
cd /d "%~dp0frontend\apps\web"

echo Installing Node dependencies...
call npm install

cd /d "%~dp0"
echo.
echo Frontend setup complete!
echo Press any key to return to menu...
pause
goto menu

REM ============================================================================
REM RUN BACKEND SERVER
REM ============================================================================
:run_backend
echo.
echo Starting Backend Server at http://localhost:8000
echo.
cd /d "%~dp0backend"
uvicorn app.main:app --reload
goto menu

REM ============================================================================
REM RUN FRONTEND SERVER
REM ============================================================================
:run_frontend
echo.
echo Starting Frontend Server at http://localhost:3000
echo.
cd /d "%~dp0frontend\apps\web"
call npm run dev
goto menu

REM ============================================================================
REM RUN BOTH SERVERS
REM ============================================================================
:run_both
echo.
echo Starting Backend Server...
start "AITIS Backend" cmd /k "cd /d "%~dp0backend" && echo Backend API: http://localhost:8000 && echo API Docs: http://localhost:8000/docs && echo. && uvicorn app.main:app --reload"
timeout /t 2 /nobreak

echo Starting Frontend Server...
start "AITIS Frontend" cmd /k "cd /d "%~dp0frontend\apps\web" && echo Frontend: http://localhost:3000 && echo. && npm run dev"

echo.
echo ============================================================================
echo   Both servers are starting in new windows!
echo ============================================================================
echo   - Frontend: http://localhost:3000
echo   - Backend: http://localhost:8000
echo   - API Docs: http://localhost:8000/docs
echo ============================================================================
echo.
echo Keep those windows open. Press any key to return to menu...
pause
goto menu

REM ============================================================================
REM RUN TESTS
REM ============================================================================
:run_tests
echo.
echo Choose tests to run:
echo   1) Backend integration tests
echo   2) Frontend E2E tests
echo   3) Both
echo.
set /p test_choice="Enter choice (1-3): "

if "%test_choice%"=="1" (
    echo.
    echo Running backend integration tests...
    echo.
    cd /d "%~dp0backend"
    pytest tests/test_phase1_integration.py -v
    pause
    cd /d "%~dp0"
)

if "%test_choice%"=="2" (
    echo.
    echo Running frontend E2E tests...
    echo.
    cd /d "%~dp0frontend\apps\web"
    call npx playwright test tests/e2e/phase1.spec.ts --headed
    pause
    cd /d "%~dp0"
)

if "%test_choice%"=="3" (
    echo.
    echo Running backend integration tests...
    echo.
    cd /d "%~dp0backend"
    pytest tests/test_phase1_integration.py -v
    
    echo.
    echo Running frontend E2E tests...
    echo.
    cd /d "%~dp0frontend\apps\web"
    call npx playwright test tests/e2e/phase1.spec.ts --headed
    pause
    cd /d "%~dp0"
)

goto menu

endlocal
