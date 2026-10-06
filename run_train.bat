@echo off
cd /d "%~dp0"
echo Starting run_train.bat...
".\.venv\Scripts\python.exe" -u scripts\run_train.py
echo run_train.bat finished with code %ERRORLEVEL%
