"""
Prosty wrapper CLI do uruchamiania analizy Gemini nad plikami transkrypcji.
Założenia:
- W katalogu TRANSKRYPCJE_DIR trzymamy jeden plik .txt z transkrypcją.
- Wywołujemy CLI `gemini` (musi być w PATH) z promptem i ścieżką do pliku.
- Zwracamy wygenerowaną notatkę, dopisujemy ją na końcu pliku i przenosimy plik do folderu DONE.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
import config


GEMINI_COMMAND = ["gemini", "pro"]


def ensure_dirs():
    Path(config.TRANSKRYPCJE_DIR).mkdir(parents=True, exist_ok=True)
    Path(config.TRANSKRYPCJE_DONE_DIR).mkdir(parents=True, exist_ok=True)


def run_gemini(file_path: Path, prompt: str) -> str:
    """
    Uruchamia CLI 'gemini pro' z promptem i plikiem jako kontekstem.
    Zwraca wyjście tekstowe.
    """
    cmd = GEMINI_COMMAND + ["--input", prompt, "--file", str(file_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=300)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Gemini CLI zwrócił błąd")
    return result.stdout.strip()


def analyze_transcription_with_gemini(transcription_text: str, base_title: str) -> tuple[str, str, Path]:
    """
    Zapisuje transkrypcję do pliku w TRANSKRYPCJE_DIR, wywołuje Gemini,
    dopisuje notatkę na końcu pliku, przenosi plik do TRANSKRYPCJE_DONE_DIR.
    Zwraca (notatka, zawartosc_transkrypcji, sciezka_docelowa).
    """
    ensure_dirs()
    base_title = base_title or "transkrypcja"
    safe_title = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in base_title.lower())
    target_path = Path(config.TRANSKRYPCJE_DIR) / f"{safe_title}.txt"

    # Upewnij się, że w katalogu jest co najwyżej jeden plik tekstowy
    existing_txt = list(Path(config.TRANSKRYPCJE_DIR).glob("*.txt"))
    if existing_txt and target_path not in existing_txt:
        raise RuntimeError(f"W folderze {config.TRANSKRYPCJE_DIR} musi być maksymalnie jeden plik .txt")

    target_path.write_text(transcription_text, encoding="utf-8")

    prompt = (
        "Przeanalizuj transkrypcję z załączonego pliku i napisz specjalistyczną, zwięzłą notatkę. "
        "Uwzględnij najważniejsze decyzje, action items i ryzyka. Format: Markdown."
    )
    note = run_gemini(target_path, prompt)

    with target_path.open("a", encoding="utf-8") as f:
        f.write("\n\n---\n\n# Notatka (Gemini)\n")
        f.write(note)

    done_path = Path(config.TRANSKRYPCJE_DONE_DIR) / target_path.name
    shutil.move(str(target_path), done_path)
    return note, transcription_text, done_path
