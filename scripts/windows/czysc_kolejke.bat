@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%..\.."

echo Activating virtual environment...
call C:\Users\kacpe\whisper-gpu-env\Scripts\activate.bat

echo Switching to repo root...
cd /D "%REPO_ROOT%"

echo.
echo Running queue cleanup script...
echo.

python scripts\windows\czysc_kolejke.py

endlocal
