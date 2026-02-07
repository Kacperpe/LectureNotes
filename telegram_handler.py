# telegram_handler.py
# GÅ‚Ã³wny moduÅ‚ logiki bota Telegram.

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
try:
    from notion_sync import create_notion_note, has_valid_token
except Exception:
    create_notion_note = None
    has_valid_token = lambda: False

# --- Zmienne globalne moduÅ‚u ---
prompts = {}
przedmioty = {}
ostatnie_zadanie = {}
TELEGRAM_TOKEN = None
chat_settings = {}
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# --- Lista komend pomocy ---
COMMANDS = {
    "start": "KrÃ³tka informacja o bocie / instrukcja uÅ¼ycia.",
    "help": "WyÅ›wietla listÄ™ dostÄ™pnych komend i krÃ³tkie opisy.",
    "jezyk": "Ustawia jÄ™zyk transkrypcji (np. pl, en, auto).",
    "rozszerzenie": "Ustawia rozszerzenie pliku wyjÅ›ciowego (.txt, .md, .srt).",
}

# --- Ustawienia per-chat (persistence) ---
def load_chat_settings():
    """Wczytuje ustawienia chatÃ³w z pliku JSON do pamiÄ™ci."""
    global chat_settings
    try:
        if os.path.exists(_resolve_path(config.CHAT_SETTINGS_FILE)):
            with open(_resolve_path(config.CHAT_SETTINGS_FILE), 'r', encoding='utf-8') as f:
                chat_settings = json.load(f)
        else:
            chat_settings = {}
    except Exception as e:
        log_status(f"BÅ‚Ä…d wczytywania ustawieÅ„ chatÃ³w: {e}")
        chat_settings = {}

def save_chat_settings():
    """Zapisuje aktualne ustawienia chatÃ³w do pliku JSON."""
    try:
        with open(_resolve_path(config.CHAT_SETTINGS_FILE), 'w', encoding='utf-8') as f:
            json.dump(chat_settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log_status(f"BÅ‚Ä…d zapisu ustawieÅ„ chatÃ³w: {e}")

def get_chat_setting(chat_id, key, default=None):
    return chat_settings.get(str(chat_id), {}).get(key, default)

def set_chat_setting(chat_id, key, value):
    sid = str(chat_id)
    if sid not in chat_settings:
        chat_settings[sid] = {}
    chat_settings[sid][key] = value
    save_chat_settings()

# --- Funkcje pomocnicze ---

def log_status(wiadomosc):
    """Wyswietla sformatowany komunikat o statusie modulu Handler."""
    print(f"[HANDLER STATUS] {wiadomosc}")


def _resolve_path(path: str) -> str:
    """Zwraca sciezke absolutna; wzgledne sciezki liczy od katalogu projektu."""
    if os.path.isabs(path):
        return path
    return os.path.join(PROJECT_ROOT, path)


def _read_token_from_file(path: str) -> str | None:
    """Czyta token z pliku; zwraca None, jesli plik nie istnieje lub token jest nieprawidlowy."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            token = f.read().strip()
        if token and ":" in token:
            return token
    except Exception:
        return None
    return None


def inicjalizuj_bota():
    """Wczytuje token, prompty i przedmioty na starcie."""
    global TELEGRAM_TOKEN, prompts, przedmioty

    # 1) Preferowana metoda: zmienna srodowiskowa
    env_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if env_token and ":" in env_token:
        TELEGRAM_TOKEN = env_token
        log_status("Token bota wczytany ze zmiennej TELEGRAM_BOT_TOKEN.")
    else:
        # 2) Fallback: pliki lokalne (nowa i stara lokalizacja)
        candidate_paths = [
            _resolve_path(config.TELEGRAM_TOKEN_FILE),
            _resolve_path("TokenBota.txt"),
            _resolve_path("secrets/API token dla Zajecia_bot.txt"),
            _resolve_path("API token dla Zajecia_bot.txt"),
        ]
        for candidate in candidate_paths:
            token = _read_token_from_file(candidate)
            if token:
                TELEGRAM_TOKEN = token
                log_status(f"Token bota wczytany z pliku: {candidate}")
                break

    if not TELEGRAM_TOKEN:
        candidate_paths = [
            _resolve_path(config.TELEGRAM_TOKEN_FILE),
            _resolve_path("TokenBota.txt"),
            _resolve_path("secrets/API token dla Zajecia_bot.txt"),
            _resolve_path("API token dla Zajecia_bot.txt"),
        ]
        log_status("KRYTYCZNY BLAD: Nie znaleziono tokenu Telegram bota.")
        log_status("Utworz plik z tokenem w jednej z lokalizacji:")
        for candidate in candidate_paths:
            log_status(f" - {candidate}")
        log_status("Albo ustaw zmienna srodowiskowa TELEGRAM_BOT_TOKEN.")
        exit()

    log_status(f"Wczytywanie promptow z folderu '{config.FOLDER_PROMPTOW}'...")
    prompts_dir = _resolve_path(config.FOLDER_PROMPTOW)
    if os.path.isdir(prompts_dir):
        for nazwa_pliku in os.listdir(prompts_dir):
            if nazwa_pliku.startswith("prompt_") and nazwa_pliku.endswith(".txt"):
                sciezka = os.path.join(prompts_dir, nazwa_pliku)
                with open(sciezka, 'r', encoding='utf-8') as f:
                    klucz = nazwa_pliku.replace("prompt_", "").replace(".txt", "")
                    prompts[klucz] = f.read()

    log_status(f"Wczytywanie przedmiotow z pliku '{config.PLIK_PRZEDMIOTOW}'...")
    try:
        with open(_resolve_path(config.PLIK_PRZEDMIOTOW), 'r', encoding='utf-8') as f:
            przedmioty = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log_status(f"OSTRZEZENIE: Nie wczytano pliku przedmiotow. Funkcja klasyfikacji bedzie niedostepna. Blad: {e}")

    # Wczytaj ustawienia per-chat (jezyk, rozszerzenie)
    try:
        load_chat_settings()
    except Exception:
        log_status("Brak lub blad pliku ustawien chatow. Utworze nowe podczas zapisu.")

def wyslij_wiadomosc_tekstowa(tekst, chat_id, reply_markup=None):
    """WysyÅ‚a wiadomoÅ›Ä‡ tekstowÄ… do uÅ¼ytkownika."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': chat_id, 'text': tekst, 'parse_mode': 'Markdown'}
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    try:
        requests.post(url, json=payload, timeout=10)
    except requests.exceptions.RequestException as e:
        log_status(f"BÅ‚Ä…d wysyÅ‚ania wiadomoÅ›ci: {e}")

# --- Funkcje pobierania i przetwarzania plikÃ³w ---

def pobierz_plik_z_telegrama(file_id, nazwa_pliku):
    """Pobiera plik z serwerÃ³w Telegrama na dysk."""
    log_status(f"Pobieranie pliku '{nazwa_pliku}' z Telegrama...")
    try:
        url_info = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}"
        response = requests.get(url_info, timeout=10).json()
        if not response.get('ok'):
            log_status(f"BÅ‚Ä…d przy pobieraniu informacji o pliku: {response.get('description')}")
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
        log_status(f"BÅ‚Ä…d sieciowy podczas pobierania z Telegrama: {e}")
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
        log_status("Pobieranie z gdown zakoÅ„czone.")
        
        if os.path.exists(sciezka_zapisu):
            file_size = os.path.getsize(sciezka_zapisu)
            log_status(f"Plik istnieje. Rozmiar: {file_size} bajtÃ³w.")
            if file_size > 1000:
                log_status("Pobieranie zakoÅ„czone sukcesem. Zwracam Å›cieÅ¼kÄ™.")
                return sciezka_zapisu, nazwa_pliku
            else:
                log_status("BÅÄ„D: Plik jest za maÅ‚y. Prawdopodobnie bÅ‚Ä…d pobierania.")
                if os.path.exists(sciezka_zapisu): os.remove(sciezka_zapisu)
                wyslij_wiadomosc_tekstowa("âŒ BÅ‚Ä…d: Pobieranie pliku z Google Drive nie powiodÅ‚o siÄ™ (plik jest pusty). SprawdÅº uprawnienia udostÄ™pniania.", chat_id)
                return None, None
        else:
            log_status("BÅÄ„D: Plik nie istnieje po pobraniu.")
            wyslij_wiadomosc_tekstowa("âŒ BÅ‚Ä…d: Pobieranie pliku z Google Drive nie powiodÅ‚o siÄ™.", chat_id)
            return None, None
    except Exception as e:
        log_status(f"Krytyczny bÅ‚Ä…d w funkcji pobierania z GDrive: {e}")
        wyslij_wiadomosc_tekstowa("âŒ WystÄ…piÅ‚ bÅ‚Ä…d serwera podczas pobierania z Google Drive.", chat_id)
        return None, None

        

def rozpoznaj_i_przygotuj_audio(sciezka_pliku, chat_id):
    """UÅ¼ywa ffprobe do analizy pliku, wyodrÄ™bnia audio z wideo i zwraca Å›cieÅ¼kÄ™ do pliku audio."""
    log_status(f"Analizowanie pliku medialnego: {os.path.basename(sciezka_pliku)}")
    try:
        command = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_streams', sciezka_pliku]
        result = subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf-8')
        info = json.loads(result.stdout)
        
        ma_wideo = any(s.get('codec_type') == 'video' for s in info.get('streams', []))
        ma_audio = any(s.get('codec_type') == 'audio' for s in info.get('streams', []))

        if not ma_audio:
            wyslij_wiadomosc_tekstowa("âŒ BÅ‚Ä…d: PrzesÅ‚any plik nie zawiera Å›cieÅ¼ki dÅºwiÄ™kowej.", chat_id)
            if os.path.exists(sciezka_pliku): os.remove(sciezka_pliku)
            return None

        if ma_wideo:
            log_status("Wykryto strumieÅ„ wideo, rozpoczynam ekstrakcjÄ™ audio...")
            sciezka_audio = os.path.splitext(sciezka_pliku)[0] + ".mp3"
            ffmpeg_cmd = ['ffmpeg', '-i', sciezka_pliku, '-vn', '-q:a', '0', '-y', sciezka_audio]
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True, encoding='utf-8')
            os.remove(sciezka_pliku)
            log_status(f"Ekstrakcja audio zakoÅ„czona: {os.path.basename(sciezka_audio)}")
            return sciezka_audio
        else:
            log_status("Plik jest plikiem audio, nie wymaga ekstrakcji.")
            return sciezka_pliku
    except FileNotFoundError:
        log_status("KRYTYCZNY BÅÄ„D: `ffmpeg`/`ffprobe` nie jest zainstalowany lub nie ma go w Å›cieÅ¼ce systemowej (PATH).")
        wyslij_wiadomosc_tekstowa("âŒ BÅ‚Ä…d serwera: Brak narzÄ™dzi do przetwarzania wideo.", chat_id)
        if os.path.exists(sciezka_pliku): os.remove(sciezka_pliku)
        return None
    except Exception as e:
        log_status(f"BÅ‚Ä…d podczas analizy pliku ({e}). ZakÅ‚adam, Å¼e to plik audio.")
        return sciezka_pliku

def wyslij_plik_z_notatkami(transkrypcja, notatki, chat_id, temat_notatki):
    """Tworzy i wysyÅ‚a plik .md z notatkami, zapisujÄ…c go w odpowiednim folderze."""
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
        # Wybierz rozszerzenie ustawione dla chatu lub domyÅ›lne
        ext = get_chat_setting(chat_id, 'extension', config.DEFAULT_OUTPUT_EXTENSION)
        if not ext.startswith('.'):
            ext = f'.{ext}'

        nazwa_pliku = f"{nazwa_bazowa}{ext}"
        sciezka_pliku = os.path.join(folder_docelowy, nazwa_pliku)

        # TreÅ›Ä‡ pliku â€” jeÅ›li .md, zostaw format Markdown; w innych przypadkach zapisujemy prosty tekst
        if ext == '.md':
            zawartosc_pliku = f"# Transkrypcja\n\n{transkrypcja}\n\n---\n\n# Notatki\n\n{notatki}"
        else:
            zawartosc_pliku = f"Transkrypcja:\n{transkrypcja}\n\nNotatki:\n{notatki}"

        with open(sciezka_pliku, 'w', encoding='utf-8') as f:
            f.write(zawartosc_pliku)

        log_status(f"WysyÅ‚anie pliku '{nazwa_pliku}'...")
        with open(sciezka_pliku, 'rb') as f:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument",
                files={'document': f},
                data={'chat_id': chat_id}
            )
        if has_valid_token() and create_notion_note:
            try:
                log_status("Eksport do Notion...")
                create_notion_note(temat_notatki, transkrypcja, notatki or "Brak podsumowania.")
                wyslij_wiadomosc_tekstowa("âœ… Zapisano takÅ¼e w Notion.", chat_id)
            except Exception as e:
                log_status(f"Notion: {e}")
                wyslij_wiadomosc_tekstowa("â„¹ï¸ Nie udaÅ‚o siÄ™ zapisaÄ‡ w Notion (sprawdÅº token/uprawnienia).", chat_id)
    except Exception as e:
        log_status(f"BÅÄ„D podczas tworzenia/wysyÅ‚ania pliku: {e}")

def wyslij_wybor_promptu(chat_id):
    """WysyÅ‚a przyciski wyboru promptu."""
    przyciski = [[{"text": k.replace('_', ' ').capitalize(), "callback_data": f"prompt_{k}"}] for k in sorted(prompts.keys())]
    # Dodaj opcjÄ™ tylko transkrypcji bez analizy AI
    przyciski.append([{"text": "ðŸ”Š Tylko transkrypcja", "callback_data": "transcribe_only"}])
    przyciski.append([{"text": "âœï¸ WÅ‚asny prompt", "callback_data": "prompt_custom"}])
    przyciski.append([{"text": "âŒ Anuluj", "callback_data": "prompt_cancel"}])
    wyslij_wiadomosc_tekstowa(
        "âœ… Plik gotowy do przetworzenia.\n\nWybierz styl notatek:",
        chat_id,
        reply_markup={"inline_keyboard": przyciski}
    )

# --- GÅ‚Ã³wny proces przetwarzania ---

def rozpocznij_przetwarzanie(chat_id, model_whisper, prompt_uzytkownika, transcribe_only: bool = False):
    global ostatnie_zadanie
    
    sciezka_pliku_audio = ostatnie_zadanie.get('sciezka_pliku_audio')
    
    if not sciezka_pliku_audio or not os.path.exists(sciezka_pliku_audio):
        wyslij_wiadomosc_tekstowa("âŒ BÅ‚Ä…d: Plik audio do przetworzenia zniknÄ…Å‚. SprÃ³buj wysÅ‚aÄ‡ go ponownie.", chat_id)
        ostatnie_zadanie = {}
        return

    wyslij_wiadomosc_tekstowa("Krok 1/3: Rozpoczynam transkrypcjÄ™ audio... ðŸŽ¤", chat_id)
    # Pobierz ustawiony jÄ™zyk dla tego chatu (jeÅ›li istnieje)
    lang = get_chat_setting(chat_id, 'language', config.DEFAULT_TRANSCRIBE_LANGUAGE)
    transkrypcja = transcriber.transkrybuj_audio(sciezka_pliku_audio, model_whisper, language=lang)
    if not transkrypcja:
        wyslij_wiadomosc_tekstowa("âŒ BÅ‚Ä…d transkrypcji. Zatrzymano przetwarzanie.", chat_id)
        ostatnie_zadanie = {}
        return

    # JeÅ¼eli uÅ¼ytkownik wybraÅ‚ tylko transkrypcjÄ™ â€” zakoÅ„cz tutaj i wyÅ›lij plik z samÄ… transkrypcjÄ…
    if transcribe_only:
        wyslij_wiadomosc_tekstowa("Krok 2/2: ZapisujÄ™ i wysyÅ‚am samÄ… transkrypcjÄ™ (bez analizy AI).", chat_id)
        temat_transkrypcji = f"transkrypcja_{int(time.time())}"
        wyslij_plik_z_notatkami(transkrypcja, "", chat_id, temat_transkrypcji)
        ostatnie_zadanie = {}
        return

    wyslij_wiadomosc_tekstowa("Krok 2/3: Przetwarzanie i synteza notatek przez AI... ðŸ§ ", chat_id)
    fragmenty = llm_handler.podziel_tekst_na_fragmenty(transkrypcja)
    polaczone_notatki, success_map = llm_handler.przetworz_fragmenty_wstepnie(fragmenty, prompt_uzytkownika)

    if not success_map:
        # ZMIANA: Implementacja Twojej proÅ›by o fallback (awaria Fazy "Map")
        wyslij_wiadomosc_tekstowa("âŒ WystÄ…piÅ‚ bÅ‚Ä…d krytyczny na etapie analizy AI (Map). Otrzymasz plik z samÄ… transkrypcjÄ….", chat_id)
        temat_awaryjny = llm_handler.wygeneruj_temat_notatki(transkrypcja) # Wygeneruj temat z transkrypcji
        notatki_awaryjne = "## BÅÄ„D AI\n\nPrzetwarzanie notatek przez model AI nie powiodÅ‚o siÄ™. PoniÅ¼ej znajduje siÄ™ tylko surowa transkrypcja."
        wyslij_plik_z_notatkami(transkrypcja, notatki_awaryjne, chat_id, temat_awaryjny)
        ostatnie_zadanie = {}
        return

    notatki_finalne, success_reduce = llm_handler.dokonaj_finalnej_syntezy(polaczone_notatki)

    wyslij_wiadomosc_tekstowa("Krok 3/3: Finalizowanie i wysyÅ‚anie pliku... ðŸ“‚", chat_id)
    if success_reduce:
        # Scenariusz pomyÅ›lny
        temat_notatki = llm_handler.wygeneruj_temat_notatki(notatki_finalne)
        wyslij_plik_z_notatkami(transkrypcja, notatki_finalne, chat_id, temat_notatki)
    else:
        # ZMIANA: Implementacja Twojej proÅ›by o fallback (awaria Fazy "Reduce")
        wyslij_wiadomosc_tekstowa("âš ï¸ OSTRZEÅ»ENIE: Finalna synteza notatek nie powiodÅ‚a siÄ™. Otrzymasz plik z samÄ… transkrypcjÄ….", chat_id)
        temat_awaryjny = llm_handler.wygeneruj_temat_notatki(transkrypcja) # Wygeneruj temat z transkrypcji
        notatki_awaryjne = "## BÅÄ„D AI\n\nPrzetwarzanie notatek przez model AI powiodÅ‚o siÄ™ czÄ™Å›ciowo (Map), ale finalna synteza (Reduce) nie powiodÅ‚a siÄ™. PoniÅ¼ej znajduje siÄ™ tylko surowa transkrypcja."
        wyslij_plik_z_notatkami(transkrypcja, notatki_awaryjne, chat_id, temat_awaryjny)

    ostatnie_zadanie = {}

# --- GÅ‚Ã³wna pÄ™tla bota ---

def uruchom_bota(model_whisper):
    global ostatnie_zadanie
    inicjalizuj_bota()
    offset = 0
    
    try:
        with open(config.PLIK_PAMIECI_BOTA, "r") as f: offset = int(f.read().strip()) + 1
    except (FileNotFoundError, ValueError): pass

    log_status("Bot gotowy do pracy. NasÅ‚uchiwanie...")
    
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
                    # ObsÅ‚uga callbackÃ³w ustawieÅ„ (jÄ™zyk / rozszerzenie) - dziaÅ‚ajÄ… niezaleÅ¼nie od ostatniego zadania
                    if data.startswith('set_lang:'):
                        wartosc = data.split(':', 1)[1]
                        set_chat_setting(chat_id, 'language', wartosc)
                        wyslij_wiadomosc_tekstowa(f"âœ… Ustawiono jÄ™zyk transkrypcji na: {wartosc}", chat_id)
                        continue
                    if data.startswith('set_ext:'):
                        wartosc = data.split(':', 1)[1]
                        set_chat_setting(chat_id, 'extension', wartosc)
                        wyslij_wiadomosc_tekstowa(f"âœ… Ustawiono rozszerzenie plikÃ³w na: {wartosc}", chat_id)
                        continue
                    if not ostatnie_zadanie or ostatnie_zadanie.get('chat_id') != chat_id: continue

                    if data == 'prompt_custom':
                        ostatnie_zadanie['status'] = 'oczekiwanie_na_wlasny_prompt'
                        wyslij_wiadomosc_tekstowa("ProszÄ™, napisz teraz swÃ³j wÅ‚asny prompt:", chat_id)
                    elif data == 'transcribe_only':
                        # UÅ¼ytkownik wybraÅ‚ tylko zapisaÄ‡ i wysÅ‚aÄ‡ transkrypcjÄ™ bez analizy AI
                        if ostatnie_zadanie.get('chat_id') == chat_id and ostatnie_zadanie.get('sciezka_pliku_audio'):
                            ostatnie_zadanie['status'] = 'processing'
                            threading.Thread(target=rozpocznij_przetwarzanie, args=(chat_id, model_whisper, None, True)).start()
                        else:
                            wyslij_wiadomosc_tekstowa("Brak pliku do transkrypcji w kolejce.", chat_id)
                        continue
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
                            wyslij_wiadomosc_tekstowa(f"âŒ Plik jest za duÅ¼y. UÅ¼yj linku z chmury.", chat_id)
                         else:
                            pobrana_sciezka = pobierz_plik_z_telegrama(plik_telegrama['file_id'], plik_telegrama.get("file_name", "plik_telegrama.media"))
                    
                    wiadomosc_tekstowa = message.get("text", "")
                    # Komenda /help lub /start â€” pokaÅ¼ listÄ™ dostÄ™pnych komend
                    if isinstance(wiadomosc_tekstowa, str) and wiadomosc_tekstowa.strip().lower() in ('/help', '/start'):
                        lines = ["DostÄ™pne komendy:"]
                        for cmd, desc in COMMANDS.items():
                            lines.append(f"/{cmd} â€” {desc}")
                        wyslij_wiadomosc_tekstowa("\n".join(lines), chat_id)
                        continue
                    # Komenda /jezyk â€” pokaÅ¼ listÄ™ jÄ™zykÃ³w do wyboru
                    if isinstance(wiadomosc_tekstowa, str) and wiadomosc_tekstowa.strip().lower() == '/jezyk':
                        przyciski = [
                            [{"text": "Polski (pl)", "callback_data": "set_lang:pl"}],
                            [{"text": "Angielski (en)", "callback_data": "set_lang:en"}],
                            [{"text": "Automatycznie (auto)", "callback_data": "set_lang:auto"}],
                            [{"text": "Anuluj", "callback_data": "prompt_cancel"}],
                        ]
                        wyslij_wiadomosc_tekstowa("Wybierz jÄ™zyk transkrypcji:", chat_id, reply_markup={"inline_keyboard": przyciski})
                        continue

                    # Komenda /rozszerzenie â€” pokaÅ¼ listÄ™ rozszerzeÅ„
                    if isinstance(wiadomosc_tekstowa, str) and wiadomosc_tekstowa.strip().lower() == '/rozszerzenie':
                        przyciski_ext = [
                            [{"text": ".md", "callback_data": "set_ext:.md"}],
                            [{"text": ".txt", "callback_data": "set_ext:.txt"}],
                            [{"text": ".srt", "callback_data": "set_ext:.srt"}],
                            [{"text": "Anuluj", "callback_data": "prompt_cancel"}],
                        ]
                        wyslij_wiadomosc_tekstowa("Wybierz rozszerzenie plikÃ³w z notatkami:", chat_id, reply_markup={"inline_keyboard": przyciski_ext})
                        continue
                    if "http" in wiadomosc_tekstowa and not pobrana_sciezka:
                        log_status(f"Wykryto link w wiadomoÅ›ci od {chat_id}. PrÃ³ba pobrania...")
                        if "drive.google.com" in wiadomosc_tekstowa:
                            pobrana_sciezka, oryginalna_nazwa = pobierz_plik_z_gdrive(wiadomosc_tekstowa, chat_id)
                    
                    if pobrana_sciezka:
                        sciezka_audio = rozpoznaj_i_przygotuj_audio(pobrana_sciezka, chat_id)
                        if sciezka_audio:
                            if ostatnie_zadanie.get('status') == 'processing':
                                wyslij_wiadomosc_tekstowa("âš ï¸ Poczekaj, aÅ¼ poprzednie zadanie zostanie ukoÅ„czone.", chat_id)
                            else:
                                ostatnie_zadanie = {'status': 'oczekiwanie_na_wybor_promptu', 'sciezka_pliku_audio': sciezka_audio, 'chat_id': chat_id}
                                wyslij_wybor_promptu(chat_id)

        except requests.exceptions.RequestException as e:
            log_status(f"BÅ‚Ä…d poÅ‚Ä…czenia z serwerem Telegrama: {e}. PrÃ³ba za 5 sekund...")
            time.sleep(5)
        except Exception as e:
            log_status(f"Nieoczekiwany bÅ‚Ä…d w gÅ‚Ã³wnej pÄ™tli: {e}")
            time.sleep(5)
        finally:
            with open(config.PLIK_PAMIECI_BOTA, "w") as f:
                f.write(str(offset-1))





