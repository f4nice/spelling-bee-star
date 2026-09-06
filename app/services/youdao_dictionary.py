"""Read public Youdao/WordNet fields; never use suggestions or premium blocks."""
import re
from urllib.parse import quote, urlencode

import httpx

from app.services.dictionary import DictionaryEntry
from app.services.web_dictionary import _Tree


def _items(value):
    return value if isinstance(value, list) else [value] if value else []


def _text(value):
    if isinstance(value, list):
        return " ".join(filter(None, (_text(item) for item in value)))
    if not isinstance(value, str):
        return ""
    tree = _Tree()
    tree.feed(value)
    return " ".join(tree.root.text().split())


def _label(value):
    if not isinstance(value, dict):
        return ""
    label = value.get("l") or {}
    return _text(label.get("i")) if isinstance(label, dict) else ""


def _exact_entry(payload, section, word):
    block = payload.get(section) or {}
    if not isinstance(block, dict):
        return {}
    for entry in _items(block.get("word")):
        if isinstance(entry, dict) and _label(entry.get("return-phrase")).casefold() == word.casefold():
            return entry
    return {}


def parse_youdao_entry(payload, word):
    word = " ".join(word.split())
    if not isinstance(payload, dict) or not word:
        raise RuntimeError("有道词典未返回有效词条。")
    bilingual = _exact_entry(payload, "ec", word)
    english = _exact_entry(payload, "ee", word)
    if not bilingual and not english:
        raise RuntimeError("有道词典未收录这个词，或返回的词条不匹配。")

    definitions = []
    examples = []
    part_of_speech = None
    for group in _items(english.get("trs")):
        if not isinstance(group, dict):
            continue
        pos = _text(group.get("pos"))
        if part_of_speech and pos != part_of_speech:
            continue
        part_of_speech = part_of_speech or pos
        for sense in _items(group.get("tr")):
            definition = _label(sense)
            if definition and definition not in definitions:
                definitions.append(definition)
            if isinstance(sense, dict):
                examples.extend(_text(item) for item in _items(sense.get("examples")))

    translations = []
    for group in _items(bilingual.get("trs")):
        if not isinstance(group, dict):
            continue
        for sense in _items(group.get("tr")):
            translation = _label(sense)
            pos_match = re.match(r"^(adj|adv|n|v|vi|vt|prep|pron|conj|interj|num|aux)\.\s*", translation)
            if pos_match:
                pos = pos_match[1] + "."
                if part_of_speech and pos != part_of_speech:
                    continue
                part_of_speech = part_of_speech or pos
                translation = translation[pos_match.end():]
            if translation and translation not in translations:
                translations.append(translation)

    if not definitions and not translations:
        raise RuntimeError("有道词典未返回这个词的公开释义。")

    sentence_block = payload.get("blng_sents_part") or {}
    if isinstance(sentence_block, dict):
        for pair in _items(sentence_block.get("sentence-pair")):
            if isinstance(pair, dict):
                examples.append(_text(pair.get("sentence") or pair.get("sentence-eng")))
    # Do not take unrelated recommendation examples or sentence fragments.
    pattern = re.compile(r"(?<![\w'-])" + re.escape(word) + r"(?![\w'-])", re.IGNORECASE)
    example = next((text for text in examples if pattern.search(text) and len(text.split()) >= 4 and text.endswith((".", "!", "?"))), None)
    phonetic = _text(bilingual.get("usphone") or bilingual.get("ukphone") or english.get("phone"))
    phonetic = re.split(r"[;；]", phonetic)[0].strip("/ ")
    audio_base = "https://dict.youdao.com/dictvoice?"
    return DictionaryEntry(
        phonetic=f"/{phonetic}/" if phonetic else None,
        part_of_speech=part_of_speech or None,
        english_definition="; ".join(definitions) or None,
        chinese_definition="；".join(translations) or None,
        english_example=example,
        american_audio_url=audio_base + urlencode({"audio": word, "type": 2}),
        british_audio_url=audio_base + urlencode({"audio": word, "type": 1}),
        source="https://dict.youdao.com/result?word=" + quote(word, safe="") + "&lang=en",
    )


class YoudaoDictionaryClient:
    async def lookup(self, word):
        try:
            async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
                response = await client.get("https://dict.youdao.com/jsonapi", params={"q": word.strip()})
                response.raise_for_status()
                return parse_youdao_entry(response.json(), word)
        except (httpx.HTTPError, ValueError) as exc:
            raise RuntimeError("有道词典暂不可用，请稍后重试。") from exc
