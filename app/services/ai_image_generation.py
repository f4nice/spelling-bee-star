import base64
from datetime import datetime, timezone
import hashlib
import hmac
from io import BytesIO
import json
import time
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageDraw, ImageFont


TENCENT_AIART_ENDPOINT = "https://aiart.tencentcloudapi.com"
TENCENT_AIART_HOST = "aiart.tencentcloudapi.com"
TENCENT_AIART_SERVICE = "aiart"
TENCENT_AIART_VERSION = "2022-12-29"
DASHSCOPE_IMAGE_MODELS = {
    "wan2.7-image-pro",
    "qwen-image-2.0-pro",
    "wan2.6-t2i",
}


def build_word_image_prompt(
    *,
    word: str,
    english_definition: str | None = None,
    chinese_definition: str | None = None,
    theme: str | None = None,
    style: str | None = None,
) -> str:
    selected_theme = (theme or "").strip()
    selected_style = (style or "").strip()
    prompt_parts = [
        "A clear educational square background image for an English vocabulary learning app.",
        f"Vocabulary word: {word}.",
        "Show the concrete meaning or a memorable visual metaphor for this word.",
        "Child-safe, clean, bright, centered main subject, high quality.",
        "No text, no letters, no captions, no watermark, no logo, no UI elements.",
    ]
    if selected_theme:
        prompt_parts.append(f"Theme: {selected_theme}.")
    if selected_style:
        prompt_parts.append(f"Visual style: {selected_style}.")
    if english_definition:
        prompt_parts.append(f"English definition: {english_definition}")
    if chinese_definition:
        prompt_parts.append(f"Chinese meaning: {chinese_definition}")
    return " ".join(prompt_parts)


def _short_meaning(chinese_definition: str | None) -> str:
    if not chinese_definition:
        return ""
    text = " ".join(str(chinese_definition).split())
    for mark in ["；", ";", "。", ".", "，", ",", "（", "("]:
        if mark in text:
            text = text.split(mark, 1)[0]
    return text.strip()[:18]


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _fit_font(text: str, max_width: int, start_size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    size = start_size
    while size >= 24:
        font = _load_font(size, bold=bold)
        bbox = ImageDraw.Draw(Image.new("RGB", (10, 10))).textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
        size -= 4
    return _load_font(24, bold=bold)


def compose_word_card_image(
    image_bytes: bytes,
    *,
    word: str,
    chinese_definition: str | None = None,
) -> bytes:
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (1024, 1024), (244, 248, 245))
    left = (1024 - image.width) // 2
    top = (1024 - image.height) // 2
    canvas.paste(image, (left, top))

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    panel_height = 230
    draw.rounded_rectangle(
        (54, 1024 - panel_height - 52, 970, 972),
        radius=34,
        fill=(255, 255, 255, 218),
    )
    draw.rounded_rectangle(
        (54, 1024 - panel_height - 52, 970, 972),
        radius=34,
        outline=(17, 103, 79, 96),
        width=4,
    )
    word_text = str(word or "").strip()
    meaning_text = _short_meaning(chinese_definition)
    word_font = _fit_font(word_text, 820, 96, bold=True)
    meaning_font = _fit_font(meaning_text, 820, 52, bold=True)

    word_bbox = draw.textbbox((0, 0), word_text, font=word_font)
    word_x = (1024 - (word_bbox[2] - word_bbox[0])) // 2
    draw.text((word_x, 742), word_text, font=word_font, fill=(16, 93, 76, 255))
    if meaning_text:
        meaning_bbox = draw.textbbox((0, 0), meaning_text, font=meaning_font)
        meaning_x = (1024 - (meaning_bbox[2] - meaning_bbox[0])) // 2
        draw.text((meaning_x, 852), meaning_text, font=meaning_font, fill=(31, 41, 55, 255))

    canvas = Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")
    output = BytesIO()
    canvas.save(output, format="JPEG", quality=92, optimize=True)
    return output.getvalue()


def _sign_tencent_payload(secret_key: str, date: str, payload_hash: str) -> bytes:
    secret_date = hmac.new(("TC3" + secret_key).encode("utf-8"), date.encode("utf-8"), hashlib.sha256).digest()
    secret_service = hmac.new(secret_date, TENCENT_AIART_SERVICE.encode("utf-8"), hashlib.sha256).digest()
    return hmac.new(secret_service, b"tc3_request", hashlib.sha256).digest()


def _tencent_auth_headers(
    *,
    secret_id: str,
    secret_key: str,
    action: str,
    payload: dict,
    region: str,
) -> tuple[dict[str, str], str]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    timestamp = int(datetime.now(timezone.utc).timestamp())
    request_time = datetime.fromtimestamp(timestamp, timezone.utc)
    date = request_time.strftime("%Y-%m-%d")

    http_request_method = "POST"
    canonical_uri = "/"
    canonical_querystring = ""
    canonical_headers = f"content-type:application/json; charset=utf-8\nhost:{TENCENT_AIART_HOST}\nx-tc-action:{action.lower()}\n"
    signed_headers = "content-type;host;x-tc-action"
    hashed_request_payload = hashlib.sha256(body.encode("utf-8")).hexdigest()
    canonical_request = "\n".join(
        [
            http_request_method,
            canonical_uri,
            canonical_querystring,
            canonical_headers,
            signed_headers,
            hashed_request_payload,
        ]
    )

    algorithm = "TC3-HMAC-SHA256"
    credential_scope = f"{date}/{TENCENT_AIART_SERVICE}/tc3_request"
    string_to_sign = "\n".join(
        [
            algorithm,
            str(timestamp),
            credential_scope,
            hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
        ]
    )
    signature = hmac.new(
        _sign_tencent_payload(secret_key, date, hashed_request_payload),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    authorization = (
        f"{algorithm} Credential={secret_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json; charset=utf-8",
        "Host": TENCENT_AIART_HOST,
        "X-TC-Action": action,
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Version": TENCENT_AIART_VERSION,
        "X-TC-Region": region,
    }
    return headers, body


async def generate_openai_word_image(
    *,
    api_key: str,
    model: str,
    word: str,
    english_definition: str | None = None,
    chinese_definition: str | None = None,
    theme: str | None = None,
    style: str | None = None,
) -> bytes:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "prompt": build_word_image_prompt(
            word=word,
            english_definition=english_definition,
            chinese_definition=chinese_definition,
            theme=theme,
            style=style,
        ),
        "size": "1024x1024",
    }
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post("https://api.openai.com/v1/images/generations", headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    image_data = (data.get("data") or [{}])[0]
    b64_json = image_data.get("b64_json")
    if not b64_json:
        raise RuntimeError("OpenAI image API did not return image data")
    return base64.b64decode(b64_json)


async def generate_tencent_hunyuan_word_image(
    *,
    secret_id: str,
    secret_key: str,
    region: str,
    action: str,
    word: str,
    english_definition: str | None = None,
    chinese_definition: str | None = None,
    theme: str | None = None,
    style: str | None = None,
) -> bytes:
    payload = {
        "Prompt": build_word_image_prompt(
            word=word,
            english_definition=english_definition,
            chinese_definition=chinese_definition,
            theme=theme,
            style=style,
        ),
        "RspImgType": "url",
    }
    if action == "TextToImageRapid":
        payload["Resolution"] = "768:768"
    headers, body = _tencent_auth_headers(
        secret_id=secret_id,
        secret_key=secret_key,
        action=action,
        payload=payload,
        region=region,
    )

    async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
        response = await client.post(TENCENT_AIART_ENDPOINT, headers=headers, content=body.encode("utf-8"))
        response.raise_for_status()
        data = response.json()
        if error := (data.get("Response") or {}).get("Error"):
            raise RuntimeError(f"{error.get('Code')}: {error.get('Message')}")

        result_image = (data.get("Response") or {}).get("ResultImage")
        if not result_image:
            raise RuntimeError("Tencent Hunyuan image API did not return ResultImage")

        parsed = urlparse(result_image)
        if parsed.scheme in {"http", "https"}:
            image_response = await client.get(result_image)
            image_response.raise_for_status()
            return image_response.content

    return base64.b64decode(result_image)


def _dashscope_image_url(data: dict) -> str:
    output = data.get("output") if isinstance(data, dict) else {}
    if not isinstance(output, dict):
        return ""
    for key in ("results", "images"):
        items = output.get(key)
        if isinstance(items, list) and items:
            first = items[0] if isinstance(items[0], dict) else {}
            url = first.get("url") or first.get("image_url") or first.get("orig_url")
            if url:
                return str(url)
    for key in ("url", "image_url"):
        if output.get(key):
            return str(output[key])
    return ""


async def generate_dashscope_word_image(
    *,
    api_key: str,
    endpoint: str,
    task_endpoint: str,
    poll_seconds: float,
    timeout_seconds: int,
    model: str,
    word: str,
    english_definition: str | None = None,
    chinese_definition: str | None = None,
    theme: str | None = None,
    style: str | None = None,
) -> bytes:
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is not configured on the server.")
    selected_model = model if model in DASHSCOPE_IMAGE_MODELS else "wan2.7-image-pro"
    prompt = build_word_image_prompt(
        word=word,
        english_definition=english_definition,
        chinese_definition=chinese_definition,
        theme=theme,
        style=style,
    )
    payload = {
        "model": selected_model,
        "input": {
            "prompt": prompt,
            "negative_prompt": "text, letters, caption, watermark, logo, blurry, distorted words",
        },
        "parameters": {
            "size": "1024*1024",
            "n": 1,
        },
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
        response = await client.post(endpoint, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        task_id = ((data.get("output") or {}).get("task_id") or data.get("task_id") or "").strip()
        image_url = _dashscope_image_url(data)
        deadline = time.monotonic() + timeout_seconds
        while not image_url and task_id and time.monotonic() < deadline:
            await asyncio_sleep(poll_seconds)
            task_response = await client.get(f"{task_endpoint.rstrip('/')}/{task_id}", headers={"Authorization": f"Bearer {api_key}"})
            task_response.raise_for_status()
            task_data = task_response.json()
            task_status = str((task_data.get("output") or {}).get("task_status") or "").upper()
            if task_status in {"FAILED", "CANCELED", "UNKNOWN"}:
                message = (task_data.get("output") or {}).get("message") or task_response.text[:300]
                raise RuntimeError(f"DashScope image task failed: {message}")
            image_url = _dashscope_image_url(task_data)
        if not image_url:
            raise RuntimeError("DashScope image API did not return an image URL.")
        image_response = await client.get(image_url)
        image_response.raise_for_status()
        return compose_word_card_image(
            image_response.content,
            word=word,
            chinese_definition=chinese_definition,
        )


async def asyncio_sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(max(0.2, seconds))


async def generate_word_image(
    *,
    provider: str,
    word: str,
    english_definition: str | None = None,
    chinese_definition: str | None = None,
    theme: str | None = None,
    style: str | None = None,
    openai_api_key: str = "",
    openai_model: str = "gpt-image-1",
    dashscope_api_key: str = "",
    dashscope_endpoint: str = "",
    dashscope_task_endpoint: str = "",
    dashscope_poll_seconds: float = 2.0,
    dashscope_timeout_seconds: int = 180,
    dashscope_model: str = "wan2.7-image-pro",
    tencent_secret_id: str = "",
    tencent_secret_key: str = "",
    tencent_region: str = "ap-guangzhou",
    tencent_action: str = "TextToImageRapid",
) -> bytes:
    if provider == "openai":
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured on the server.")
        return await generate_openai_word_image(
            api_key=openai_api_key,
            model=openai_model,
            word=word,
            english_definition=english_definition,
            chinese_definition=chinese_definition,
            theme=theme,
            style=style,
        )

    if provider == "dashscope":
        return await generate_dashscope_word_image(
            api_key=dashscope_api_key,
            endpoint=dashscope_endpoint,
            task_endpoint=dashscope_task_endpoint,
            poll_seconds=dashscope_poll_seconds,
            timeout_seconds=dashscope_timeout_seconds,
            model=dashscope_model,
            word=word,
            english_definition=english_definition,
            chinese_definition=chinese_definition,
            theme=theme,
            style=style,
        )

    if not tencent_secret_id or not tencent_secret_key:
        raise RuntimeError("TENCENTCLOUD_SECRET_ID and TENCENTCLOUD_SECRET_KEY are not configured on the server.")
    return await generate_tencent_hunyuan_word_image(
        secret_id=tencent_secret_id,
        secret_key=tencent_secret_key,
        region=tencent_region,
        action=tencent_action,
        word=word,
        english_definition=english_definition,
        chinese_definition=chinese_definition,
        theme=theme,
        style=style,
    )
