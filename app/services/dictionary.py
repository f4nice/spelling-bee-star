from dataclasses import dataclass
from html import unescape
import re
from urllib.parse import quote

import httpx

from app.config import Settings


@dataclass
class DictionaryEntry:
    phonetic: str | None = None
    part_of_speech: str | None = None
    american_audio_url: str | None = None
    british_audio_url: str | None = None
    english_definition: str | None = None
    english_example: str | None = None
    source: str | None = None
    chinese_definition: str | None = None


class MerriamWebsterClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def lookup(self, word: str) -> DictionaryEntry:
        if not self.settings.merriam_webster_api_key:
            raise RuntimeError("MERRIAM_WEBSTER_API_KEY is not configured")

        reference = self.settings.merriam_webster_reference
        url = f"https://www.dictionaryapi.com/api/v3/references/{reference}/json/{quote(word.strip(), safe='')}"
        params = {"key": self.settings.merriam_webster_api_key}
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPStatusError as exc:
            # httpx's normal message contains the full URL, including the key.
            raise RuntimeError(f"韦氏词典接口返回 HTTP {exc.response.status_code}。") from None
        except httpx.HTTPError:
            raise RuntimeError("韦氏词典接口连接失败，请稍后重试。") from None
        except ValueError:
            raise RuntimeError("韦氏词典接口返回的内容无法解析。") from None

        # Suggestions and related words are not definitions of the requested word.
        entry = next((item for item in payload if isinstance(item, dict) and
                      _merriam_entry_matches(item, word)), None) if isinstance(payload, list) else None
        if not entry:
            raise RuntimeError("韦氏词典未返回完全匹配的词条。")

        hwi = entry.get("hwi") or {}
        prs = hwi.get("prs") or []
        phonetic = next((str(item["ipa"]).strip() for item in prs if item.get("ipa")), None)
        if not phonetic:
            phonetic = next((formatted for item in prs
                             if (formatted := _merriam_phonetic(item.get("mw")))), None)
        sound = next((item.get("sound", {}) for item in prs if item.get("sound", {}).get("audio")), {})
        audio = _audio_url(sound.get("audio")) if sound else None

        definition = _first_definition(entry)
        example = _first_example(entry)

        return DictionaryEntry(
            phonetic=phonetic,
            part_of_speech=_optional_clean(entry.get("fl")),
            american_audio_url=audio,
            british_audio_url=None,
            english_definition=definition,
            english_example=example,
            source="https://www.merriam-webster.com/dictionary/" + quote(word.strip(), safe=""),
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
        part_of_speech, definition, example = _first_free_meaning_fields(entry)

        return DictionaryEntry(
            phonetic=phonetic,
            part_of_speech=part_of_speech,
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


def _first_free_meaning_fields(entry: dict) -> tuple[str | None, str | None, str | None]:
    for meaning in entry.get("meanings", []):
        for definition_item in meaning.get("definitions", []):
            definition = _optional_clean(definition_item.get("definition"))
            if definition:
                # A later sense's example must not be attached to this meaning.
                return (
                    _optional_clean(meaning.get("partOfSpeech")), definition,
                    _optional_clean(definition_item.get("example")),
                )
    return None, None, None


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
    sense = _first_defined_sense(entry)
    if sense:
        return _clean(_walk_for_text(sense.get("dt"), "text"))
    shortdefs = entry.get("shortdef") or []
    if shortdefs:
        return _clean(shortdefs[0])
    return None


def _first_example(entry: dict) -> str | None:
    # Keep the example in the same sense as the returned definition. An example
    # in a later sense, run-on or synonym paragraph can teach a different meaning.
    sense = _first_defined_sense(entry)
    return _clean(_walk_for_text(sense.get("dt"), "vis")) if sense else None


def _first_defined_sense(entry: dict) -> dict | None:
    for definition_block in entry.get("def", []):
        for sense in _walk_senses(definition_block.get("sseq", [])):
            if _clean(_walk_for_text(sense.get("dt"), "text")):
                return sense
    return None


def _walk_senses(value):
    if isinstance(value, list):
        if len(value) == 2 and value[0] == "sense" and isinstance(value[1], dict):
            yield value[1]
        else:
            for item in value:
                yield from _walk_senses(item)
    elif isinstance(value, dict):
        # Binding substitutes use {"sense": {...}} rather than a tagged pair.
        if isinstance(value.get("sense"), dict):
            yield value["sense"]
        else:
            for item in value.values():
                yield from _walk_senses(item)


def _walk_for_text(value, target_key: str) -> str | None:
    if isinstance(value, dict):
        if target_key in value:
            return _extract_text(value[target_key])
        for item in value.values():
            found = _walk_for_text(item, target_key)
            if found:
                return found
    elif isinstance(value, list):
        # The official API represents dt elements as tagged arrays, e.g.
        # ["vis", [{"t": "An example."}]], not as {"vis": ...} objects.
        if len(value) == 2 and value[0] == target_key:
            return _extract_text(value[1])
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
    # Cross-reference tokens contain visible words; do not discard their text.
    text = re.sub(r"\{(?:a_link|d_link|dxt|et_link|i_link|mat|sx)\|([^{}|]*)(?:\|[^{}]*)?\}", r"\1", text)
    text = re.sub(r"\{[^{}]*\}", "", text)
    return unescape(" ".join(text.split()))


def _normalize_merriam_headword(value: str) -> str:
    value = re.sub(r":\d+$", "", str(value).strip())
    return " ".join(value.replace("*", "").replace("·", "").replace("\u200b", "")
                    .replace("’", "'").casefold().split())


def _merriam_entry_matches(entry: dict, word: str) -> bool:
    expected = _normalize_merriam_headword(word)
    if not expected:
        return False
    candidates = [(entry.get("hwi") or {}).get("hw"), (entry.get("meta") or {}).get("id")]
    return any(value and _normalize_merriam_headword(value) == expected for value in candidates)


def _merriam_phonetic(value: str | None) -> str | None:
    text = _optional_clean(value)
    # MW uses its own respelling system, not IPA. A cutback pronunciation such
    # as "-dərə(r)" is only a suffix and must not masquerade as a full word.
    if not text or text.startswith(("-", "–", "—")) or text.endswith(("-", "–", "—")):
        return None
    return "韦氏标音：" + text


def _optional_clean(text: str | None) -> str | None:
    if not text:
        return None
    return " ".join(str(text).split())
