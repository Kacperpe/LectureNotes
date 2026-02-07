@echo off
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT=%SCRIPT_DIR%..\.."

title Uruchamianie Systemu Bota

echo Zwalnianie pamieci z poprzednich modeli...
lms unload --all

echo Ladowanie modelu 'openai/gpt-oss-20b' do pamieci...
lms load "openai/gpt-oss-20b"

echo Uruchamianie serwera LM Studio w nowym oknie...
start "LM Studio Server" lms server start --port 1234

echo.
echo Czekanie 5 sekund, az serwer sie w pelni uruchomi...
timeout /t 5

echo.
echo Aktywowanie srodowiska wirtualnego Whisper...
call "C:\Users\kacpe\whisper-gpu-env\Scripts\activate.bat"

echo Przechodzenie do folderu projektu...
cd /D "%REPO_ROOT%"

echo.
echo Uruchamianie bota (bot_zajeciowy.py)...
python bot_zajeciowy.py

echo.
echo Glowny skrypt zakonczyl dzialanie. Nacisnij dowolny klawisz, aby zamknac to okno.
pause

endlocal
