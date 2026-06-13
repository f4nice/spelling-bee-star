import httpx

from app.config import Settings


class TranslationClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def translate_definition(self, text: str | None) -> str | None:
        if not text:
            return None
        provider = self.settings.translation_provider.lower().strip()
        if provider == "none":
            return None
        if provider == "libretranslate":
            return await self._libretranslate(text)
        return await self._mymemory(text)

    async def _mymemory(self, text: str) -> str | None:
        params = {"q": text, "langpair": "en|zh-CN"}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get("https://api.mymemory.translated.net/get", params=params)
            response.raise_for_status()
            data = response.json()
        translated = (data.get("responseData") or {}).get("translatedText")
        return translated.strip() if translated else None

    async def _libretranslate(self, text: str) -> str | None:
        if not self.settings.libretranslate_url:
            return None
        payload = {
            "q": text,
            "source": "en",
            "target": "zh",
            "format": "text",
        }
        if self.settings.libretranslate_api_key:
            payload["api_key"] = self.settings.libretranslate_api_key
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(self.settings.libretranslate_url.rstrip("/") + "/translate", json=payload)
            response.raise_for_status()
            data = response.json()
        translated = data.get("translatedText")
        return translated.strip() if translated else None
