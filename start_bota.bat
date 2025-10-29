@echo off
title Uruchamianie Systemu Bota

:: --- KROK 1: Upewnij się, że żaden inny model nie jest załadowany ---
echo Zwalnianie pamieci z poprzednich modeli...
lms unload --all

:: --- KROK 2: Załadowanie konkretnego modelu do LM Studio ---
echo Ladowanie modelu 'openai/gpt-oss-20b' do pamieci...
:: Ta komenda zaczeka, aż model zostanie w pełni załadowany
lms load "openai/gpt-oss-20b"

:: --- KROK 3: Uruchomienie serwera LM Studio w tle ---
echo Uruchamianie serwera LM Studio w nowym oknie...
start "LM Studio Server" lms server start --port 1234

:: --- KROK 4: Poczekaj, aż serwer się uruchomi ---
echo.
echo Czekanie 5 sekund, az serwer sie w pelni uruchomi...
timeout /t 5

:: --- KROK 5: Uruchomienie bota na Telegramie ---
echo.
echo Aktywowanie srodowiska wirtualnego Whisper...
call "C:\Users\kacpe\whisper-gpu-env\Scripts\activate.bat"

echo Przechodzenie do folderu z botem...
cd /D "C:\Users\kacpe\Nagrania_bot"

echo.
echo Uruchamianie bota (bot_zajeciowy.py)...
python bot_zajeciowy.py

:: --- Zakończenie ---
echo.
echo Glowny skrypt zakonczyl dzialanie. Nacisnij dowolny klawisz, aby zamknac to okno.
pause
