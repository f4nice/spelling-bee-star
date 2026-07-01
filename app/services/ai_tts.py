import base64
from datetime import datetime, timezone
import hmac
import hashlib
import re
from pathlib import Path
from time import time
from typing import Any
from urllib.parse import quote
from uuid import uuid4

import httpx


OPENAI_SPEECH_URL = "https://api.openai.com/v1/audio/speech"
DASHSCOPE_TTS_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer"
DATAMUSE_WORDS_URL = "https://api.datamuse.com/words"
SUPPORTED_AUDIO_FORMATS = {"mp3", "wav", "pcm"}
ALIYUN_TOKEN_ACTION = "CreateToken"
ALIYUN_TOKEN_VERSION = "2019-02-28"
_ALIYUN_TOKEN_CACHE: dict[str, Any] = {"id": "", "expire_time": 0}


def _safe_word_slug(word: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", word.lower()).strip("-") or "word"


def _percent_encode(value: str) -> str:
    return quote(str(value), safe="~")


def _aliyun_token_signature(params: dict[str, str], access_key_secret: str) -> str:
    canonicalized_query = "&".join(
        f"{_percent_encode(key)}={_percent_encode(params[key])}"
        for key in sorted(params)
    )
    string_to_sign = f"GET&%2F&{_percent_encode(canonicalized_query)}"
    digest = hmac.new(
        f"{access_key_secret}&".encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


async def fetch_aliyun_nls_token(
    *,
    access_key_id: str,
    access_key_secret: str,
    region: str,
    endpoint: str,
) -> str:
    if not access_key_id:
        raise RuntimeError("ALIYUN_ACCESS_KEY_ID is not configured on the server.")
    if not access_key_secret:
        raise RuntimeError("ALIYUN_ACCESS_KEY_SECRET is not configured on the server.")

    cached_id = _ALIYUN_TOKEN_CACHE.get("id") or ""
    cached_expire_time = int(_ALIYUN_TOKEN_CACHE.get("expire_time") or 0)
    if cached_id and cached_expire_time - int(time()) > 300:
        return cached_id

    params = {
        "AccessKeyId": access_key_id,
        "Action": ALIYUN_TOKEN_ACTION,
        "Version": ALIYUN_TOKEN_VERSION,
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "Format": "JSON",
        "RegionId": region,
        "SignatureMethod": "HMAC-SHA1",
        "SignatureVersion": "1.0",
        "SignatureNonce": uuid4().hex,
    }
    params["Signature"] = _aliyun_token_signature(params, access_key_secret)

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(endpoint, params=params)
        response.raise_for_status()
        payload = response.json()

    token = payload.get("Token") or {}
    token_id = token.get("Id") or ""
    expire_time = int(token.get("ExpireTime") or 0)
    if not token_id:
        message = payload.get("Message") or payload.get("Code") or str(payload)[:400]
        raise RuntimeError(f"阿里云 Token 获取失败: {message}")

    _ALIYUN_TOKEN_CACHE["id"] = token_id
    _ALIYUN_TOKEN_CACHE["expire_time"] = expire_time
    return token_id


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
    voice_gender: str,
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
    target = audio_dir / f"{_safe_word_slug(word)}-{accent}-{voice_gender}-ai-{uuid4().hex[:8]}.mp3"
    target.write_bytes(content)
    return f"/media/audio/{target.name}"


def _escape_ssml_text(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _extract_cmu_pronunciation(payload: Any, word: str) -> str:
    if not isinstance(payload, list) or not payload:
        return ""
    normalized_word = (word or "").strip().lower()
    for item in payload:
        if not isinstance(item, dict):
            continue
        if normalized_word and str(item.get("word") or "").strip().lower() != normalized_word:
            continue
        for tag in item.get("tags") or []:
            tag_text = str(tag or "")
            if tag_text.startswith("pron:"):
                return re.sub(r"\s+", " ", tag_text.removeprefix("pron:")).strip()
    return ""


async def lookup_cmu_pronunciation(word: str) -> str:
    query_word = (word or "").strip()
    if not query_word:
        return ""
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            DATAMUSE_WORDS_URL,
            params={"sp": query_word, "qe": "sp", "md": "r", "max": 1},
        )
        response.raise_for_status()
        return _extract_cmu_pronunciation(response.json(), query_word)


def build_cmu_phoneme_ssml(word: str, cmu_pronunciation: str) -> str:
    safe_word = _escape_ssml_text((word or "").strip())
    safe_pronunciation = _escape_ssml_text(re.sub(r"\s+", " ", cmu_pronunciation.strip()))
    return f'<speak><phoneme alphabet="cmu" ph="{safe_pronunciation}">{safe_word}</phoneme></speak>'


def _choose_dashscope_voice(*, voice_gender: str, voice_female: str, voice_male: str) -> str:
    if voice_gender == "male":
        return voice_male or "longanyang"
    return voice_female or "longyan_v3"


def _dashscope_audio_url(data: dict[str, Any]) -> str:
    output = data.get("output") or {}
    audio = output.get("audio") or {}
    for key in ("url", "audio_url"):
        if audio.get(key):
            return str(audio[key])
    if isinstance(output.get("url"), str):
        return str(output["url"])
    return ""


async def generate_dashscope_phoneme_audio(
    *,
    api_key: str,
    endpoint: str,
    model: str,
    word: str,
    accent: str,
    voice_gender: str,
    audio_dir: Path,
    voice_female: str,
    voice_male: str,
    audio_format: str,
    sample_rate: int,
) -> str:
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is not configured on the server.")

    normalized_format = (audio_format or "mp3").lower()
    if normalized_format not in SUPPORTED_AUDIO_FORMATS:
        raise RuntimeError(f"DASHSCOPE_TTS_FORMAT '{audio_format}' is not supported.")

    cmu_pronunciation = await lookup_cmu_pronunciation(word)
    if not cmu_pronunciation:
        raise RuntimeError("没有找到可用的 CMU 音标，暂时不能按音标生成朗读。")

    payload = {
        "model": model or "cosyvoice-v3-flash",
        "input": {
            "text": build_cmu_phoneme_ssml(word, cmu_pronunciation),
            "voice": _choose_dashscope_voice(
                voice_gender=voice_gender,
                voice_female=voice_female,
                voice_male=voice_male,
            ),
            "format": normalized_format,
            "sample_rate": sample_rate,
            "enable_ssml": True,
        },
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    request_endpoint = endpoint or DASHSCOPE_TTS_URL

    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(request_endpoint, headers=headers, json=payload)
        response.raise_for_status()
        response_data = response.json()
        audio_url = _dashscope_audio_url(response_data)
        if not audio_url:
            message = response_data.get("message") or response_data.get("code") or str(response_data)[:400]
            raise RuntimeError(f"阿里百炼音标朗读生成失败: {message}")
        audio_response = await client.get(audio_url)
        audio_response.raise_for_status()
        content = audio_response.content

    if len(content) < 1000:
        raise RuntimeError("阿里百炼音标朗读返回的音频太短，请稍后重试。")

    audio_dir.mkdir(parents=True, exist_ok=True)
    target = audio_dir / f"{_safe_word_slug(word)}-{accent}-{voice_gender}-phoneme-{uuid4().hex[:8]}.{normalized_format}"
    target.write_bytes(content)
    return f"/media/audio/{target.name}"


def _choose_aliyun_voice(
    *,
    accent: str,
    voice_gender: str,
    voice_us: str,
    voice_gb: str,
    voice_us_female: str,
    voice_us_male: str,
    voice_gb_female: str,
    voice_gb_male: str,
) -> str:
    if accent == "gb":
        if voice_gender == "male":
            return voice_gb_male or voice_gb or "david"
        return voice_gb_female or voice_gb or "beth"
    if voice_gender == "male":
        return voice_us_male or voice_us or "brian"
    return voice_us_female or voice_us or "betty"


async def generate_aliyun_word_audio(
    *,
    appkey: str,
    token: str,
    access_key_id: str,
    access_key_secret: str,
    token_region: str,
    token_endpoint: str,
    gateway: str,
    word: str,
    accent: str,
    voice_gender: str,
    audio_dir: Path,
    audio_format: str,
    sample_rate: int,
    voice_us: str,
    voice_gb: str,
    voice_us_female: str,
    voice_us_male: str,
    voice_gb_female: str,
    voice_gb_male: str,
    volume: int,
    speech_rate: int,
    pitch_rate: int,
) -> str:
    if not appkey:
        raise RuntimeError("ALIYUN_NLS_APPKEY is not configured on the server.")
    if not token:
        token = await fetch_aliyun_nls_token(
            access_key_id=access_key_id,
            access_key_secret=access_key_secret,
            region=token_region,
            endpoint=token_endpoint,
        )

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
    voice = _choose_aliyun_voice(
        accent=accent,
        voice_gender=voice_gender,
        voice_us=voice_us,
        voice_gb=voice_gb,
        voice_us_female=voice_us_female,
        voice_us_male=voice_us_male,
        voice_gb_female=voice_gb_female,
        voice_gb_male=voice_gb_male,
    )
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
    target = audio_dir / f"{_safe_word_slug(word)}-{accent}-{voice_gender}-aliyun-{uuid4().hex[:8]}.{normalized_format}"
    target.write_bytes(content)
    return f"/media/audio/{target.name}"


async def generate_word_ai_audio(
    *,
    provider: str,
    api_key: str,
    model: str,
    word: str,
    accent: str,
    voice_gender: str = "female",
    text_mode: str = "word",
    audio_dir: Path,
    voice_us: str,
    voice_gb: str,
    dashscope_api_key: str = "",
    dashscope_tts_endpoint: str = DASHSCOPE_TTS_URL,
    dashscope_tts_model: str = "cosyvoice-v3-flash",
    dashscope_tts_voice_female: str = "longyan_v3",
    dashscope_tts_voice_male: str = "longanyang",
    dashscope_tts_format: str = "mp3",
    dashscope_tts_sample_rate: int = 24000,
    aliyun_appkey: str = "",
    aliyun_token: str = "",
    aliyun_access_key_id: str = "",
    aliyun_access_key_secret: str = "",
    aliyun_token_region: str = "cn-shanghai",
    aliyun_token_endpoint: str = "https://nls-meta.cn-shanghai.aliyuncs.com/",
    aliyun_gateway: str = "https://nls-gateway-cn-shanghai.aliyuncs.com/stream/v1/tts",
    aliyun_format: str = "mp3",
    aliyun_sample_rate: int = 16000,
    aliyun_voice_us: str = "",
    aliyun_voice_gb: str = "",
    aliyun_voice_us_female: str = "",
    aliyun_voice_us_male: str = "",
    aliyun_voice_gb_female: str = "",
    aliyun_voice_gb_male: str = "",
    aliyun_volume: int = 50,
    aliyun_speech_rate: int = 0,
    aliyun_pitch_rate: int = 0,
) -> str:
    if text_mode == "phonetic":
        return await generate_dashscope_phoneme_audio(
            api_key=dashscope_api_key,
            endpoint=dashscope_tts_endpoint,
            model=dashscope_tts_model,
            word=word,
            accent=accent,
            voice_gender=voice_gender,
            audio_dir=audio_dir,
            voice_female=dashscope_tts_voice_female,
            voice_male=dashscope_tts_voice_male,
            audio_format=dashscope_tts_format,
            sample_rate=dashscope_tts_sample_rate,
        )
    if provider == "openai":
        return await generate_openai_word_audio(
            api_key=api_key,
            model=model,
            voice=voice_gb if accent == "gb" else voice_us,
            word=word,
            accent=accent,
            voice_gender=voice_gender,
            audio_dir=audio_dir,
        )
    if provider == "aliyun":
        return await generate_aliyun_word_audio(
            appkey=aliyun_appkey,
            token=aliyun_token,
            access_key_id=aliyun_access_key_id,
            access_key_secret=aliyun_access_key_secret,
            token_region=aliyun_token_region,
            token_endpoint=aliyun_token_endpoint,
            gateway=aliyun_gateway,
            word=word,
            accent=accent,
            voice_gender=voice_gender,
            audio_dir=audio_dir,
            audio_format=aliyun_format,
            sample_rate=aliyun_sample_rate,
            voice_us=aliyun_voice_us,
            voice_gb=aliyun_voice_gb,
            voice_us_female=aliyun_voice_us_female,
            voice_us_male=aliyun_voice_us_male,
            voice_gb_female=aliyun_voice_gb_female,
            voice_gb_male=aliyun_voice_gb_male,
            volume=aliyun_volume,
            speech_rate=aliyun_speech_rate,
            pitch_rate=aliyun_pitch_rate,
        )
    raise RuntimeError(f"AI_TTS_PROVIDER '{provider}' is not supported.")
