# VoiceNote AI – instrukcje

## Link do strony (GitHub Pages)
- Landing: https://kacperpe.github.io/LectureNotes/
- Studio: https://kacperpe.github.io/LectureNotes/studio.html
- Uwaga: `studio.html` wymaga zalogowania (demo auth w `localStorage`).


## Dla użytkownika (operacyjne)
- Wymagane: Python 3.11, internet do pobierania z GDrive, token Notion (secret_…) z integracji udostępnionej bazie `2c5870e0ab6781e1a59ed0e415bf859f`.
- Start backendu:
  - Ustaw token: `$env:NOTION_TOKEN="secret_xxx"`
  - `cd backend`
  - `python -m uvicorn api_server:app --reload --host 0.0.0.0 --port 8000`
  - Sprawdź: `http://127.0.0.1:8000/api/health` → `{"status":"ok"}`
- Start frontu (drugie okno):
  - `cd frontend`
  - `python -m http.server 3001`
  - Otwórz `http://localhost:3001/index.html`
- Użycie w UI:
  - Wklej publiczny link GDrive → „Importuj z GDrive” (transkrypcja).
  - „Eksportuj do Notion” zapisze stronę (callout z podsumowaniem + transkrypcja w paragrafach).
- GPU: jeśli masz CUDA 11.8, zainstaluj PyTorch GPU (poniżej sekcja dev) i backend uruchamiaj tym samym Pythonem.

## Dla developera
- Struktura:
  - `frontend/index.html` – statyczny React z Tailwind CDN (tryby Deep/Swiss, GDrive input, pseudo-progresy).
  - `backend/api_server.py` – FastAPI: `/api/import-drive` (gdown + transkrypcja Whisper), `/api/export-notion` (Notion).
  - `backend/notion_sync.py` – tworzenie stron w Notion, callout + paragrafy dzielone co 1900 znaków.
- Zależności (instaluj tym samym interpreterem co uvicorn):
  - CPU: `python -m pip install "numpy<2.2" torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 openai-whisper==20231117 fastapi uvicorn[standard] gdown`
  - GPU (CUDA 11.8): odinstaluj torch* i zainstaluj `torch==2.1.2+cu118 torchvision==0.16.2+cu118 torchaudio==2.1.2+cu118 --index-url https://download.pytorch.org/whl/cu118`, reszta jak wyżej.
- Uruchamianie backendu:
  - `cd backend`
  - `python -m uvicorn api_server:app --reload --host 0.0.0.0 --port 8000`
- Test API Notion (po ustawieniu `NOTION_TOKEN`):
  - `Invoke-RestMethod -Uri http://127.0.0.1:8000/api/export-notion -Method Post -Headers @{ "Content-Type"="application/json" } -Body '{"transcription":"test","summary":"test","title":"test"}'`
- Notion:
  - Baza: `2c5870e0ab6781e1a59ed0e415bf859f`.
  - Token: `NOTION_TOKEN` = sekret integracji (`secret_...` / `ntn_...`) z dostępem do bazy (Share/Connections).
- Transkrypcja:
  - Whisper użyje GPU gdy `torch.cuda.is_available()`; nic nie zmieniasz w kodzie.
  - Jeśli błąd „Numpy is not available” – upewnij się, że instalacja była na tym samym interpreterze co uvicorn.

## Szybkie komendy PowerShell (CPU przykład)
```
$env:NOTION_TOKEN="secret_xxx"
cd C:\Users\kacpe\OneDrive\Programowanie\Nagrania_Bot_aplikacja_telegram\backend
python -m uvicorn api_server:app --reload --host 0.0.0.0 --port 8000
# nowe okno
cd C:\Users\kacpe\OneDrive\Programowanie\Nagrania_Bot_aplikacja_telegram\frontend
python -m http.server 3001
```

## TODO / Stan integracji
- [ ] Spiąć frontend/REST z backendem Notion/Gemini dla pełnego przepływu (import → transkrypcja → analiza prompt → zapis w Notion).
- [ ] Telegram: połączony z Notion (wysyłka pliku + zapis strony, gdy jest token), ale analiza Gemini nie jest jeszcze wpięta (trzeba podmienić flow w `telegram_handler.py`).
- [ ] Transkrypcje plików: tymczasowo pliki nie są usuwane (zmiana w transcriberze do zrobienia ręcznie), potrzebne foldery `transkrypcje`, `transkrypcje-zrobione`, `transkrypcje-AI`.
- [ ] Gemini CLI: dodano wrapper `gemini_cli.py`, ale endpointy jeszcze nie wywołują go; wymaga gemini w PATH i decyzji, gdzie zapisywać (katalog `transkrypcje-AI`).
- [ ] Frontend: prompt dropdown ładuje się z `/api/prompts`; sekcja transkrypcji jest read-only; trzeba przesłać prompt do backendu przy eksporcie/analityce.
- [ ] Health: backend `api/health` pokazuje tylko token Notion; dodać test Gemini/ffmpeg jeśli potrzebne.

### Co działa
- Backend FastAPI (`api_server.py`): /api/import-drive (pobiera GDrive, transkrybuje Whisper), /api/export-notion (tworzy stronę w bazie), /api/prompts (ładuje prompty z folderu).
- Frontend statyczny: UI „Deep Focus/Swiss”, import z GDrive, wybór promptu z folderu `prompts`, eksport do Notion (wysyła prompt content w payload).
- Notion: zapis callout + transkrypcja w paragrafach; działający gdy `NOTION_TOKEN` ustawiony i integracja ma dostęp.

### Co nie działa / do spięcia
- Telegram flow nadal używa lokalnego LLM (LLM handler); trzeba ręcznie podmienić sekcję analizy na wywołanie `gemini_cli.analyze_transcription_with_gemini` i zapewnić zapis do `transkrypcje-AI`/Notion.
- Transcriber nadal usuwa pliki po transkrypcji w repo; żeby zostawiać pliki, usuń blok `os.remove(...)` w `transcriber.py`.
- Gemini CLI nie jest wywoływane z backendu /api; brak zapisu transkrypcji+analizy do `transkrypcje-AI`.

## Aktualna struktura katalogow (po porzadkach)
- `backend/` - API FastAPI i integracja Notion.
- `frontend/` - statyczny frontend (`frontend/index.html`).
- `prompts/` - szablony promptow.
- `data/` - pliki danych (`chat_settings.json`, `last_update_id.txt`, `przedmioty.json`).
- `runtime/` - pliki robocze (`audio_do_przetworzenia`, `transkrypcje`, `transkrypcje-zrobione`, `transkrypcje-AI`).
- `secrets/` - pliki tokenow (`TokenBota.txt`, inne tokeny lokalne).
- `scripts/windows/` - skrypty `.bat` i cleanup script (`czysc_kolejke.py`).
- `frontend/legacy/` - starszy prototypowy `index.html`.

## Aktualne komendy skryptow
- Start bota (Windows): `scripts\\windows\\start_bota.bat`
- Czyszczenie kolejki Telegram (Windows): `scripts\\windows\\czysc_kolejke.bat`
