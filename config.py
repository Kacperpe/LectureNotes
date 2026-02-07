# config.py
# Centralny plik konfiguracyjny dla bota.

# --- ÅšCIEÅ»KI I NAZWY PLIKÃ“W ---
TELEGRAM_TOKEN_FILE = "secrets/TokenBota.txt"
FOLDER_POBIERANIA = "runtime/audio_do_przetworzenia"
FOLDER_PROMPTOW = "prompts"
PLIK_PRZEDMIOTOW = "data/przedmioty.json"
PLIK_PAMIECI_BOTA = "data/last_update_id.txt"

# --- USTAWIENIA MODELI AI ---
LOKALNE_AI_URL = "http://localhost:1234/v1"
MODEL_WHISPER = "base"
# Nazwa modelu LLM uÅ¼ywanego do analizy notatek przez LM Studio
LLM_MODEL_NAME = "local-model"

# --- USTAWIENIA PRZETWARZANIA ---
MAX_FILE_SIZE_TELEGRAM = 20 * 1024 * 1024  # Limit 20 MB dla plikÃ³w z Telegrama

# Ustawienia dla dzielenia dÅ‚ugich transkrypcji
MAX_CONTEXT_TOKENS = 4096  # Maksymalny kontekst Twojego modelu w LM Studio
PROMPT_BUFFER = 1536     # Zostawiamy spory bufor na prompt, instrukcje i odpowiedÅº AI
CHUNK_TOKEN_LIMIT = MAX_CONTEXT_TOKENS - PROMPT_BUFFER # Bezpieczny limit tokenÃ³w na fragment = 2560

# --- DOMYÅšLNY JÄ˜ZYK DLA TRANSKRYPCJI ---
# MoÅ¼esz ustawiÄ‡ tu domyÅ›lny jÄ™zyk uÅ¼ywany przez Whisper (np. "pl" dla polskiego)
DEFAULT_TRANSCRIBE_LANGUAGE = "pl"
# DomyÅ›lne rozszerzenie pliku wyjÅ›ciowego (moÅ¼esz zmieniÄ‡ na ".txt" lub ".srt")
DEFAULT_OUTPUT_EXTENSION = ".txt"

# Plik, w ktÃ³rym przechowujemy ustawienia per-chat (jÄ™zyk, rozszerzenie)
CHAT_SETTINGS_FILE = "data/chat_settings.json"

# ÅšcieÅ¼ki dla przepÅ‚ywu z Gemini/plikami
TRANSKRYPCJE_DIR = "runtime/transkrypcje"
TRANSKRYPCJE_DONE_DIR = "runtime/transkrypcje-zrobione"
TRANSKRYPCJE_AI_DIR = "runtime/transkrypcje-AI"

