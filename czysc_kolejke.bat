@echo off
title Czyszczenie Kolejki Bota

echo Aktywowanie srodowiska wirtualnego...
call C:\Users\kacpe\whisper-gpu-env\Scripts\activate.bat

echo Przechodzenie do folderu bota...
cd C:\Users\kacpe\Nagrania_bot

echo.
echo Uruchamianie skryptu czyszczacego kolejke...
echo.

python czysc_kolejke.py