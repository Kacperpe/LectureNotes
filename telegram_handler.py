# telegram_handler.py
# Główny moduł logiki bota Telegram.

import os
import requests
import time
import json
import gdown
import base64
import subprocess
import threading
import config
import llm_handler
import transcriber

# --- Zmienne globalne modułu ---
prompts = {}
przedmioty = {}
ostatnie_zadanie = {}
TELEGRAM_TOKEN = None

# --- Funkcje pomocnicze ---

def log_status(wiadomosc):
    """Wyświetla sformatowany komunikat o statusie modułu Handler."""
    print(f"[HANDLER STATUS] {wiadomosc}")

def inicjalizuj_bota():
    """Wczytuje token, prompty i przedmioty na starcie."""
    global TELEGRAM_TOKEN, prompts, przedmioty
    
    try:
        with open(config.TELEGRAM_TOKEN_FILE, "r", encoding='utf-8') as f:
            TELEGRAM_TOKEN = f.read().strip()
        if not TELEGRAM_TOKEN or ":" not in TELEGRAM_TOKEN:
            raise ValueError("Nie znaleziono prawidłowego tokenu.")
        log_status("Token bota wczytany.")
    except (FileNotFoundError, ValueError) as e:
        log_status(f"KRYTYCZNY BŁĄD: Problem z plikiem '{config.TELEGRAM_TOKEN_FILE}'. Błąd: {e}")
        exit()
        
    log_status(f"Wczytywanie promptów z folderu '{config.FOLDER_PROMPTOW}'...")
    if os.path.isdir(config.FOLDER_PROMPTOW):
        for nazwa_pliku in os.listdir(config.FOLDER_PROMPTOW):
            if nazwa_pliku.startswith("prompt_") and nazwa_pliku.endswith(".txt"):
                sciezka = os.path.join(config.FOLDER_PROMPTOW, nazwa_pliku)
                with open(sciezka, 'r', encoding='utf-8') as f:
                    klucz = nazwa_pliku.replace("prompt_", "").replace(".txt", "")
                    prompts[klucz] = f.read()
    
    log_status(f"Wczytywanie przedmiotów z pliku '{config.PLIK_PRZEDMIOTOW}'...")
    try:
        with open(config.PLIK_PRZEDMIOTOW, 'r', encoding='utf-8') as f:
            przedmioty = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log_status(f"OSTRZEŻENIE: Nie wczytano pliku przedmiotów. Funkcja klasyfikacji będzie niedostępna. Błąd: {e}")

def wyslij_wiadomosc_tekstowa(tekst, chat_id, reply_markup=None):
    """Wysyła wiadomość tekstową do użytkownika."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': tekst, 'parse_mode': 'Markdown'}
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    try:
        requests.post(url, json=payload, timeout=10)
    except requests.exceptions.RequestException as e:
        log_status(f"Błąd wysyłania wiadomości: {e}")

# --- Funkcje pobierania i przetwarzania plików ---

def pobierz_plik_z_telegrama(file_id, nazwa_pliku):
    """Pobiera plik z serwerów Telegrama na dysk."""
    log_status(f"Pobieranie pliku '{nazwa_pliku}' z Telegrama...")
    try:
        url_info = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}"
        response = requests.get(url_info, timeout=10).json()
        if not response.get('ok'):
            log_status(f"Błąd przy pobieraniu informacji o pliku: {response.get('description')}")
            return None
        file_path = response['result']['file_path']
        url_pobierania = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        response_audio = requests.get(url_pobierania, timeout=60)
        
        if not os.path.exists(config.FOLDER_POBIERANIA):
            os.makedirs(config.FOLDER_POBIERANIA)
            
        sciezka_zapisu = os.path.join(config.FOLDER_POBIERANIA, nazwa_pliku)
        with open(sciezka_zapisu, 'wb') as f:
            f.write(response_audio.content)
        return sciezka_zapisu
    except requests.exceptions.RequestException as e:
        log_status(f"Błąd sieciowy podczas pobierania z Telegrama: {e}")
        return None

def pobierz_plik_z_gdrive(link_gdrive, chat_id):
    """Pobiera plik z Google Drive z dodanym logowaniem."""
    log_status("Wykryto link Google Drive. Rozpoczynanie pobierania...")
    try:
        if not os.path.exists(config.FOLDER_POBIERANIA):
            os.makedirs(config.FOLDER_POBIERANIA)
        nazwa_pliku = f"gdrive_{int(time.time())}.media"
        sciezka_zapisu = os.path.join(config.FOLDER_POBIERANIA, nazwa_pliku)
        
        log_status("Rozpoczynam pobieranie z gdown...")
        gdown.download(link_gdrive, sciezka_zapisu, quiet=False, fuzzy=True)
        log_status("Pobieranie z gdown zakończone.")
        
        if os.path.exists(sciezka_zapisu):
            file_size = os.path.getsize(sciezka_zapisu)
            log_status(f"Plik istnieje. Rozmiar: {file_size} bajtów.")
            if file_size > 1000:
                log_status("Pobieranie zakończone sukcesem. Zwracam ścieżkę.")
                return sciezka_zapisu, nazwa_pliku
            else:
                log_status("BŁĄD: Plik jest za mały. Prawdopodobnie błąd pobierania.")
                if os.path.exists(sciezka_zapisu): os.remove(sciezka_zapisu)
                wyslij_wiadomosc_tekstowa("❌ Błąd: Pobieranie pliku z Google Drive nie powiodło się (plik jest pusty). Sprawdź uprawnienia udostępniania.", chat_id)
                return None, None
        else:
            log_status("BŁĄD: Plik nie istnieje po pobraniu.")
            wyslij_wiadomosc_tekstowa("❌ Błąd: Pobieranie pliku z Google Drive nie powiodło się.", chat_id)
            return None, None
    except Exception as e:
        log_status(f"Krytyczny błąd w funkcji pobierania z GDrive: {e}")
        wyslij_wiadomosc_tekstowa("❌ Wystąpił błąd serwera podczas pobierania z Google Drive.", chat_id)
        return None, None

def rozpoznaj_i_przygotuj_audio(sciezka_pliku, chat_id):
    """Używa ffprobe do analizy pliku, wyodrębnia audio z wideo i zwraca ścieżkę do pliku audio."""
    log_status(f"Analizowanie pliku medialnego: {os.path.basename(sciezka_pliku)}")
    try:
        command = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', sciezka_pliku]
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        info = json.loads(result.stdout)
        
        ma_wideo = any(s.get('codec_type') == 'video' for s in info.get('streams', []))
        ma_audio = any(s.get('codec_type') == 'audio' for s in info.get('streams', []))

        if not ma_audio:
            wyslij_wiadomosc_tekstowa("❌ Błąd: Przesłany plik nie zawiera ścieżki dźwiękowej.", chat_id)
            if os.path.exists(sciezka_pliku): os.remove(sciezka_pliku)
            return None

        if ma_wideo:
            log_status("Wykryto strumień wideo, rozpoczynam ekstrakcję audio...")
            sciezka_audio = os.path.splitext(sciezka_pliku)[0] + ".mp3"
            ffmpeg_cmd = ['ffmpeg', '-i', sciezka_pliku, '-vn', '-q:a', '0', '-y', sciezka_audio]
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
            os.remove(sciezka_pliku)
            log_status(f"Ekstrakcja audio zakończona: {os.path.basename(sciezka_audio)}")
            return sciezka_audio
        else:
            log_status("Plik jest plikiem audio, nie wymaga ekstrakcji.")
            return sciezka_pliku
    except FileNotFoundError:
        log_status("KRYTYCZNY BŁĄD: `ffmpeg`/`ffprobe` nie jest zainstalowany lub nie ma go w ścieżce systemowej (PATH).")
        wyslij_wiadomosc_tekstowa("❌ Błąd serwera: Brak narzędzi do przetwarzania wideo.", chat_id)
        if os.path.exists(sciezka_pliku): os.remove(sciezka_pliku)
        return None
    except Exception as e:
        log_status(f"Błąd podczas analizy pliku ({e}). Zakładam, że to plik audio.")
        return sciezka_pliku

def wyslij_plik_z_notatkami(transkrypcja, notatki, chat_id, temat_notatki):
    """Tworzy i wysyła plik .md z notatkami, zapisując go w odpowiednim folderze."""
    log_status("Przygotowywanie pliku Markdown z notatkami...")
    try:
        klucz_przedmiotu = llm_handler.sklasyfikuj_notatke(notatki, przedmioty) if przedmioty else None
        
        folder_docelowy = config.FOLDER_POBIERANIA
        if klucz_przedmiotu:
            folder_docelowy = os.path.join(config.FOLDER_POBIERANIA, klucz_przedmiotu)
            if not os.path.exists(folder_docelowy):
                os.makedirs(folder_docelowy)
        
        nazwa_bazowa = temat_notatki.lower().replace(" ", "_")
        for znak in r'<>:"/\|?*.':
            nazwa_bazowa = nazwa_bazowa.replace(znak, '')
        # ZMIANA: Zmiana rozszerzenia pliku na .md
        nazwa_pliku_md = f"{nazwa_bazowa}.md"
        
        sciezka_pliku_md = os.path.join(folder_docelowy, nazwa_pliku_md)
        
        # ZMIANA: Zmiana zawartości na formatowanie Markdown
        zawartosc_pliku = f"# Transkrypcja\n\n{transkrypcja}\n\n---\n\n# Notatki\n\n{notatki}"
        with open(sciezka_pliku_md, 'w', encoding='utf-8') as f:
            f.write(zawartosc_pliku)

        log_status(f"Wysyłanie pliku '{nazwa_pliku_md}'...")
        with open(sciezka_pliku_md, 'rb') as f:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument",
                files={'document': f},
                data={'chat_id': chat_id}
            )
    except Exception as e:
        log_status(f"BŁĄD podczas tworzenia/wysyłania pliku: {e}")

def wyslij_wybor_promptu(chat_id):
    """Wysyła przyciski wyboru promptu."""
    przyciski = [[{"text": k.replace('_', ' ').capitalize(), "callback_data": f"prompt_{k}"}] for k in sorted(prompts.keys())]
    przyciski.append([{"text": "✍️ Własny prompt", "callback_data": "prompt_custom"}])
    przyciski.append([{"text": "❌ Anuluj", "callback_data": "prompt_cancel"}])
    wyslij_wiadomosc_tekstowa(
        "✅ Plik gotowy do przetworzenia.\n\nWybierz styl notatek:",
        chat_id,
        reply_markup={"inline_keyboard": przyciski}
    )

# --- Główny proces przetwarzania ---

def rozpocznij_przetwarzanie(chat_id, model_whisper, prompt_uzytkownika):
    global ostatnie_zadanie
    
    sciezka_pliku_audio = ostatnie_zadanie.get('sciezka_pliku_audio')
    
    if not sciezka_pliku_audio or not os.path.exists(sciezka_pliku_audio):
        wyslij_wiadomosc_tekstowa("❌ Błąd: Plik audio do przetworzenia zniknął. Spróbuj wysłać go ponownie.", chat_id)
        ostatnie_zadanie = {}
        return

    wyslij_wiadomosc_tekstowa("Krok 1/3: Rozpoczynam transkrypcję audio... 🎤", chat_id)
    transkrypcja = transcriber.transkrybuj_audio(sciezka_pliku_audio, model_whisper)
    if not transkrypcja:
        wyslij_wiadomosc_tekstowa("❌ Błąd transkrypcji. Zatrzymano przetwarzanie.", chat_id)
        ostatnie_zadanie = {}
        return
    
    wyslij_wiadomosc_tekstowa("Krok 2/3: Przetwarzanie i synteza notatek przez AI... 🧠", chat_id)
    fragmenty = llm_handler.podziel_tekst_na_fragmenty(transkrypcja)
    polaczone_notatki, success_map = llm_handler.przetworz_fragmenty_wstepnie(fragmenty, prompt_uzytkownika)
    
    if not success_map:
        # ZMIANA: Implementacja Twojej prośby o fallback (awaria Fazy "Map")
        wyslij_wiadomosc_tekstowa("❌ Wystąpił błąd krytyczny na etapie analizy AI (Map). Otrzymasz plik z samą transkrypcją.", chat_id)
        temat_awaryjny = llm_handler.wygeneruj_temat_notatki(transkrypcja) # Wygeneruj temat z transkrypcji
        notatki_awaryjne = "## BŁĄD AI\n\nPrzetwarzanie notatek przez model AI nie powiodło się. Poniżej znajduje się tylko surowa transkrypcja."
        wyslij_plik_z_notatkami(transkrypcja, notatki_awaryjne, chat_id, temat_awaryjny)
        ostatnie_zadanie = {}
        return
        
    notatki_finalne, success_reduce = llm_handler.dokonaj_finalnej_syntezy(polaczone_notatki)
    
    wyslij_wiadomosc_tekstowa("Krok 3/3: Finalizowanie i wysyłanie pliku... 📂", chat_id)
    if success_reduce:
        # Scenariusz pomyślny
        temat_notatki = llm_handler.wygeneruj_temat_notatki(notatki_finalne)
        wyslij_plik_z_notatkami(transkrypcja, notatki_finalne, chat_id, temat_notatki)
    else:
        # ZMIANA: Implementacja Twojej prośby o fallback (awaria Fazy "Reduce")
        wyslij_wiadomosc_tekstowa("⚠️ OSTRZEŻENIE: Finalna synteza notatek nie powiodła się. Otrzymasz plik z samą transkrypcją.", chat_id)
        temat_awaryjny = llm_handler.wygeneruj_temat_notatki(transkrypcja) # Wygeneruj temat z transkrypcji
        notatki_awaryjne = "## BŁĄD AI\n\nPrzetwarzanie notatek przez model AI powiodło się częściowo (Map), ale finalna synteza (Reduce) nie powiodła się. Poniżej znajduje się tylko surowa transkrypcja."
        wyslij_plik_z_notatkami(transkrypcja, notatki_awaryjne, chat_id, temat_awaryjny)

    ostatnie_zadanie = {}

# --- Główna pętla bota ---

def uruchom_bota(model_whisper):
    global ostatnie_zadanie
    inicjalizuj_bota()
    offset = 0
    
    try:
        with open(config.PLIK_PAMIECI_BOTA, "r") as f: offset = int(f.read().strip()) + 1
    except (FileNotFoundError, ValueError): pass

    log_status("Bot gotowy do pracy. Nasłuchiwanie...")
    
    while True:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={offset}&timeout=100"
        try:
            response = requests.get(url, timeout=110).json()
            updates = response.get("result", [])
            
            if updates: log_status(f"Otrzymano {len(updates)} nowych aktualizacji.")
            
            for update in updates:
                offset = update.get("update_id") + 1
                
                if 'callback_query' in update:
                    query = update['callback_query']
                    chat_id = query['message']['chat']['id']
                    data = query['data']
                    if not ostatnie_zadanie or ostatnie_zadanie.get('chat_id') != chat_id: continue

                    if data == 'prompt_custom':
                        ostatnie_zadanie['status'] = 'oczekiwanie_na_wlasny_prompt'
                        wyslij_wiadomosc_tekstowa("Proszę, napisz teraz swój własny prompt:", chat_id)
                    elif data == 'prompt_cancel':
                        ostatnie_zadanie = {}
                        wyslij_wiadomosc_tekstowa("Anulowano.", chat_id)
                    elif data.startswith('prompt_') and (klucz := data.replace('prompt_', '')) in prompts:
                        ostatnie_zadanie['status'] = 'processing'
                        threading.Thread(target=rozpocznij_przetwarzanie, args=(chat_id, model_whisper, prompts[klucz])).start()
                
                elif 'message' in update:
                    message = update.get("message", {})
                    chat_id = message.get("chat", {}).get("id")
                    
                    if ostatnie_zadanie.get('status') == 'oczekiwanie_na_wlasny_prompt' and ostatnie_zadanie.get('chat_id') == chat_id:
                        ostatnie_zadanie['status'] = 'processing'
                        threading.Thread(target=rozpocznij_przetwarzanie, args=(chat_id, model_whisper, message.get('text', ''))).start()
                        continue

                    pobrana_sciezka, oryginalna_nazwa = None, None
                    
                    plik_telegrama = message.get("audio") or message.get("voice") or message.get("document") or message.get("video")
                    if plik_telegrama:
                         if (file_size := plik_telegrama.get("file_size", 0)) > config.MAX_FILE_SIZE_TELEGRAM:
                            wyslij_wiadomosc_tekstowa(f"❌ Plik jest za duży. Użyj linku z chmury.", chat_id)
                         else:
                            pobrana_sciezka = pobierz_plik_z_telegrama(plik_telegrama['file_id'], plik_telegrama.get("file_name", "plik_telegrama.media"))
                    
                    wiadomosc_tekstowa = message.get("text", "")
                    if "http" in wiadomosc_tekstowa and not pobrana_sciezka:
                        log_status(f"Wykryto link w wiadomości od {chat_id}. Próba pobrania...")
                        if "drive.google.com" in wiadomosc_tekstowa:
                            pobrana_sciezka, oryginalna_nazwa = pobierz_plik_z_gdrive(wiadomosc_tekstowa, chat_id)
                    
                    if pobrana_sciezka:
                        sciezka_audio = rozpoznaj_i_przygotuj_audio(pobrana_sciezka, chat_id)
                        if sciezka_audio:
                            if ostatnie_zadanie.get('status') == 'processing':
                                wyslij_wiadomosc_tekstowa("⚠️ Poczekaj, aż poprzednie zadanie zostanie ukończone.", chat_id)
                            else:
                                ostatnie_zadanie = {'status': 'oczekiwanie_na_wybor_promptu', 'sciezka_pliku_audio': sciezka_audio, 'chat_id': chat_id}
                                wyslij_wybor_promptu(chat_id)

        except requests.exceptions.RequestException as e:
            log_status(f"Błąd połączenia z serwerem Telegrama: {e}. Próba za 5 sekund...")
            time.sleep(5)
        except Exception as e:
            log_status(f"Nieoczekiwany błąd w głównej pętli: {e}")
            time.sleep(5)
        finally:
            with open(config.PLIK_PAMIECI_BOTA, "w") as f:
                f.write(str(offset-1))


