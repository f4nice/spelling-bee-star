import httpx
from urllib.parse import quote_plus


class ImageClient:
    async def find_image(self, word: str) -> str | None:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": word,
            "gsrlimit": 1,
            "prop": "pageimages",
            "piprop": "thumbnail",
            "pithumbsize": 800,
            "format": "json",
            "origin": "*",
        }
        headers = {
            "User-Agent": "SpellingBeeStar/1.0 (https://github.com/f4nice/spelling-bee-star; contact: f4nice@example.com)"
        }
        async with httpx.AsyncClient(timeout=20, headers=headers) as client:
            try:
                response = await client.get("https://commons.wikimedia.org/w/api.php", params=params)
                response.raise_for_status()
                data = response.json()
                pages = (data.get("query") or {}).get("pages") or {}
                for page in pages.values():
                    thumbnail = page.get("thumbnail") or {}
                    if thumbnail.get("source"):
                        return thumbnail["source"]
            except Exception:
                pass
        return f"https://loremflickr.com/800/800/{quote_plus(word)}"
