@echo off
setlocal

:: ============================================================================
::   AITIS Platform - Start Backend Server
::   Double-click this file to start the backend API server
:: ============================================================================

cd /d "%~dp0backend"

:: Use venv Python if available
set "VENV_UVICORN=p:\AITIS\.venv\Scripts\uvicorn.exe"

echo.
echo ============================================================================
echo   AITIS Backend Server
echo ============================================================================
echo.
echo   API:      http://localhost:8000
echo   Docs:     http://localhost:8000/docs
echo   Health:   http://localhost:8000/health
echo.
echo   Press Ctrl+C to stop the server
echo ============================================================================
echo.

if exist "%VENV_UVICORN%" (
    "%VENV_UVICORN%" app.main:app --host 0.0.0.0 --port 8000 --reload
) else (
    echo [WARN] venv uvicorn not found, trying system uvicorn...
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
)

pause
endlocal
