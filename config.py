# config.py
# Centralny plik konfiguracyjny dla bota.

# --- ŚCIEŻKI I NAZWY PLIKÓW ---
TELEGRAM_TOKEN_FILE = "secrets/TokenBota.txt"
FOLDER_POBIERANIA = "runtime/audio_do_przetworzenia"
FOLDER_PROMPTOW = "prompts"
PLIK_PRZEDMIOTOW = "data/przedmioty.json"
PLIK_PAMIECI_BOTA = "data/last_update_id.txt"

# --- USTAWIENIA MODELI AI ---
LOKALNE_AI_URL = "http://localhost:1234/v1"
MODEL_WHISPER = "base"
# Nazwa modelu LLM używanego do analizy notatek przez LM Studio
LLM_MODEL_NAME = "local-model"

# --- USTAWIENIA PRZETWARZANIA ---
MAX_FILE_SIZE_TELEGRAM = 20 * 1024 * 1024  # Limit 20 MB dla plików z Telegrama

# Ustawienia dla dzielenia długich transkrypcji
MAX_CONTEXT_TOKENS = 4096  # Maksymalny kontekst Twojego modelu w LM Studio
PROMPT_BUFFER = 1536     # Zostawiamy spory bufor na prompt, instrukcje i odpowiedź AI
CHUNK_TOKEN_LIMIT = MAX_CONTEXT_TOKENS - PROMPT_BUFFER # Bezpieczny limit tokenów na fragment = 2560

# --- DOMYŚLNY JĘZYK DLA TRANSKRYPCJI ---
# Możesz ustawić tu domyślny język używany przez Whisper (np. "pl" dla polskiego)
DEFAULT_TRANSCRIBE_LANGUAGE = "pl"
# Domyślne rozszerzenie pliku wyjściowego (możesz zmienić na ".txt" lub ".srt")
DEFAULT_OUTPUT_EXTENSION = ".txt"

# Plik, w którym przechowujemy ustawienia per-chat (język, rozszerzenie)
CHAT_SETTINGS_FILE = "data/chat_settings.json"

# Ścieżki dla przepływu z Gemini/plikami
TRANSKRYPCJE_DIR = "runtime/transkrypcje"
TRANSKRYPCJE_DONE_DIR = "runtime/transkrypcje-zrobione"
TRANSKRYPCJE_AI_DIR = "runtime/transkrypcje-AI"

