# bot_zajeciowy.py
# Główny plik uruchamiający aplikację.

import transcriber
import telegram_handler

def main():
    """
    Główna funkcja: inicjalizuje komponenty i uruchamia bota.
    """
    # 1. Wczytaj model Whisper - to najdłuższa operacja, robimy ją raz na starcie.
    #    Dzięki temu model jest w pamięci i gotowy do natychmiastowego użycia.
    model_whisper = transcriber.load_model("base")

    # 2. Przekaż kontrolę do handlera Telegrama, który zawiera główną pętlę nasłuchującą.
    #    Przekazujemy mu załadowany model, aby mógł z niego korzystać.
    telegram_handler.uruchom_bota(model_whisper)

if __name__ == '__main__':
    # Uruchomienie głównej funkcji, gdy skrypt jest wywoływany bezpośrednio
    # przez komendę 'python bot_zajeciowy.py' w Twoim pliku start_bota.bat.
    main()

