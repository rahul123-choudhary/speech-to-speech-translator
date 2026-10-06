@echo off
setlocal enabledelayedexpansion

title STS Frontend Server (Vite)

:: Navigate to project root directory
cd /d "%~dp0"

:: Configuration
set PORT=5173

echo ========================================================
echo        STS Frontend (Vite) Launcher
echo ========================================================

:: 1. Detect Frontend Directory
set "TARGET_DIR=%~dp0"

if exist "%~dp0frontend\package.json" (
    set "TARGET_DIR=%~dp0frontend"
) else if exist "%~dp0client\package.json" (
    set "TARGET_DIR=%~dp0client"
) else if exist "%~dp0web\package.json" (
    set "TARGET_DIR=%~dp0web"
) else if exist "%~dp0package.json" (
    set "TARGET_DIR=%~dp0"
) else if exist "%~dp0frontend" (
    set "TARGET_DIR=%~dp0frontend"
)

cd /d "!TARGET_DIR!"
echo [1/3] Frontend Directory: !TARGET_DIR!

:: 2. Check if port is in use and free it
echo [2/3] Checking if port %PORT% is in use...
set FOUND=0
set LAST_KILLED=0

for /f "tokens=5" %%a in ('netstat -ano ^| findstr /r /c:":%PORT% "') do (
    if not "%%a"=="" if not "%%a"=="0" if not "%%a"=="!LAST_KILLED!" (
        set FOUND=1
        set LAST_KILLED=%%a
        echo [INFO] Port %PORT% is in use by PID %%a. Terminating process...
        taskkill /f /pid %%a >nul 2>&1
    )
)

if "!FOUND!"=="0" (
    echo [OK] Port %PORT% is free.
) else (
    echo [OK] Port %PORT% successfully cleared.
    ping 127.0.0.1 -n 2 >nul
)

:: 3. Prepare and run Vite
echo.
echo [3/3] Preparing and starting Vite server...

if not exist "package.json" (
    echo [INFO] Web UI is built-in and served directly by FastAPI backend.
    echo [INFO] Launching browser to http://127.0.0.1:8000 ...
    start http://127.0.0.1:8000
    echo [INFO] Ensure backend is running via run_backend.bat!
    pause
    goto end
)

if not exist "node_modules" (
    echo [INFO] node_modules folder missing. Running npm install...
    call npm install
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] npm install encountered an error.
        pause
        exit /b %ERRORLEVEL%
    )
)

echo [OK] Launching Vite development server...
echo --------------------------------------------------------
call npm run dev

:end
if %ERRORLEVEL% neq 0 (
    echo.
    echo ========================================================
    echo [ERROR] Frontend stopped or crashed with exit code %ERRORLEVEL%.
    echo ========================================================
    pause
)
