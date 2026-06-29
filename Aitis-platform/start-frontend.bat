@echo off
setlocal

:: ============================================================================
::   AITIS Platform - Start Frontend Server
::   Double-click this file to start the frontend dev server
:: ============================================================================

cd /d "%~dp0frontend\apps\web"

echo.
echo ============================================================================
echo   AITIS Frontend Server
echo ============================================================================
echo.
echo   URL:  http://localhost:3000
echo.
echo   Press Ctrl+C to stop the server
echo ============================================================================
echo.

:: Check if node_modules exists
if not exist "node_modules" (
    echo [SETUP] Installing dependencies (first run)...
    call npm install
    echo.
)

call npm run dev
pause
endlocal
