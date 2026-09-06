"""Last-resort public dictionary definitions, with exact headword validation."""
from urllib.parse import quote

import httpx

from app.services.dictionary import DictionaryEntry
from app.services.web_dictionary import _Tree


def parse_wordnik_entry(html, word, source_url):
    tree = _Tree()
    tree.feed(html)
    head = next((node for node in tree.root.tags("h1") if node.attrs.get("id") == "headword"), None)
    normalize = lambda value: " ".join(value.casefold().split())
    if not head or normalize(head.text()) != normalize(word):
        raise RuntimeError("备用词典返回的词条不匹配。")
    definitions = next((node for node in tree.root.tags("div") if node.attrs.get("id") == "define"), None)
    if definitions:
        for item in definitions.tags("li"):
            pos_node = next((node for node in item.tags("abbr") if node.attrs.get("title") == "partOfSpeech"), None)
            pos = " ".join(pos_node.text().split()) if pos_node else None
            text = " ".join(item.text().split())
            if pos and text.startswith(pos):
                text = text[len(pos):].strip()
            if not text or text.startswith("Sorry,"):
                continue
            return DictionaryEntry(
                part_of_speech=pos,
                english_definition=text,
                # Page-wide examples may refer to a different sense. Do not mix them.
                source=source_url,
            )
    raise RuntimeError("备用词典未收录这个词。")


class WordnikDictionaryClient:
    async def lookup(self, word):
        # Wordnik can place capitalized English entries on its lowercase page.
        # The parser still validates the returned headword exactly (case-insensitive).
        url = "https://www.wordnik.com/words/" + quote(word.strip().lower(), safe="")
        async with httpx.AsyncClient(timeout=8, follow_redirects=True, headers={
            "User-Agent": "NEWABBYDictionaryBot/1.0 (https://www.newabby.com/)",
        }) as client:
            response = await client.get(url)
            response.raise_for_status()
            return parse_wordnik_entry(response.text, word, url)
