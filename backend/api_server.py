"""
FastAPI serwer dla VoiceNote AI:
- /api/import-drive: pobiera plik z Google Drive, transkrybuje Whisperem i zwraca tekst.
- /api/export-notion: wysyła transkrypcję do Notion (używa backend/notion_sync.py).

Uruchom:
    cd backend
    uvicorn api_server:app --reload --port 8000
"""

import os
import sys
import tempfile
from pathlib import Path
import gdown
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Upewnij się, że katalog główny repo jest w sys.path (aby załadować transcriber.py itp.)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import transcriber  # teraz powinno się załadować
try:
    # kiedy odpalasz jako "python -m uvicorn backend.api_server:app"
    from backend.notion_sync import create_notion_note, NOTION_TOKEN
except ImportError:
    # kiedy odpalasz z katalogu backend/
    from notion_sync import create_notion_note, NOTION_TOKEN
import config

# --- Konfiguracja ---
API_PORT = int(os.getenv("API_PORT", "8000"))
MODEL_NAME = os.getenv("WHISPER_MODEL", "base")

app = FastAPI(title="VoiceNote AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model_whisper = None


def ensure_model():
    global model_whisper
    if model_whisper is None:
        model_whisper = transcriber.load_model(MODEL_NAME)
    return model_whisper


class ImportDrivePayload(BaseModel):
    drive_url: str


class ExportNotionPayload(BaseModel):
    transcription: str
    summary: str | None = None
    title: str | None = None


@app.post("/api/import-drive")
def import_drive(payload: ImportDrivePayload):
    drive_url = payload.drive_url.strip()
    if not drive_url:
        return {"error": "Brak linku"}  # FastAPI zwróci 200, ale z polem error

    tmp_dir = tempfile.mkdtemp(prefix="voicenote_drive_")
    target_path = os.path.join(tmp_dir, "imported_file")

    # Pobierz z Google Drive
    try:
        gdown.download(drive_url, target_path, quiet=False, fuzzy=True)
    except Exception as e:
        return {"error": f"Błąd pobierania: {e}"}

    if not os.path.exists(target_path) or os.path.getsize(target_path) < 1000:
        return {"error": "Pobrany plik jest pusty lub nie istnieje."}

    # Transkrypcja
    try:
        model = ensure_model()
        text = transcriber.transkrybuj_audio(target_path, model)
    except Exception as e:
        return {"error": f"Błąd transkrypcji: {e}"}

    return {"transcription": text or "", "summary": "Autopodsumowanie niedostępne w tym endpoint."}


@app.post("/api/export-notion")
def export_notion(payload: ExportNotionPayload):
    try:
        res = create_notion_note(
            title=payload.title or "VoiceNote",
            transcription=payload.transcription or "",
            summary=payload.summary or "Brak podsumowania",
        )
        return {"status": "ok", "page_id": res.get("id")}
    except Exception as e:
        return {"error": str(e)}


@app.get("/api/health")
def health():
    return {"status": "ok", "notion_token_configured": bool(NOTION_TOKEN and NOTION_TOKEN != "YOUR_SECRET_TOKEN")}


@app.get("/api/prompts")
def list_prompts():
    """
    Zwraca listę promptów z folderu prompts (pliki prompt_*.txt).
    """
    prompts_dir = Path(REPO_ROOT) / config.FOLDER_PROMPTOW
    items = []
    if prompts_dir.exists():
        for p in sorted(prompts_dir.glob("prompt_*.txt")):
            try:
                key = p.stem.replace("prompt_", "")
                content = p.read_text(encoding="utf-8").strip()
                items.append({"key": key, "label": key.replace("_", " ").title(), "content": content})
            except Exception:
                continue
    return {"prompts": items}
