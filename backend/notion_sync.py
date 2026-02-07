"""
Integracja z Notion dla VoiceNote AI.
Tworzy stronę w bazie Notion z podsumowaniem i pociętą transkrypcją.
"""

import os
from datetime import datetime
import requests

DATABASE_ID = "2c5870e0ab6781e1a59ed0e415bf859f"
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "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")
NOTION_API_URL = "https://api.notion.com/v1/pages"
NOTION_VERSION = "2022-06-28"

def has_valid_token() -> bool:
    return bool(NOTION_TOKEN and NOTION_TOKEN != "YOUR_SECRET_TOKEN")


def chunk_text(text: str, max_length: int = 1900):
    """Dzieli tekst na fragmenty krótsze niż max_length (limit Notion to 2000)."""
    if not text:
        return []
    return [text[i : i + max_length] for i in range(0, len(text), max_length)]


def build_rich_text(content: str):
    return [{"type": "text", "text": {"content": content}}]


def create_notion_note(title: str, transcription: str, summary: str):
    """Tworzy stronę w bazie Notion i wstawia podsumowanie + pociętą transkrypcję."""
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    children_blocks = [
        {
            "object": "block",
            "type": "callout",
            "callout": {
                "icon": {"emoji": "📝"},
                "rich_text": build_rich_text(summary or "Brak podsumowania."),
                "color": "gray_background",
            },
        },
        {
            "object": "block",
            "type": "divider",
            "divider": {},
        },
        {
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": build_rich_text("Pełna Transkrypcja")},
        },
    ]

    for idx, chunk in enumerate(chunk_text(transcription or "")):
        children_blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": build_rich_text(chunk),
                    "color": "default",
                },
            }
        )
        # Dodaj subtelne separatory co kilka paragrafów dla czytelności
        if (idx + 1) % 4 == 0:
            children_blocks.append({"object": "block", "type": "divider", "divider": {}})

    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Name": {
                "title": build_rich_text(title or f"Notatka {datetime.utcnow().isoformat()}"),
            }
        },
        "children": children_blocks,
    }

    response = requests.post(NOTION_API_URL, headers=headers, json=payload, timeout=15)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    # Przykładowe użycie (do szybkiego testu manualnego):
    demo_title = "VoiceNote Demo"
    demo_transcription = "A" * 4200  # sztuczny tekst, by zobaczyć podział na bloki
    demo_summary = "Podsumowanie testowe."
    try:
        result = create_notion_note(demo_title, demo_transcription, demo_summary)
        print("Utworzono stronę w Notion:", result.get("id"))
    except Exception as exc:
        print("Błąd podczas wysyłki do Notion:", exc)
