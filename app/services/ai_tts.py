import re
from pathlib import Path
from uuid import uuid4

import httpx


OPENAI_SPEECH_URL = "https://api.openai.com/v1/audio/speech"
SUPPORTED_AUDIO_FORMATS = {"mp3", "wav", "pcm"}


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


async def generate_aliyun_word_audio(
    *,
    appkey: str,
    token: str,
    gateway: str,
    word: str,
    accent: str,
    audio_dir: Path,
    audio_format: str,
    sample_rate: int,
    voice_us: str,
    voice_gb: str,
    volume: int,
    speech_rate: int,
    pitch_rate: int,
) -> str:
    if not appkey:
        raise RuntimeError("ALIYUN_NLS_APPKEY is not configured on the server.")
    if not token:
        raise RuntimeError("ALIYUN_NLS_TOKEN is not configured on the server.")

    normalized_format = (audio_format or "mp3").lower()
    if normalized_format not in SUPPORTED_AUDIO_FORMATS:
        raise RuntimeError(f"ALIYUN_TTS_FORMAT '{audio_format}' is not supported.")

    params = {
        "appkey": appkey,
        "token": token,
        "text": word,
        "format": normalized_format,
        "sample_rate": sample_rate,
        "volume": volume,
        "speech_rate": speech_rate,
        "pitch_rate": pitch_rate,
    }
    voice = voice_gb if accent == "gb" else voice_us
    if voice:
        params["voice"] = voice

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(gateway, params=params)
        response.raise_for_status()
        content = response.content

    content_type = (response.headers.get("content-type") or "").lower()
    if "json" in content_type or content[:1] == b"{":
        message = content.decode("utf-8", errors="ignore")[:400]
        raise RuntimeError(f"阿里云语音合成失败: {message}")
    if len(content) < 1000:
        raise RuntimeError("阿里云语音合成返回的音频太短，请稍后重试。")

    audio_dir.mkdir(parents=True, exist_ok=True)
    target = audio_dir / f"{_safe_word_slug(word)}-{accent}-aliyun-{uuid4().hex[:8]}.{normalized_format}"
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
    aliyun_appkey: str = "",
    aliyun_token: str = "",
    aliyun_gateway: str = "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/tts",
    aliyun_format: str = "mp3",
    aliyun_sample_rate: int = 16000,
    aliyun_voice_us: str = "",
    aliyun_voice_gb: str = "",
    aliyun_volume: int = 50,
    aliyun_speech_rate: int = 0,
    aliyun_pitch_rate: int = 0,
) -> str:
    if provider == "openai":
        return await generate_openai_word_audio(
            api_key=api_key,
            model=model,
            voice=voice_gb if accent == "gb" else voice_us,
            word=word,
            accent=accent,
            audio_dir=audio_dir,
        )
    if provider == "aliyun":
        return await generate_aliyun_word_audio(
            appkey=aliyun_appkey,
            token=aliyun_token,
            gateway=aliyun_gateway,
            word=word,
            accent=accent,
            audio_dir=audio_dir,
            audio_format=aliyun_format,
            sample_rate=aliyun_sample_rate,
            voice_us=aliyun_voice_us,
            voice_gb=aliyun_voice_gb,
            volume=aliyun_volume,
            speech_rate=aliyun_speech_rate,
            pitch_rate=aliyun_pitch_rate,
        )
    raise RuntimeError(f"AI_TTS_PROVIDER '{provider}' is not supported.")
