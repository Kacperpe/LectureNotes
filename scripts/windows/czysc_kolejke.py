import os
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import config


def wyczysc_kolejke():
    """Laczy sie z API Telegrama i usuwa wszystkie oczekujace wiadomosci."""
    print("--- CZYSZCZENIE KOLEJKI WIADOMOSCI NA SERWERZE TELEGRAMA ---")

    token_path = REPO_ROOT / config.TELEGRAM_TOKEN_FILE
    memory_path = REPO_ROOT / config.PLIK_PAMIECI_BOTA

    try:
        token = ""
        with token_path.open("r", encoding="utf-8") as f:
            for line in f:
                cleaned = line.strip()
                if cleaned and ":" in cleaned:
                    token = cleaned
                    break
        if not token:
            raise ValueError("Nie znaleziono tokenu.")
        print("Token bota wczytany.")
    except Exception as e:
        print(f"KRYTYCZNY BLAD: Nie udalo sie wczytac tokenu z pliku '{token_path}'. Blad: {e}")
        return

    try:
        print("Sprawdzanie oczekujacych wiadomosci...")
        url = f"https://api.telegram.org/bot{token}/getUpdates?timeout=1"
        response = requests.get(url, timeout=15).json()

        if response.get("ok") and response.get("result"):
            count = len(response["result"])
            print(f"Znaleziono {count} oczekujacych wiadomosci.")

            last_update_id = response["result"][-1]["update_id"]
            offset = last_update_id + 1
            requests.get(f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}", timeout=15)
            print("Kolejka na serwerze Telegrama zostala wyczyszczona.")
        else:
            print("Kolejka wiadomosci na serwerze jest juz pusta.")
    except Exception as e:
        print(f"Wystapil blad podczas komunikacji z API Telegrama: {e}")

    if memory_path.exists():
        try:
            os.remove(memory_path)
            print(f"Lokalny plik pamieci '{memory_path}' zostal usuniety.")
        except Exception as e:
            print(f"Blad podczas usuwania lokalnego pliku pamieci: {e}")


if __name__ == "__main__":
    wyczysc_kolejke()
    print("\nGotowe! Mozesz teraz bezpiecznie uruchomic bota.")
    print("To okno zamknie sie automatycznie za 10 sekund...")
    time.sleep(10)
