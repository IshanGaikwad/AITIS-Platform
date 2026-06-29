@echo off
setlocal enabledelayedexpansion

:: ============================================================================
::   AITIS Platform - One-Click Launcher
::   Double-click this file to start the entire application
:: ============================================================================

cd /d "%~dp0"

:: ── Configuration ────────────────────────────────────────────
set "BACKEND_DIR=%~dp0backend"
set "FRONTEND_DIR=%~dp0frontend\apps\web"
set "VENV_PYTHON=p:/AITIS/.venv/Scripts/python.exe"
set "VENV_PIP=p:/AITIS/.venv/Scripts/pip.exe"
set "VENV_UVICORN=p:/AITIS/.venv/Scripts/uvicorn.exe"
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=3000"
set "BROWSER_WAIT=8"

title AITIS Platform Launcher

echo.
echo ============================================================================
echo                         AITIS Platform Launcher
echo ============================================================================
echo.
echo   Backend:  http://localhost:%BACKEND_PORT%
echo   API Docs: http://localhost:%BACKEND_PORT%/docs
echo   Frontend: http://localhost:%FRONTEND_PORT%
echo.
echo ============================================================================
echo.

:: ── Step 1: Check Python ─────────────────────────────────────
echo [1/5] Checking Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo   [FAIL] Python not found! Please install Python 3.11+
    pause
    exit /b 1
)
for /f "tokens=2" %%v in ('python --version 2^>^&1') do echo   [OK] Python %%v

:: ── Step 2: Check Node.js ────────────────────────────────────
echo [2/5] Checking Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo   [FAIL] Node.js not found! Please install Node.js 18+
    pause
    exit /b 1
)
for /f "tokens=1" %%a in ('node --version') do echo   [OK] Node %%a

:: ── Step 3: Backend Setup ────────────────────────────────────
echo [3/5] Setting up backend...

if exist "%BACKEND_DIR%\.env" goto :env_ok
    echo   [WARN] No .env found, creating from .env.example...
    if not exist "%BACKEND_DIR%\.env.example" (
        echo   [FAIL] No .env.example found!
        pause
        exit /b 1
    )
    copy "%BACKEND_DIR%\.env.example" "%BACKEND_DIR%\.env" >nul
    echo   [OK] Created .env from .env.example
    goto :env_done
:env_ok
echo   [OK] .env file exists
:env_done

echo   Installing Python packages...
"%VENV_PIP%" install -q -r "%BACKEND_DIR%\requirements.txt"
if %errorlevel% neq 0 (
    echo   [WARN] Some packages may have failed, trying to continue...
) else (
    echo   [OK] Backend dependencies ready
)

:: ── Step 4: Frontend Setup ───────────────────────────────────
echo [4/5] Setting up frontend...

if exist "%FRONTEND_DIR%\node_modules" goto :npm_ok
    echo   Installing Node packages (this may take a minute)...
    cd /d "%FRONTEND_DIR%"
    call npm install --silent
    if %errorlevel% neq 0 (
        echo   [FAIL] npm install failed! Check your Node.js installation.
        cd /d "%~dp0"
        pause
        exit /b 1
    )
    cd /d "%~dp0"
    echo   [OK] Node packages installed
    goto :npm_done
:npm_ok
echo   [OK] Node packages already installed
:npm_done

:: ── Step 5: Start Servers ────────────────────────────────────
echo [5/5] Starting servers...

:: Kill any existing processes on our ports
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%BACKEND_PORT%" ^| findstr "LISTENING" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%FRONTEND_PORT%" ^| findstr "LISTENING" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: Start Backend in a new window
start "AITIS Backend (Port %BACKEND_PORT%)" cmd /k "cd /d "%BACKEND_DIR%" && echo Starting backend on port %BACKEND_PORT%... && echo. && "%VENV_UVICORN%" app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload"

:: Start Frontend in a new window
start "AITIS Frontend (Port %FRONTEND_PORT%)" cmd /k "cd /d "%FRONTEND_DIR%" && echo Starting frontend on port %FRONTEND_PORT%... && echo. && npm run dev"

echo.
echo ============================================================================
echo   Waiting %BROWSER_WAIT% seconds for servers to start...
echo ============================================================================
echo.

:: Wait for servers to be ready
timeout /t %BROWSER_WAIT% /nobreak

:: ── Open Browser ─────────────────────────────────────────────
echo.
echo ============================================================================
echo   Opening browser...
echo ============================================================================
echo.

:: Try to open the frontend in the default browser
start "" http://localhost:%FRONTEND_PORT%

echo.
echo ============================================================================
echo   AITIS Platform is now running!
echo ============================================================================
echo.
echo   Frontend:  http://localhost:%FRONTEND_PORT%
echo   Backend:   http://localhost:%BACKEND_PORT%
echo   API Docs:  http://localhost:%BACKEND_PORT%/docs
echo.
echo   Keep the server windows open. Close them to stop the app.
echo.
echo ============================================================================
echo.
echo Press any key to open API docs in browser...
pause >nul
start "" http://localhost:%BACKEND_PORT%/docs

endlocal