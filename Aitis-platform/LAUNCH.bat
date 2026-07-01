@echo off
setlocal
cd /d "%~dp0"

set BACKEND_PORT=8001
set FRONTEND_PORT=3000
set BACKEND_DIR=%~dp0backend
set FRONTEND_DIR=%~dp0frontend\apps\web

echo.
echo  AITIS Platform — Starting...
echo  Backend  : http://localhost:%BACKEND_PORT%
echo  Frontend : http://localhost:%FRONTEND_PORT%
echo.

:: Write .env.local so Next.js can find the backend
echo NEXT_PUBLIC_API_URL=http://127.0.0.1:%BACKEND_PORT%>"%FRONTEND_DIR%\.env.local"
echo [1/3] Frontend env set (NEXT_PUBLIC_API_URL=http://127.0.0.1:%BACKEND_PORT%)

:: Kill anything already on these ports
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /R ":%BACKEND_PORT% " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr /R ":%FRONTEND_PORT% " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)

:: Start backend — use %BACKEND_DIR% unquoted (path has no spaces)
echo [2/3] Starting backend on port %BACKEND_PORT%...
start "AITIS Backend [port %BACKEND_PORT%]" cmd /k "cd /d %BACKEND_DIR% && python -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT%"

:: Clear stale Next.js build cache (prevents ChunkLoadError on restart)
if exist "%FRONTEND_DIR%\.next" (
    rmdir /s /q "%FRONTEND_DIR%\.next" 2>nul
)

:: Start frontend
echo [3/3] Starting frontend on port %FRONTEND_PORT%...
start "AITIS Frontend [port %FRONTEND_PORT%]" cmd /k "cd /d %FRONTEND_DIR% && npm run dev"

:: Open browser after servers have had time to start
echo.
echo  Waiting 12 seconds for servers to initialise...
timeout /t 12 /nobreak >nul

start "" http://localhost:%FRONTEND_PORT%

echo.
echo  AITIS is running.
echo  Keep the two server windows open.
echo  Press any key to also open API docs...
pause >nul
start "" http://localhost:%BACKEND_PORT%/docs

endlocal
