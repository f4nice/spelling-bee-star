import httpx
from urllib.parse import quote_plus


class ImageClient:
    async def find_images(self, word: str, limit: int = 8) -> list[dict[str, str]]:
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": word,
            "gsrlimit": max(1, min(limit, 12)),
            "prop": "pageimages",
            "piprop": "thumbnail",
            "pithumbsize": 800,
            "format": "json",
            "origin": "*",
        }
        headers = {
            "User-Agent": "SpellingBeeStar/1.0 (https://github.com/f4nice/spelling-bee-star; contact: f4nice@example.com)"
        }
        results: list[dict[str, str]] = []
        async with httpx.AsyncClient(timeout=6, headers=headers) as client:
            try:
                response = await client.get("https://commons.wikimedia.org/w/api.php", params=params)
                response.raise_for_status()
                data = response.json()
                pages = (data.get("query") or {}).get("pages") or {}
                for page in pages.values():
                    thumbnail = page.get("thumbnail") or {}
                    source = thumbnail.get("source")
                    if source:
                        results.append(
                            {
                                "url": source,
                                "title": page.get("title") or word,
                                "source": "Wikimedia Commons",
                            }
                        )
            except Exception:
                pass

        if not results:
            results.append(
                {
                    "url": f"https://loremflickr.com/800/800/{quote_plus(word)}",
                    "title": word,
                    "source": "LoremFlickr",
                }
            )
        return results

    async def find_image(self, word: str) -> str | None:
        images = await self.find_images(word, limit=1)
        return images[0]["url"] if images else None
