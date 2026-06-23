import re
from pathlib import Path
from uuid import uuid4

import httpx


OPENAI_SPEECH_URL = "https://api.openai.com/v1/audio/speech"


def _safe_word_slug(word: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", word.lower()).strip("-") or "word"


def _accent_instruction(accent: str) -> str:
    if accent == "gb":
        return (
            "Read this single English vocabulary word clearly in a natural British English accent. "
            "Pronounce only the word, with no explanation, no spelling, and no extra words."
        )
    return (
        "Read this single English vocabulary word clearly in a natural American English accent. "
        "Pronounce only the word, with no explanation, no spelling, and no extra words."
    )


async def generate_openai_word_audio(
    *,
    api_key: str,
    model: str,
    voice: str,
    word: str,
    accent: str,
    audio_dir: Path,
) -> str:
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured on the server.")

    payload = {
        "model": model,
        "voice": voice,
        "input": word,
        "instructions": _accent_instruction(accent),
        "response_format": "mp3",
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(OPENAI_SPEECH_URL, headers=headers, json=payload)
        response.raise_for_status()
        content = response.content

    if len(content) < 1000:
        raise RuntimeError("AI 朗读返回的音频太短，请稍后重试。")

    audio_dir.mkdir(parents=True, exist_ok=True)
    target = audio_dir / f"{_safe_word_slug(word)}-{accent}-ai-{uuid4().hex[:8]}.mp3"
    target.write_bytes(content)
    return f"/media/audio/{target.name}"


async def generate_word_ai_audio(
    *,
    provider: str,
    api_key: str,
    model: str,
    word: str,
    accent: str,
    audio_dir: Path,
    voice_us: str,
    voice_gb: str,
) -> str:
    if provider != "openai":
        raise RuntimeError(f"AI_TTS_PROVIDER '{provider}' is not supported.")

    return await generate_openai_word_audio(
        api_key=api_key,
        model=model,
        voice=voice_gb if accent == "gb" else voice_us,
        word=word,
        accent=accent,
        audio_dir=audio_dir,
    )
