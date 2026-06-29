@echo off
REM Run Phase 1 Tests
REM Usage: Double-click this file or run from command line

setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo ============================================================================
echo   AITIS Phase 1 - Run Tests
echo ============================================================================
echo.
echo Choose which tests to run:
echo   1) Backend Integration Tests
echo   2) Frontend E2E Tests (Playwright)
echo   3) Both
echo   0) Cancel
echo.
set /p choice="Enter your choice (0-3): "

if "%choice%"=="0" exit /b 0

if "%choice%"=="1" (
    echo.
    echo Running backend integration tests...
    echo.
    cd /d "%~dp0backend"
    pytest tests/test_phase1_integration.py -v
    pause
)

if "%choice%"=="2" (
    echo.
    echo Running frontend E2E tests...
    echo.
    cd /d "%~dp0frontend\apps\web"
    call npx playwright test tests/e2e/phase1.spec.ts --headed
    pause
)

if "%choice%"=="3" (
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
)

endlocal
