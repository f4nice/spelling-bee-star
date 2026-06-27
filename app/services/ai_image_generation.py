import base64
from datetime import datetime, timezone
import hashlib
import hmac
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.parse import urlparse

import httpx
from PIL import Image, ImageDraw, ImageFilter, ImageFont


TENCENT_AIART_ENDPOINT = "https://aiart.tencentcloudapi.com"
TENCENT_AIART_HOST = "aiart.tencentcloudapi.com"
TENCENT_AIART_SERVICE = "aiart"
TENCENT_AIART_VERSION = "2022-12-29"
DASHSCOPE_IMAGE_MODELS = {
    "wan2.7-image-pro",
    "qwen-image-2.0-pro",
    "wan2.6-t2i",
}
DASHSCOPE_ASYNC_IMAGE_ENDPOINT = "https://dashscope.aliyuncs.com/api/v1/services/aigc/image-generation/generation"
DASHSCOPE_MULTIMODAL_ENDPOINT = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
CHINESE_FONT_PATHS = [
    "C:/Windows/Fonts/STZHONGS.TTF",
    "C:/Windows/Fonts/simkai.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSerifCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
]
CARD_TITLE_FONT_PATHS = [
    "C:/Windows/Fonts/STZHONGS.TTF",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simkai.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSerifCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
]


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
    selected_meaning = _short_meaning(chinese_definition) or (chinese_definition or "").strip()
    prompt_parts = [
        "A clear educational square background image for an English vocabulary learning app.",
        f"Visual concept: {selected_meaning or word}.",
        "Use the visual concept as the primary subject.",
        f"The English vocabulary word is {word}, but it is metadata only and must not appear as text.",
        "Child-safe, clean, bright, centered main subject, high quality.",
        "Generate a pure picture background only.",
        "Do not include any text, letters, Chinese characters, captions, signs, labels, book pages, logos, watermarks, UI elements, or typography in the image.",
        "Leave all wording to be added later by the application.",
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
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _load_card_title_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in CARD_TITLE_FONT_PATHS:
        try:
            return ImageFont.truetype(path, size=size)
        except OSError:
            continue
    return _load_font(size, bold=True)


def _has_chinese_font() -> bool:
    return any(Path(path).exists() for path in CHINESE_FONT_PATHS)


def ensure_chinese_font() -> None:
    if _has_chinese_font() or os.name == "nt":
        return
    if hasattr(os, "geteuid") and os.geteuid() != 0:
        return
    apt_get = "/usr/bin/apt-get"
    if not Path(apt_get).exists():
        return
    try:
        subprocess.run([apt_get, "update", "-qq"], check=False, timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(
            [apt_get, "install", "-y", "-qq", "fontconfig", "fonts-wqy-microhei"],
            check=False,
            timeout=180,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.SubprocessError):
        return


def _fit_font(text: str, max_width: int, start_size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    size = start_size
    while size >= 24:
        font = _load_font(size, bold=bold)
        bbox = ImageDraw.Draw(Image.new("RGB", (10, 10))).textbbox((0, 0), text, font=font)
        if bbox[2] - bbox[0] <= max_width:
            return font
        size -= 4
    return _load_font(24, bold=bold)


def _fit_card_title_font(text: str, max_width: int, start_size: int) -> ImageFont.ImageFont:
    size = start_size
    while size >= 40:
        font = _load_card_title_font(size)
        bbox = ImageDraw.Draw(Image.new("RGB", (10, 10))).textbbox((0, 0), text, font=font, stroke_width=8)
        if bbox[2] - bbox[0] <= max_width:
            return font
        size -= 5
    return _load_card_title_font(40)


def _paint_bottom_readability_gradient(overlay: Image.Image) -> None:
    width, height = overlay.size
    gradient_height = int(height * 0.36)
    start_y = height - gradient_height
    gradient = Image.new("RGBA", (width, gradient_height), (0, 0, 0, 0))
    grad_draw = ImageDraw.Draw(gradient)
    for y in range(gradient_height):
        progress = y / max(1, gradient_height - 1)
        alpha = int(108 * (progress**1.8))
        grad_draw.line((0, y, width, y), fill=(34, 18, 9, alpha))
    overlay.alpha_composite(gradient, (0, start_y))


def _draw_reference_style_title(
    overlay: Image.Image,
    text: str,
    *,
    canvas_size: int = 1024,
) -> None:
    draw = ImageDraw.Draw(overlay)
    font = _fit_card_title_font(text, 900, 122)
    stroke_width = 8
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (canvas_size - text_width) // 2 - bbox[0]
    y = canvas_size - text_height - 68 - bbox[1]

    shadow = Image.new("RGBA", overlay.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.text(
        (x + 5, y + 8),
        text,
        font=font,
        fill=(56, 28, 12, 220),
        stroke_width=stroke_width + 2,
        stroke_fill=(56, 28, 12, 220),
    )
    overlay.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(radius=4)))

    for dx, dy, alpha in [(0, 5, 150), (3, 7, 120), (-3, 7, 100)]:
        draw.text(
            (x + dx, y + dy),
            text,
            font=font,
            fill=(86, 44, 18, alpha),
            stroke_width=stroke_width,
            stroke_fill=(86, 44, 18, alpha),
        )
    draw.text(
        (x, y),
        text,
        font=font,
        fill=(255, 252, 244, 255),
        stroke_width=stroke_width,
        stroke_fill=(97, 55, 30, 238),
    )


def compose_word_card_image(
    image_bytes: bytes,
    *,
    word: str,
    chinese_definition: str | None = None,
) -> bytes:
    ensure_chinese_font()
    image = Image.open(BytesIO(image_bytes)).convert("RGB")
    image.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (1024, 1024), (244, 248, 245))
    left = (1024 - image.width) // 2
    top = (1024 - image.height) // 2
    canvas.paste(image, (left, top))

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    meaning_text = _short_meaning(chinese_definition)
    if meaning_text:
        _paint_bottom_readability_gradient(overlay)
        _draw_reference_style_title(overlay, meaning_text)

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
    choices = output.get("choices")
    if isinstance(choices, list) and choices:
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            content = ((choice.get("message") or {}).get("content") or [])
            if not isinstance(content, list):
                continue
            for item in content:
                if not isinstance(item, dict):
                    continue
                url = item.get("image") or item.get("url") or item.get("image_url")
                if url:
                    return str(url)
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


def _dashscope_endpoint_for_model(model: str, configured_endpoint: str) -> str:
    endpoint = (configured_endpoint or "").strip()
    if model == "wan2.7-image-pro":
        if "image-generation/generation" in endpoint:
            return endpoint
        return DASHSCOPE_ASYNC_IMAGE_ENDPOINT
    if "multimodal-generation/generation" in endpoint:
        return endpoint
    return DASHSCOPE_MULTIMODAL_ENDPOINT


def _dashscope_payload_for_model(model: str, prompt: str) -> tuple[dict, bool]:
    message_input = {
        "messages": [
            {
                "role": "user",
                "content": [{"text": prompt}],
            }
        ]
    }
    if model == "wan2.7-image-pro":
        return (
            {
                "model": model,
                "input": message_input,
                "parameters": {
                    "size": "1024*1024",
                    "n": 1,
                    "watermark": False,
                },
            },
            True,
        )
    if model == "wan2.6-t2i":
        return (
            {
                "model": model,
                "input": message_input,
                "parameters": {
                    "size": "1280*1280",
                    "n": 1,
                    "prompt_extend": True,
                    "watermark": False,
                    "negative_prompt": "text, letters, caption, watermark, logo, blurry, distorted words",
                },
            },
            False,
        )
    return (
        {
            "model": model,
            "input": message_input,
            "parameters": {
                "size": "2048*2048",
                "n": 1,
                "prompt_extend": True,
                "watermark": False,
                "negative_prompt": "Low resolution, low quality, blurry, watermark, logo, distorted text, malformed objects.",
            },
        },
        False,
    )


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
    prompt = build_word_image_prompt(
        word=word,
        english_definition=english_definition,
        chinese_definition=chinese_definition,
        theme=theme,
        style=style,
    )
    image_content = await generate_dashscope_prompt_image(
        api_key=api_key,
        endpoint=endpoint,
        task_endpoint=task_endpoint,
        poll_seconds=poll_seconds,
        timeout_seconds=timeout_seconds,
        model=model,
        prompt=prompt,
    )
    return compose_word_card_image(
        image_content,
        word=word,
        chinese_definition=chinese_definition,
    )


async def generate_dashscope_prompt_image(
    *,
    api_key: str,
    endpoint: str,
    task_endpoint: str,
    poll_seconds: float,
    timeout_seconds: int,
    model: str,
    prompt: str,
) -> bytes:
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is not configured on the server.")
    selected_model = model if model in DASHSCOPE_IMAGE_MODELS else "wan2.7-image-pro"
    payload, is_async = _dashscope_payload_for_model(selected_model, prompt)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if is_async:
        headers["X-DashScope-Async"] = "enable"
    request_endpoint = _dashscope_endpoint_for_model(selected_model, endpoint)
    async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
        response = await client.post(request_endpoint, headers=headers, json=payload)
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
        return image_response.content


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
