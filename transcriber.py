# transcriber.py
# Moduł odpowiedzialny za obsługę modelu Whisper.

import whisper
import sys
import threading
import time
import os

def log_status(wiadomosc):
    """Wyświetla sformatowany komunikat o statusie modułu Transcriber."""
    print(f"[TRANSCRIBER STATUS] {wiadomosc}")

def load_model(model_name="base"):
    """Ładuje model Whisper do pamięci i zwraca go."""
    log_status(f"Ładowanie modelu Whisper '{model_name}' do pamięci...")
    try:
        model = whisper.load_model(model_name)
        log_status("✅ Model Whisper załadowany!")
        return model
    except Exception as e:
        log_status(f"❌ KRYTYCZNY BŁĄD: Nie udało się załadować modelu Whisper. Błąd: {e}")
        exit()

def transkrybuj_audio(sciezka_pliku: str, model) -> str:
    """Dokonuje transkrypcji pliku audio i usuwa go po zakończeniu."""
    if not os.path.exists(sciezka_pliku):
        log_status(f"Błąd: Plik do transkrypcji nie istnieje: {sciezka_pliku}")
        return None

    wynik = {}
    
    def praca_transkrypcji():
        try:
            log_status(f"Rozpoczynanie transkrypcji pliku: {os.path.basename(sciezka_pliku)}")
            result = model.transcribe(sciezka_pliku, language=None, fp16=False)
            wynik['transkrypcja'] = result["text"]
        except Exception as e:
            wynik['blad'] = e

    watek_transkrypcji = threading.Thread(target=praca_transkrypcji)
    watek_transkrypcji.start()
    
    # Animacja oczekiwania w konsoli
    while watek_transkrypcji.is_alive():
        for c in "⢿⣻⣽⣾⣷⣯⣟⡿":
            if not watek_transkrypcji.is_alive(): break
            sys.stdout.write(f'\r[TRANSCRIBER STATUS] Transkrypcja w toku... {c} ')
            sys.stdout.flush()
            time.sleep(0.1)
    
    sys.stdout.write('\r' + ' ' * 60 + '\r') # Wyczyszczenie linii animacji
    sys.stdout.flush()

    # Usunięcie pliku po transkrypcji
    try:
        os.remove(sciezka_pliku)
        log_status(f"Tymczasowy plik '{os.path.basename(sciezka_pliku)}' został usunięty.")
    except OSError as e:
        log_status(f"Błąd podczas usuwania pliku tymczasowego: {e}")

    if 'blad' in wynik:
        log_status(f"Błąd podczas transkrypcji: {wynik['blad']}")
        return None
    else:
        log_status("✅ Transkrypcja zakończona pomyślnie.")
        return wynik.get('transkrypcja')

