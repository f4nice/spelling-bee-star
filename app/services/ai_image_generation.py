import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
from urllib.parse import urlparse

import httpx


TENCENT_AIART_ENDPOINT = "https://aiart.tencentcloudapi.com"
TENCENT_AIART_HOST = "aiart.tencentcloudapi.com"
TENCENT_AIART_SERVICE = "aiart"
TENCENT_AIART_VERSION = "2022-12-29"


def build_word_image_prompt(
    *,
    word: str,
    english_definition: str | None = None,
    chinese_definition: str | None = None,
) -> str:
    prompt_parts = [
        "A clear educational square image for an English vocabulary learning app.",
        f"Vocabulary word: {word}.",
        "Show the concrete meaning or a memorable visual metaphor for this word.",
        "Child-safe, clean, bright, centered main subject, high quality illustration or photo style.",
        "No text, no letters, no captions, no watermark, no logo, no UI elements.",
    ]
    if english_definition:
        prompt_parts.append(f"English definition: {english_definition}")
    if chinese_definition:
        prompt_parts.append(f"Chinese meaning: {chinese_definition}")
    return " ".join(prompt_parts)


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
) -> bytes:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "prompt": build_word_image_prompt(
            word=word,
            english_definition=english_definition,
            chinese_definition=chinese_definition,
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
) -> bytes:
    payload = {
        "Prompt": build_word_image_prompt(
            word=word,
            english_definition=english_definition,
            chinese_definition=chinese_definition,
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


async def generate_word_image(
    *,
    provider: str,
    word: str,
    english_definition: str | None = None,
    chinese_definition: str | None = None,
    openai_api_key: str = "",
    openai_model: str = "gpt-image-1",
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
    )
