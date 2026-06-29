@echo off
REM Start Both Backend and Frontend Servers + Open Browser
REM Usage: Double-click this file or run from command line

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ============================================================================
echo   AITIS - Starting Both Servers
echo ============================================================================
echo.

:: Kill any existing processes on our ports
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING" 2^>nul') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo Starting Backend Server...
start "AITIS Backend" cmd /k "cd /d "%~dp0backend" && echo Backend API: http://localhost:8000 && echo API Docs: http://localhost:8000/docs && echo. && p:\AITIS\.venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload"

echo Starting Frontend Server...
start "AITIS Frontend" cmd /k "cd /d "%~dp0frontend\apps\web" && echo Frontend: http://localhost:3000 && echo. && npm run dev"

echo.
echo ============================================================================
echo   Waiting 6 seconds for servers to start...
echo ============================================================================
timeout /t 6 /nobreak

echo Opening browser...
start "" http://localhost:3000

echo.
echo ============================================================================
echo   Both servers are running!
echo ============================================================================
echo.
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo.
echo   Keep the server windows open. Close them to stop.
echo.
pause
endlocal
