"""Small, source-attributed supplement for rare words unavailable to live APIs."""
import json
from pathlib import Path

from app.services.dictionary import DictionaryEntry


DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "reviewed_dictionary.json"


def lookup_reviewed_entry(word: str) -> DictionaryEntry | None:
    normalized = " ".join(word.casefold().split())
    try:
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    record = data.get(normalized)
    if not record or " ".join(record.get("word", "").casefold().split()) != normalized:
        return None
    return DictionaryEntry(**record["entry"])
