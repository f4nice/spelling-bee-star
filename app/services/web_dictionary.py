"""Fallback lookup of a single exact dictionary headword and its first sense."""
from html.parser import HTMLParser
from urllib.parse import quote

import httpx

from app.services.dictionary import DictionaryEntry


class _Node:
    def __init__(self, tag="", attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []

    def find(self, css_class):
        if css_class in self.attrs.get("class", "").split():
            yield self
        for child in self.children:
            if isinstance(child, _Node):
                yield from child.find(css_class)

    def text(self):
        return "".join(child.text() if isinstance(child, _Node) else child for child in self.children)


class _Tree(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _text(node, css_class):
    found = next(node.find(css_class), None)
    return " ".join(found.text().split()).strip() if found else None


def parse_cambridge_entry(html, word, source_url):
    tree = _Tree()
    tree.feed(html)
    normalized = " ".join(word.casefold().split())
    for entry in tree.root.find("entry-body__el"):
        headword = _text(entry, "hw") or ""
        if " ".join(headword.casefold().split()) != normalized:
            continue
        # Definitions, translation and example must come from the same sense.
        sense = next(entry.find("def-block"), None)
        definition = _text(sense, "def") if sense else None
        if not definition:
            continue
        us = next(entry.find("us"), None)
        phonetic = _text(us or entry, "ipa") or _text(entry, "ipa")
        return DictionaryEntry(
            phonetic=f"/{phonetic.strip('/ ' )}/" if phonetic else None,
            part_of_speech=_text(entry, "pos"),
            english_definition=definition.rstrip(": "),
            english_example=_text(sense, "eg"),
            chinese_definition=_text(sense, "trans"),
            source=source_url,
        )
    raise RuntimeError("备用词典未收录这个词，或返回的词条不匹配。")


class CambridgeDictionaryClient:
    async def lookup(self, word):
        path = quote(word.strip(), safe="")
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}) as client:
            for dictionary in ("english-chinese-simplified", "english"):
                url = f"https://dictionary.cambridge.org/dictionary/{dictionary}/{path}"
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    return parse_cambridge_entry(response.text, word, url)
                except (httpx.HTTPError, RuntimeError):
                    continue
        raise RuntimeError("备用在线词典暂不可用或未收录，请稍后重试。")
