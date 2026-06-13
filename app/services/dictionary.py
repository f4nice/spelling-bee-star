from dataclasses import dataclass
from html import unescape
import re

import httpx

from app.config import Settings


@dataclass
class DictionaryEntry:
    phonetic: str | None = None
    american_audio_url: str | None = None
    british_audio_url: str | None = None
    english_definition: str | None = None
    english_example: str | None = None
    source: str | None = None


class MerriamWebsterClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def lookup(self, word: str) -> DictionaryEntry:
        if not self.settings.merriam_webster_api_key:
            raise RuntimeError("MERRIAM_WEBSTER_API_KEY is not configured")

        reference = self.settings.merriam_webster_reference
        url = f"https://www.dictionaryapi.com/api/v3/references/{reference}/json/{word}"
        params = {"key": self.settings.merriam_webster_api_key}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        entry = next((item for item in payload if isinstance(item, dict)), None)
        if not entry:
            suggestions = ", ".join(str(item) for item in payload[:5]) if isinstance(payload, list) else ""
            raise RuntimeError(f"No dictionary entry found. Suggestions: {suggestions}")

        hwi = entry.get("hwi") or {}
        prs = hwi.get("prs") or []
        pronunciation = next((item for item in prs if item.get("mw")), None)
        sound = next((item.get("sound", {}) for item in prs if item.get("sound", {}).get("audio")), {})
        audio = _audio_url(sound.get("audio")) if sound else None

        definition = _first_definition(entry)
        example = _first_example(entry)

        return DictionaryEntry(
            phonetic=pronunciation.get("mw") if pronunciation else None,
            american_audio_url=audio,
            british_audio_url=None,
            english_definition=definition,
            english_example=example,
            source="Merriam-Webster Collegiate Dictionary",
        )


class FreeDictionaryClient:
    source_name = "Free Dictionary API"

    async def lookup(self, word: str) -> DictionaryEntry:
        payload = await _fetch_free_dictionary_payload(word, allow_missing=True)
        entry = next((item for item in payload if isinstance(item, dict)), None)
        if not entry:
            raise RuntimeError("开放词典暂未收录这个词，可以手动编辑定义、例句和音频。")

        phonetic = _first_free_phonetic(entry)
        american_audio, british_audio = _free_audio_urls(payload)
        definition, example = _first_free_definition_and_example(entry)

        return DictionaryEntry(
            phonetic=phonetic,
            american_audio_url=american_audio,
            british_audio_url=british_audio,
            english_definition=definition,
            english_example=example,
            source=self.source_name,
        )


class FreeDictionaryAudioClient:
    async def lookup_audio(self, word: str) -> tuple[str | None, str | None]:
        payload = await _fetch_free_dictionary_payload(word, allow_missing=True)
        return _free_audio_urls(payload)


async def _fetch_free_dictionary_payload(word: str, allow_missing: bool = False) -> list[dict]:
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(url)
        if response.status_code == 404 and allow_missing:
            return []
        response.raise_for_status()
        payload = response.json()
    return payload if isinstance(payload, list) else []


def _first_free_phonetic(entry: dict) -> str | None:
    if entry.get("phonetic"):
        return str(entry["phonetic"]).strip().strip("/") or None
    for phonetic in entry.get("phonetics", []):
        text = str(phonetic.get("text", "")).strip().strip("/")
        if text:
            return text
    return None


def _first_free_definition_and_example(entry: dict) -> tuple[str | None, str | None]:
    for meaning in entry.get("meanings", []):
        for definition_item in meaning.get("definitions", []):
            definition = definition_item.get("definition")
            if definition:
                return str(definition).strip(), _optional_clean(definition_item.get("example"))
    return None, None


def _free_audio_urls(payload: list[dict]) -> tuple[str | None, str | None]:
    american_audio = None
    british_audio = None
    fallback_audio = None

    for entry in payload:
        for phonetic in entry.get("phonetics", []):
            audio = phonetic.get("audio")
            if not audio:
                continue
            source = " ".join(str(phonetic.get(key, "")) for key in ("sourceUrl", "license"))
            text = str(phonetic.get("text", "")).lower()
            marker = f"{source} {audio} {text}".lower()
            if not british_audio and any(token in marker for token in ("uk", "gb", "british")):
                british_audio = audio
            elif not american_audio and any(token in marker for token in ("us", "american")):
                american_audio = audio
            elif not fallback_audio:
                fallback_audio = audio

    return american_audio or fallback_audio, british_audio


def _audio_url(audio: str | None) -> str | None:
    if not audio:
        return None
    if audio.startswith("bix"):
        subdir = "bix"
    elif audio.startswith("gg"):
        subdir = "gg"
    elif audio[0].isdigit() or audio[0] in "_!":
        subdir = "number"
    else:
        subdir = audio[0]
    return f"https://media.merriam-webster.com/audio/prons/en/us/mp3/{subdir}/{audio}.mp3"


def _first_definition(entry: dict) -> str | None:
    shortdefs = entry.get("shortdef") or []
    if shortdefs:
        return _clean(shortdefs[0])

    for definition_block in entry.get("def", []):
        for sense_sequence in definition_block.get("sseq", []):
            text = _walk_for_text(sense_sequence, "dt")
            if text:
                return _clean(text)
    return None


def _first_example(entry: dict) -> str | None:
    for definition_block in entry.get("def", []):
        for sense_sequence in definition_block.get("sseq", []):
            example = _walk_for_text(sense_sequence, "vis")
            if example:
                return _clean(example)
    return None


def _walk_for_text(value, target_key: str) -> str | None:
    if isinstance(value, dict):
        if target_key in value:
            return _extract_text(value[target_key])
        for item in value.values():
            found = _walk_for_text(item, target_key)
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _walk_for_text(item, target_key)
            if found:
                return found
    return None


def _extract_text(value) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if "t" in value:
            return str(value["t"])
        if "text" in value:
            return str(value["text"])
    if isinstance(value, list):
        for item in value:
            text = _extract_text(item)
            if text:
                return text
    return None


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    text = re.sub(r"\{/?[a-z|:0-9 ]+\}", "", text)
    return unescape(" ".join(text.split()))


def _optional_clean(text: str | None) -> str | None:
    if not text:
        return None
    return " ".join(str(text).split())
