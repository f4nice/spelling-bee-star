import re
from pathlib import Path
from urllib.parse import urlencode

import httpx

from app.services.dictionary import FreeDictionaryAudioClient


AUDIO_HEADERS = {"User-Agent": "Mozilla/5.0"}


def is_local_audio_url(url: str | None) -> bool:
    return bool(url and url.startswith("/media/audio/"))


def audio_candidates(word: str, accent: str) -> list[dict]:
    google_lang = "en-GB" if accent == "gb" else "en-US"
    primary_youdao_type = "1" if accent == "gb" else "2"
    secondary_youdao_type = "2" if primary_youdao_type == "1" else "1"
    return [
        {
            "key": f"youdao-{primary_youdao_type}",
            "label": "有道英式" if accent == "gb" else "有道美式",
            "url": f"https://dict.youdao.com/dictvoice?{urlencode({'audio': word, 'type': primary_youdao_type})}",
        },
        {
            "key": f"youdao-{secondary_youdao_type}",
            "label": "有道备用",
            "url": f"https://dict.youdao.com/dictvoice?{urlencode({'audio': word, 'type': secondary_youdao_type})}",
        },
        {
            "key": f"google-{google_lang.lower()}",
            "label": "Google 英式" if accent == "gb" else "Google 美式",
            "url": "https://translate.google.com/translate_tts?"
            + urlencode({"ie": "UTF-8", "client": "tw-ob", "q": word, "tl": google_lang}),
        },
    ]


async def audio_candidates_with_dictionary(word: str, accent: str) -> list[dict]:
    candidates = audio_candidates(word, accent)
    try:
        american_audio, british_audio = await FreeDictionaryAudioClient().lookup_audio(word)
        dictionary_url = british_audio if accent == "gb" else american_audio
        if dictionary_url:
            candidates.insert(
                0,
                {
                    "key": "free-dictionary",
                    "label": "Free Dictionary",
                    "url": dictionary_url,
                },
            )
    except Exception:
        pass
    return candidates


async def store_audio_candidate(word: str, accent: str, source_key: str, audio_url: str, audio_dir: Path) -> str | None:
    if not audio_url or is_local_audio_url(audio_url):
        return audio_url

    audio_dir.mkdir(parents=True, exist_ok=True)
    safe_word = re.sub(r"[^a-zA-Z0-9_-]+", "-", word.lower()).strip("-") or "word"
    safe_source = re.sub(r"[^a-zA-Z0-9_-]+", "-", source_key.lower()).strip("-") or "source"
    target = audio_dir / f"{safe_word}-{accent}-{safe_source}.mp3"

    async with httpx.AsyncClient(timeout=20, headers=AUDIO_HEADERS, follow_redirects=True) as client:
        response = await client.get(audio_url)
        response.raise_for_status()
        content = response.content

    if len(content) < 1000:
        return None

    target.write_bytes(content)
    return f"/media/audio/{target.name}"


async def store_first_available_audio(word: str, accent: str, audio_dir: Path) -> str | None:
    for candidate in await audio_candidates_with_dictionary(word, accent):
        try:
            local_url = await store_audio_candidate(word, accent, candidate["key"], candidate["url"], audio_dir)
            if local_url:
                return local_url
        except Exception:
            continue
    return None
