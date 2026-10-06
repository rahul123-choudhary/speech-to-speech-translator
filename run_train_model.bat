@echo off
cd /d "%~dp0"
echo Starting train_yoruba_english.py... > artifacts\train_output.log
".\.venv\Scripts\python.exe" scripts\train_yoruba_english.py >> artifacts\train_output.log 2>&1
echo Done with code %ERRORLEVEL% >> artifacts\train_output.log
