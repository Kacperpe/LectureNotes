# bot_zajeciowy.py
# GÅ‚Ã³wny plik uruchamiajÄ…cy aplikacjÄ™.

import transcriber
import telegram_handler

def main():
    """
    GÅ‚Ã³wna funkcja: inicjalizuje komponenty i uruchamia bota.
    """
    # 1. Wczytaj model Whisper - to najdÅ‚uÅ¼sza operacja, robimy jÄ… raz na starcie.
    #    DziÄ™ki temu model jest w pamiÄ™ci i gotowy do natychmiastowego uÅ¼ycia.
    model_whisper = transcriber.load_model("base")

    # 2. PrzekaÅ¼ kontrolÄ™ do handlera Telegrama, ktÃ³ry zawiera gÅ‚Ã³wnÄ… pÄ™tlÄ™ nasÅ‚uchujÄ…cÄ….
    #    Przekazujemy mu zaÅ‚adowany model, aby mÃ³gÅ‚ z niego korzystaÄ‡.
    telegram_handler.uruchom_bota(model_whisper)

if __name__ == '__main__':
    # Uruchomienie gÅ‚Ã³wnej funkcji, gdy skrypt jest wywoÅ‚ywany bezpoÅ›rednio
    # przez komendÄ™ 'python bot_zajeciowy.py' w Twoim pliku scripts/windows/start_bota.bat.
    main()


