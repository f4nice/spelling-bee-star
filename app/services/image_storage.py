from io import BytesIO
import re
from pathlib import Path

import httpx
from PIL import Image, ImageOps


IMAGE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; SpellingBeeStar/1.0; +https://github.com/f4nice/spelling-bee-star)",
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
}


def is_local_media_url(url: str | None) -> bool:
    return bool(url and url.startswith("/media/images/"))


async def store_word_image(word: str, image_url: str, image_dir: Path) -> str | None:
    if not image_url or is_local_media_url(image_url):
        return image_url

    image_dir.mkdir(parents=True, exist_ok=True)
    safe_word = re.sub(r"[^a-zA-Z0-9_-]+", "-", word.lower()).strip("-") or "word"
    target = image_dir / f"{safe_word}.webp"

    async with httpx.AsyncClient(timeout=30, headers=IMAGE_HEADERS, follow_redirects=True) as client:
        response = await client.get(image_url)
        response.raise_for_status()

    with Image.open(BytesIO(response.content)) as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail((800, 800), Image.Resampling.LANCZOS)
        if image.mode in {"RGBA", "LA"}:
            background = Image.new("RGB", image.size, (255, 255, 255))
            background.paste(image, mask=image.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")
        image.save(target, format="WEBP", quality=76, method=6)

    return f"/media/images/{target.name}"
