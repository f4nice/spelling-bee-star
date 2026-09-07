"""Bounded lookup of the public Merriam-Webster entry, without bypassing blocks.

Only an exact headword and one local sense are accepted. Page-wide news examples,
related headwords, suggestions, and paywalled entries are deliberately excluded.
"""
import asyncio
import time
from urllib.parse import quote

import httpx

from app.services.dictionary import (
    DictionaryEntry, _merriam_phonetic, _normalize_merriam_headword,
)
from app.services.web_dictionary import _Node, _Tree


_BLOCKED_UNTIL = 0.0
_BLOCK_COOLDOWN_SECONDS = 300
_BLOCK_MESSAGE = "韦氏官网暂不接受自动查询，已暂停请求，稍后可重试。"
_DERIVED_ENTRY_CLASSES = frozenset({"uros", "uro", "dros", "dro"})


def _visible_text(node):
    # Citation and cross-reference notes are not part of a definition/example.
    excluded = {"aq", "vis-aq", "mw_t_bc", "dxnls", "dxt"}
    if node.tag in {"script", "style"} or excluded.intersection(node.attrs.get("class", "").split()):
        return ""
    return "".join(_visible_text(child) if isinstance(child, _Node) else child
                   for child in node.children)


def _plain(node):
    return " ".join(_visible_text(node).split()).strip(" :") if node else None


def _local_nodes(node, css_class, skip_classes):
    if css_class in node.attrs.get("class", "").split():
        yield node
    for child in node.children:
        if isinstance(child, _Node) and not skip_classes.intersection(child.attrs.get("class", "").split()):
            yield from _local_nodes(child, css_class, skip_classes)


def parse_merriam_webster_entry(html: str, word: str, source_url: str) -> DictionaryEntry:
    tree = _Tree()
    tree.feed(html)
    expected = _normalize_merriam_headword(word)
    if not expected:
        raise RuntimeError("韦氏词典查询词不能为空。")
    title = next(tree.root.tags("title"), None)
    if title and title.text().strip().casefold() in {"just a moment...", "access denied", "attention required! | cloudflare"}:
        raise RuntimeError(_BLOCK_MESSAGE)

    # Limit every lookup to an actual entry container; h1s in suggestions and
    # definitions belonging to neighboring or derived words cannot be mixed in.
    entries = list(tree.root.find("entry-word-section-container"))
    if not entries:
        entries = [node for node in tree.root.tags("div")
                   if node.attrs.get("id", "").startswith("dictionary-entry-")]
    for entry in entries:
        headword = _plain(next(_local_nodes(entry, "hword", _DERIVED_ENTRY_CLASSES), None))
        if not headword or _normalize_merriam_headword(headword) != expected:
            continue
        # Run-ons and derived-entry blocks have their own headwords. They may
        # appear before the main senses, or be the only public definitions.
        # Never treat them as a definition/example of this matching headword.
        for sense in _local_nodes(entry, "sense", _DERIVED_ENTRY_CLASSES):
            sense_boundaries = _DERIVED_ENTRY_CLASSES | {"sense"}
            definition_node = next(_local_nodes(sense, "dtText", sense_boundaries), None)
            definition = _plain(definition_node)
            if not definition:
                continue
            # Do not take the page's "Recent Examples on the Web" section: it
            # is not tied to this sense and may have a different meaning/POS.
            example_node = next(_local_nodes(sense, "ex-sent", sense_boundaries), None)
            example = _plain(example_node)
            header = next(_local_nodes(entry, "entry-header", _DERIVED_ENTRY_CLASSES), None)
            pos = _plain(next(_local_nodes(header or entry, "parts-of-speech", _DERIVED_ENTRY_CLASSES), None))
            pronunciation = next((formatted for node in _local_nodes(entry, "pr", sense_boundaries)
                                  if (formatted := _merriam_phonetic(_plain(node)))), None)
            return DictionaryEntry(
                phonetic=pronunciation,
                part_of_speech=pos,
                english_definition=definition,
                english_example=example,
                source=source_url,
            )
    raise RuntimeError("韦氏官网未返回完全匹配的公开词条，或词条格式暂不支持。")


class MerriamWebsterWebClient:
    async def lookup(self, word: str) -> DictionaryEntry:
        global _BLOCKED_UNTIL
        if time.monotonic() < _BLOCKED_UNTIL:
            raise RuntimeError(_BLOCK_MESSAGE)
        url = "https://www.merriam-webster.com/dictionary/" + quote(word.strip().lower(), safe="")
        # Total time is capped as well as each socket operation. There is one
        # attempt only: no proxies, challenge solving, or alternate hosts.
        async with asyncio.timeout(12):
            async with httpx.AsyncClient(timeout=8, follow_redirects=True, max_redirects=2, headers={
                "User-Agent": "NEWABBYDictionaryBot/1.0 (https://www.newabby.com/)",
            }) as client:
                response = await client.get(url)
                if response.status_code in {401, 403, 429}:
                    _BLOCKED_UNTIL = time.monotonic() + _BLOCK_COOLDOWN_SECONDS
                    raise RuntimeError(_BLOCK_MESSAGE)
                response.raise_for_status()
                if response.url.host not in {"www.merriam-webster.com", "merriam-webster.com"}:
                    raise RuntimeError("韦氏词典返回了非词典地址。")
                if len(response.content) > 2_000_000:
                    raise RuntimeError("韦氏词条内容过大，已停止解析。")
                try:
                    return parse_merriam_webster_entry(response.text, word, url)
                except RuntimeError as exc:
                    if str(exc) == _BLOCK_MESSAGE:
                        _BLOCKED_UNTIL = time.monotonic() + _BLOCK_COOLDOWN_SECONDS
                    raise
