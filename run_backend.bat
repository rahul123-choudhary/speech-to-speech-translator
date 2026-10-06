@echo off
setlocal enabledelayedexpansion

title STS Backend Server (FastAPI)

:: Navigate to project root directory
cd /d "%~dp0"

:: Configuration
set PORT=8000
set HOST=127.0.0.1

echo ========================================================
echo        STS Backend Server Launcher
echo ========================================================
echo [1/3] Checking if port %PORT% is in use...

set FOUND=0
set LAST_KILLED=0

:: Check for any process listening on the port and terminate it
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
    :: Small pause to ensure socket is completely released by the OS
    ping 127.0.0.1 -n 2 >nul
)

echo.
echo [2/3] Detecting Python environment...
if exist ".\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=.\.venv\Scripts\python.exe"
    echo [OK] Using virtual environment Python: !PYTHON_EXE!
) else if exist "venv\Scripts\python.exe" (
    set "PYTHON_EXE=venv\Scripts\python.exe"
    echo [OK] Using virtual environment Python: !PYTHON_EXE!
) else (
    set "PYTHON_EXE=python"
    echo [WARN] .venv not found. Falling back to system Python.
)

echo.
echo [3/3] Starting FastAPI backend with Uvicorn on http://%HOST%:%PORT% ...
echo --------------------------------------------------------

"!PYTHON_EXE!" -m uvicorn s2st.api:app --host %HOST% --port %PORT% --reload %*

if %ERRORLEVEL% neq 0 (
    echo.
    echo ========================================================
    echo [ERROR] Backend stopped or crashed with exit code %ERRORLEVEL%.
    echo ========================================================
    pause
)
