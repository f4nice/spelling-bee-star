from __future__ import annotations

import json
import math
import re
import statistics
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout, as_completed
from collections import Counter, defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


USER_AGENT = "BookLearner/0.1 (+local learning app)"
GUTENDEX_SEARCH = "https://gutendex.com/books/?search={query}"
OPEN_LIBRARY_SEARCH = (
    "https://openlibrary.org/search.json?q={query}"
    "&limit=5&fields=title,author_name,first_publish_year,language,key"
)
INTERNET_ARCHIVE_SEARCH = (
    "https://archive.org/advancedsearch.php?q={query}"
    "&fl[]=identifier&fl[]=title&fl[]=creator&fl[]=year&rows=5&output=json"
)
GOOGLE_BOOKS_SEARCH = "https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=5"
DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
MAX_TEXT_BYTES = 2_500_000
MAX_ANALYSIS_CHARS = 450_000
MATCH_STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "book",
    "novel",
    "story",
    "tale",
}


COMMON_WORDS = {
    "about",
    "above",
    "across",
    "after",
    "again",
    "against",
    "almost",
    "alone",
    "along",
    "already",
    "also",
    "although",
    "always",
    "among",
    "another",
    "answer",
    "because",
    "became",
    "become",
    "before",
    "being",
    "below",
    "between",
    "cannot",
    "chapter",
    "could",
    "course",
    "dear",
    "does",
    "done",
    "down",
    "each",
    "either",
    "enough",
    "even",
    "every",
    "first",
    "found",
    "friend",
    "from",
    "good",
    "great",
    "gutenberg",
    "hand",
    "having",
    "here",
    "herself",
    "himself",
    "house",
    "into",
    "just",
    "know",
    "last",
    "little",
    "long",
    "look",
    "made",
    "make",
    "many",
    "might",
    "more",
    "most",
    "much",
    "must",
    "never",
    "nothing",
    "only",
    "other",
    "over",
    "people",
    "place",
    "project",
    "quite",
    "rather",
    "said",
    "same",
    "shall",
    "should",
    "some",
    "still",
    "such",
    "than",
    "that",
    "their",
    "them",
    "then",
    "there",
    "these",
    "thing",
    "think",
    "this",
    "those",
    "though",
    "through",
    "time",
    "under",
    "until",
    "upon",
    "very",
    "well",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "without",
    "would",
    "your",
    "youre",
}

QUOTE_CUES = {
    "beauty",
    "believe",
    "courage",
    "death",
    "dream",
    "fear",
    "fortune",
    "freedom",
    "friendship",
    "happiness",
    "heart",
    "hope",
    "human",
    "imagination",
    "justice",
    "knowledge",
    "life",
    "love",
    "memory",
    "mind",
    "nature",
    "power",
    "pride",
    "reason",
    "soul",
    "truth",
    "wisdom",
    "world",
}

BUILTIN_DEFINITIONS = {
    "amiable": "friendly and pleasant",
    "ardent": "showing strong feeling or enthusiasm",
    "benevolent": "kind and generous",
    "capricious": "changing suddenly and unpredictably",
    "countenance": "a person's face or expression",
    "discern": "to notice or understand something",
    "disposition": "a person's usual mood or character",
    "eloquence": "clear and persuasive expression",
    "endeavour": "a serious attempt or effort",
    "felicity": "great happiness or suitable expression",
    "impertinent": "rude or not showing respect",
    "melancholy": "deep sadness",
    "obstinate": "stubborn and refusing to change",
    "propriety": "correct behavior or manners",
    "reproach": "to criticize or express disappointment",
    "solicitude": "care or concern for someone",
}

KNOWN_GUTENBERG_BOOKS = [
    {
        "id": 1342,
        "title": "Pride and Prejudice",
        "authors": ["Jane Austen"],
        "aliases": ["傲慢与偏见", "jane austen"],
    },
    {
        "id": 1260,
        "title": "Jane Eyre",
        "authors": ["Charlotte Bronte"],
        "aliases": ["简爱", "charlotte bronte"],
    },
    {
        "id": 64317,
        "title": "The Great Gatsby",
        "authors": ["F. Scott Fitzgerald"],
        "aliases": ["了不起的盖茨比", "great gatsby", "fitzgerald"],
    },
    {
        "id": 1661,
        "title": "The Adventures of Sherlock Holmes",
        "authors": ["Arthur Conan Doyle"],
        "aliases": ["福尔摩斯", "sherlock holmes", "conan doyle"],
    },
    {
        "id": 84,
        "title": "Frankenstein",
        "authors": ["Mary Wollstonecraft Shelley"],
        "aliases": ["弗兰肯斯坦", "mary shelley"],
    },
    {
        "id": 2701,
        "title": "Moby-Dick",
        "authors": ["Herman Melville"],
        "aliases": ["白鲸", "moby dick", "melville"],
    },
    {
        "id": 98,
        "title": "A Tale of Two Cities",
        "authors": ["Charles Dickens"],
        "aliases": ["双城记", "dickens"],
    },
    {
        "id": 1400,
        "title": "Great Expectations",
        "authors": ["Charles Dickens"],
        "aliases": ["远大前程", "dickens"],
    },
    {
        "id": 11,
        "title": "Alice's Adventures in Wonderland",
        "authors": ["Lewis Carroll"],
        "aliases": ["爱丽丝梦游仙境", "alice in wonderland"],
    },
    {
        "id": 76,
        "title": "Adventures of Huckleberry Finn",
        "authors": ["Mark Twain"],
        "aliases": ["哈克贝利费恩历险记", "huckleberry finn", "mark twain"],
    },
    {
        "id": 2600,
        "title": "War and Peace",
        "authors": ["Leo Tolstoy"],
        "aliases": ["战争与和平", "tolstoy"],
    },
    {
        "id": 1513,
        "title": "Romeo and Juliet",
        "authors": ["William Shakespeare"],
        "aliases": ["罗密欧与朱丽叶", "shakespeare"],
    },
    {
        "id": 1524,
        "title": "Hamlet",
        "authors": ["William Shakespeare"],
        "aliases": ["哈姆雷特", "shakespeare"],
    },
    {
        "id": 345,
        "title": "Dracula",
        "authors": ["Bram Stoker"],
        "aliases": ["德古拉", "bram stoker"],
    },
    {
        "id": 174,
        "title": "The Picture of Dorian Gray",
        "authors": ["Oscar Wilde"],
        "aliases": ["道林格雷的画像", "dorian gray", "oscar wilde"],
    },
    {
        "id": 5200,
        "title": "Metamorphosis",
        "authors": ["Franz Kafka"],
        "aliases": ["变形记", "kafka"],
    },
]

POPULAR_BOOK_SUGGESTIONS = [
    {
        "title": "The Graveyard Book",
        "authors": ["Neil Gaiman"],
        "aliases": ["graveyard book", "neil gaiman"],
        "firstPublishYear": 2008,
    },
    {
        "title": "Nineteen Eighty-Four",
        "authors": ["George Orwell"],
        "aliases": ["1984", "nineteen eighty four", "orwell"],
        "firstPublishYear": 1949,
    },
    {
        "title": "Animal Farm",
        "authors": ["George Orwell"],
        "aliases": ["animal farm", "orwell"],
        "firstPublishYear": 1945,
    },
    {
        "title": "To Kill a Mockingbird",
        "authors": ["Harper Lee"],
        "aliases": ["mockingbird", "harper lee"],
        "firstPublishYear": 1960,
    },
    {
        "title": "The Catcher in the Rye",
        "authors": ["J. D. Salinger"],
        "aliases": ["catcher in the rye", "salinger"],
        "firstPublishYear": 1951,
    },
    {
        "title": "Harry Potter and the Philosopher's Stone",
        "authors": ["J. K. Rowling"],
        "aliases": ["harry potter", "sorcerer's stone", "rowling"],
        "firstPublishYear": 1997,
    },
]

STANDARD_EBOOKS_BOOKS = [
    {
        "title": "Pride and Prejudice",
        "authors": ["Jane Austen"],
        "aliases": ["jane austen", "pride prejudice"],
        "path": "jane-austen/pride-and-prejudice",
    },
    {
        "title": "Jane Eyre",
        "authors": ["Charlotte Bronte"],
        "aliases": ["charlotte bronte"],
        "path": "charlotte-bronte/jane-eyre",
    },
    {
        "title": "The Great Gatsby",
        "authors": ["F. Scott Fitzgerald"],
        "aliases": ["great gatsby", "fitzgerald"],
        "path": "f-scott-fitzgerald/the-great-gatsby",
    },
    {
        "title": "The Adventures of Sherlock Holmes",
        "authors": ["Arthur Conan Doyle"],
        "aliases": ["sherlock holmes", "conan doyle"],
        "path": "arthur-conan-doyle/the-adventures-of-sherlock-holmes",
    },
    {
        "title": "Frankenstein",
        "authors": ["Mary Wollstonecraft Shelley"],
        "aliases": ["mary shelley"],
        "path": "mary-shelley/frankenstein",
    },
    {
        "title": "Dracula",
        "authors": ["Bram Stoker"],
        "aliases": ["bram stoker"],
        "path": "bram-stoker/dracula",
    },
    {
        "title": "Moby-Dick",
        "authors": ["Herman Melville"],
        "aliases": ["moby dick", "melville"],
        "path": "herman-melville/moby-dick",
    },
    {
        "title": "Alice's Adventures in Wonderland",
        "authors": ["Lewis Carroll"],
        "aliases": ["alice in wonderland"],
        "path": "lewis-carroll/alices-adventures-in-wonderland",
    },
]


@dataclass
class BookSource:
    title: str
    authors: list[str]
    language: str
    source_name: str
    source_url: str
    text_url: str | None
    copyright_note: str


def analyze_query(query: str) -> dict[str, Any]:
    query = query.strip()
    network_notes = []
    known_result = _search_known_gutenberg(query)
    if known_result and known_result[1]:
        return _analyze_public_text(source=known_result[0], text=known_result[1], query=query)

    standard_result = _search_standard_ebooks(query)
    if standard_result and standard_result[1]:
        return _analyze_public_text(source=standard_result[0], text=standard_result[1], query=query)

    try:
        gutenberg_result = _search_gutendex(query)
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        gutenberg_result = None
        network_notes.append("Gutendex / Project Gutenberg 暂时访问失败。")

    if gutenberg_result:
        source, raw_text = gutenberg_result
        if raw_text:
            return _analyze_public_text(source=source, text=raw_text, query=query)
        return _metadata_only(
            source=source,
            query=query,
            notice="找到了公版书籍信息，但没有拿到可分析的纯文本。",
        )

    if known_result:
        source, raw_text = known_result
        if raw_text:
            return _analyze_public_text(source=source, text=raw_text, query=query)
        return _metadata_only(source=source, query=query, notice="找到了内置公版书籍信息，但文本下载失败。")

    if standard_result:
        source, raw_text = standard_result
        if raw_text:
            return _analyze_public_text(source=source, text=raw_text, query=query)
        return _metadata_only(source=source, query=query, notice="找到了 Standard Ebooks 书籍信息，但文本下载失败。")

    metadata = _search_metadata_sources(query)
    if metadata:
        source_names = metadata.get("sourceName", "元信息来源")
        notice = f"未找到可合法分析的公版全文；已改用 {source_names} 元信息。为避免编造语录，暂不生成原文短句。"
        if network_notes:
            notice = f"公版全文检索暂时失败；已改用 {source_names} 元信息。为避免编造语录，暂不生成原文短句。"
        return {
            "status": "metadata_only",
            "query": query,
            "book": metadata,
            "notice": notice,
            "quotes": [],
            "vocabulary": [],
            "readingFocus": [],
            "nextSteps": ["换一个英文公版书名重试", "在“粘贴文本”里放入你有权学习使用的原文片段"],
        }

    if network_notes:
        return {
            "status": "network_error",
            "query": query,
            "notice": "在线书库暂时访问失败。可以稍后重试，或直接粘贴文本分析。",
            "quotes": [],
            "vocabulary": [],
            "readingFocus": [],
            "nextSteps": ["稍后重新搜索", "检查本机网络或代理", "粘贴文本片段分析"],
        }

    return {
        "status": "not_found",
        "query": query,
        "notice": "没有找到匹配的书籍。可以尝试英文书名、作者名，或直接粘贴文本分析。",
        "quotes": [],
        "vocabulary": [],
        "readingFocus": [],
        "nextSteps": ["检查书名拼写", "用作者名加书名一起搜索", "粘贴文本片段分析"],
    }


def suggest_books(query: str, limit: int = 8) -> list[dict[str, Any]]:
    query = query.strip()
    normalized_query = _normalize_match_text(query)
    if len(normalized_query) < 2:
        return []

    suggestions: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in _local_book_suggestions(query):
        _add_suggestion(suggestions, seen, item)

    for item in _internet_archive_suggestions(query, limit=limit):
        _add_suggestion(suggestions, seen, item)

    for item in _google_books_suggestions(query, limit=limit):
        _add_suggestion(suggestions, seen, item)

    for item in _open_library_suggestions(query, limit=limit):
        _add_suggestion(suggestions, seen, item)

    suggestions.sort(key=lambda item: item.get("score", 0), reverse=True)
    return suggestions[:limit]


def analyze_text(title: str, author: str, text: str) -> dict[str, Any]:
    source = BookSource(
        title=title.strip() or "粘贴文本",
        authors=[author.strip()] if author.strip() else [],
        language="unknown",
        source_name="User provided text",
        source_url="",
        text_url=None,
        copyright_note="用户粘贴文本，仅在本地用于学习分析。",
    )
    return _analyze_public_text(source=source, text=text, query=title, user_text=True)


def _analyze_public_text(
    source: BookSource, text: str, query: str, user_text: bool = False
) -> dict[str, Any]:
    cleaned = _strip_gutenberg_boilerplate(text)
    cleaned = _normalize_text(cleaned[:MAX_ANALYSIS_CHARS])
    sentences = _split_sentences(cleaned)
    tokens = _tokenize(cleaned)

    quotes = _extract_quotes(sentences)
    vocabulary = _extract_vocabulary(tokens=tokens, sentences=sentences)
    reading_focus = _extract_reading_focus(tokens)

    return {
        "status": "ok",
        "query": query,
        "book": {
            "title": source.title,
            "authors": source.authors,
            "language": source.language,
            "sourceName": source.source_name,
            "sourceUrl": source.source_url,
            "textUrl": source.text_url,
            "copyrightNote": source.copyright_note,
        },
        "stats": {
            "characters": len(cleaned),
            "sentences": len(sentences),
            "words": len(tokens),
        },
        "quotesLabel": "经典短句" if user_text else "公版原文短句",
        "quotes": quotes,
        "vocabulary": vocabulary,
        "readingFocus": reading_focus,
        "notice": "已基于你粘贴的文本生成学习内容。"
        if user_text
        else "已基于可公开访问的公版全文生成学习内容。",
    }


def _metadata_only(source: BookSource, query: str, notice: str) -> dict[str, Any]:
    return {
        "status": "metadata_only",
        "query": query,
        "book": {
            "title": source.title,
            "authors": source.authors,
            "language": source.language,
            "sourceName": source.source_name,
            "sourceUrl": source.source_url,
            "textUrl": source.text_url,
            "copyrightNote": source.copyright_note,
        },
        "notice": notice,
        "quotes": [],
        "vocabulary": [],
        "readingFocus": [],
        "nextSteps": ["换一个英文公版书名重试", "粘贴你有权学习使用的文本片段"],
    }


def _search_gutendex(query: str) -> tuple[BookSource, str | None] | None:
    url = GUTENDEX_SEARCH.format(query=quote(query))
    payload = _fetch_json(url, timeout=10)
    results = payload.get("results", []) if isinstance(payload, dict) else []
    if not results:
        return None

    best = max(results[:8], key=lambda item: _book_score(query, item))
    formats = best.get("formats") or {}
    text_url = _choose_text_url(formats)
    authors = [
        author.get("name", "").strip()
        for author in best.get("authors", [])
        if author.get("name", "").strip()
    ]
    languages = best.get("languages") or []
    source = BookSource(
        title=best.get("title", "Unknown title"),
        authors=authors,
        language=", ".join(languages) if languages else "unknown",
        source_name="Gutendex / Project Gutenberg",
        source_url=f"https://www.gutenberg.org/ebooks/{best.get('id')}",
        text_url=text_url,
        copyright_note="Project Gutenberg public-domain text; availability depends on your country.",
    )
    if not text_url:
        return source, None

    try:
        return source, _fetch_text(text_url, timeout=18, max_bytes=MAX_TEXT_BYTES)
    except (HTTPError, URLError, TimeoutError, UnicodeDecodeError, OSError):
        return source, None


def _search_known_gutenberg(query: str) -> tuple[BookSource, str | None] | None:
    best = _match_known_book(query)
    if not best:
        return None

    source_url = f"https://www.gutenberg.org/ebooks/{best['id']}"
    text_urls = _gutenberg_text_urls(int(best["id"]))
    source = BookSource(
        title=str(best["title"]),
        authors=list(best["authors"]),
        language="en",
        source_name="Project Gutenberg direct text",
        source_url=source_url,
        text_url=text_urls[0],
        copyright_note="Project Gutenberg public-domain text; availability depends on your country.",
    )

    for text_url in text_urls:
        try:
            text = _fetch_text(text_url, timeout=12, max_bytes=MAX_TEXT_BYTES)
            if len(text) > 1_000:
                source.text_url = text_url
                return source, text
        except (HTTPError, URLError, TimeoutError, UnicodeDecodeError, OSError):
            continue
    return source, None


def _search_standard_ebooks(query: str) -> tuple[BookSource, str | None] | None:
    best = _match_catalog_book(query, STANDARD_EBOOKS_BOOKS, min_score=7)
    if not best:
        return None

    page_url = f"https://standardebooks.org/ebooks/{best['path']}/text/single-page"
    source = BookSource(
        title=str(best["title"]),
        authors=list(best["authors"]),
        language="en",
        source_name="Standard Ebooks",
        source_url=f"https://standardebooks.org/ebooks/{best['path']}",
        text_url=page_url,
        copyright_note="Standard Ebooks public-domain text; availability depends on your country.",
    )
    try:
        html = _fetch_text(page_url, timeout=16, max_bytes=MAX_TEXT_BYTES)
        text = _html_to_text(html)
        if len(text) > 1_000:
            return source, text
    except (HTTPError, URLError, TimeoutError, UnicodeDecodeError, OSError):
        pass
    return source, None


def _match_known_book(query: str) -> dict[str, Any] | None:
    normalized_query = _normalize_match_text(query)
    query_terms = set(_meaningful_match_terms(normalized_query))
    best_score = 0.0
    best_book = None

    for book in KNOWN_GUTENBERG_BOOKS:
        title = _normalize_match_text(str(book["title"]))
        authors = [_normalize_match_text(author) for author in book["authors"]]
        aliases = [_normalize_match_text(alias) for alias in book["aliases"]]
        haystack = " ".join([title, *authors, *aliases])
        score = 0.0
        if normalized_query == title:
            score += 20
        if normalized_query and normalized_query in haystack:
            score += 8
        score += sum(2 for term in query_terms if len(term) > 2 and term in haystack)
        if score > best_score:
            best_score = score
            best_book = book

    return best_book if best_score >= 4 else None


def _match_catalog_book(query: str, books: list[dict[str, Any]], min_score: float) -> dict[str, Any] | None:
    best_score = 0.0
    best_book = None
    for book in books:
        score = _catalog_match_score(query, book)
        if score > best_score:
            best_score = score
            best_book = book
    return best_book if best_book and best_score >= min_score else None


def _normalize_match_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", " ", value.lower())).strip()


def _gutenberg_text_urls(book_id: int) -> list[str]:
    return [
        f"https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt",
        f"https://www.gutenberg.org/files/{book_id}/{book_id}-0.txt",
        f"https://www.gutenberg.org/files/{book_id}/{book_id}.txt",
    ]


def _search_open_library(query: str) -> dict[str, Any] | None:
    url = OPEN_LIBRARY_SEARCH.format(query=quote(query))
    try:
        payload = _fetch_json(url, timeout=12)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None

    docs = payload.get("docs", []) if isinstance(payload, dict) else []
    if not docs:
        return None

    best = max(docs, key=lambda item: _open_library_score(query, item))
    return {
        "title": best.get("title", "Unknown title"),
        "authors": best.get("author_name", [])[:5],
        "firstPublishYear": best.get("first_publish_year"),
        "language": ", ".join(best.get("language", [])[:5]),
        "sourceName": "Open Library",
        "sourceUrl": f"https://openlibrary.org{best.get('key', '')}",
        "copyrightNote": "仅找到书籍元信息，未找到可分析的全文。",
        "_score": _open_library_score(query, best),
    }


def _search_metadata_sources(query: str) -> dict[str, Any] | None:
    candidates = [
        item
        for item in (
            _search_open_library(query),
            _search_internet_archive(query),
            _search_google_books(query),
        )
        if item
    ]
    if not candidates:
        return None

    best = max(candidates, key=lambda item: _metadata_rank(query, item))
    source_names = []
    source_urls = []
    for item in sorted(candidates, key=lambda row: _metadata_rank(query, row), reverse=True):
        source_name = item.get("sourceName")
        source_url = item.get("sourceUrl")
        if source_name and source_name not in source_names:
            source_names.append(source_name)
        if source_url and source_url not in source_urls:
            source_urls.append(source_url)

    merged = {key: value for key, value in best.items() if not key.startswith("_")}
    merged["sourceName"] = " / ".join(source_names)
    merged["sourceUrl"] = source_urls[0] if source_urls else best.get("sourceUrl", "")
    merged["sourceUrls"] = source_urls
    merged["copyrightNote"] = "仅找到书籍元信息，未找到可分析的公版全文。"
    return merged


def _metadata_rank(query: str, item: dict[str, Any]) -> float:
    title_similarity = _text_similarity(query, str(item.get("title", "")))
    source_priority = {
        "Open Library": 8,
        "Google Books": 6,
        "Internet Archive": 3,
    }.get(str(item.get("sourceName", "")), 0)
    return title_similarity * 35 + item.get("_score", 0) + source_priority


def _search_internet_archive(query: str) -> dict[str, Any] | None:
    url = INTERNET_ARCHIVE_SEARCH.format(query=quote(f'title:"{query}"'))
    try:
        payload = _fetch_json(url, timeout=8)
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None

    docs = payload.get("response", {}).get("docs", []) if isinstance(payload, dict) else []
    if not docs:
        return None

    best = max(docs, key=lambda item: _internet_archive_score(query, item))
    identifier = best.get("identifier", "")
    return {
        "title": best.get("title", "Unknown title"),
        "authors": _as_list(best.get("creator"))[:5],
        "firstPublishYear": best.get("year"),
        "language": "",
        "sourceName": "Internet Archive",
        "sourceUrl": f"https://archive.org/details/{identifier}" if identifier else "https://archive.org/",
        "copyrightNote": "仅找到书籍元信息，未找到可分析的公版全文。",
        "_score": _internet_archive_score(query, best),
    }


def _search_google_books(query: str) -> dict[str, Any] | None:
    url = GOOGLE_BOOKS_SEARCH.format(query=quote(query))
    try:
        payload = _fetch_json(url, timeout=6)
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None

    items = payload.get("items", []) if isinstance(payload, dict) else []
    if not items:
        return None

    best = max(items, key=lambda item: _google_books_score(query, item))
    info = best.get("volumeInfo", {})
    return {
        "title": info.get("title", "Unknown title"),
        "authors": info.get("authors", [])[:5],
        "firstPublishYear": _year_from_date(info.get("publishedDate")),
        "language": info.get("language", ""),
        "sourceName": "Google Books",
        "sourceUrl": info.get("infoLink") or f"https://books.google.com/books?id={best.get('id', '')}",
        "copyrightNote": "仅找到书籍元信息，未找到可分析的公版全文。",
        "_score": _google_books_score(query, best),
    }


def _fetch_json(url: str, timeout: int) -> dict[str, Any]:
    data = _fetch_bytes(url, timeout=timeout, max_bytes=1_500_000)
    return json.loads(data.decode("utf-8"))


def _fetch_text(url: str, timeout: int, max_bytes: int) -> str:
    data = _fetch_bytes(url, timeout=timeout, max_bytes=max_bytes)
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _html_to_text(html: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(html)
    return _normalize_text(" ".join(parser.parts))


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "svg", "nav", "header", "footer"}:
            self._skip_depth += 1
        if tag in {"p", "div", "section", "article", "h1", "h2", "h3", "li", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg", "nav", "header", "footer"} and self._skip_depth:
            self._skip_depth -= 1
        if tag in {"p", "div", "section", "article", "li"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if text:
            self.parts.append(text)


def _fetch_bytes(url: str, timeout: int, max_bytes: int) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        return response.read(max_bytes)


def _book_score(query: str, item: dict[str, Any]) -> float:
    haystack = " ".join(
        [
            str(item.get("title", "")),
            " ".join(author.get("name", "") for author in item.get("authors", [])),
        ]
    ).lower()
    query_terms = [part for part in re.split(r"\W+", query.lower()) if part]
    score = sum(4 for term in query_terms if term in haystack)
    score += min(int(item.get("download_count", 0) or 0), 50_000) / 10_000
    if str(item.get("title", "")).lower() == query.lower():
        score += 10
    return score


def _open_library_score(query: str, item: dict[str, Any]) -> float:
    title = str(item.get("title", "")).lower()
    authors = " ".join(item.get("author_name", [])).lower()
    haystack = f"{title} {authors}"
    terms = [part for part in re.split(r"\W+", query.lower()) if part]
    score = sum(3 for term in terms if term in haystack)
    if title == query.lower():
        score += 10
    if item.get("first_publish_year"):
        score += 1
    return score


def _internet_archive_score(query: str, item: dict[str, Any]) -> float:
    title = str(item.get("title", ""))
    creators = " ".join(_as_list(item.get("creator")))
    score = _catalog_text_score(query, f"{title} {creators}")
    if item.get("year"):
        score += 1
    return score


def _google_books_score(query: str, item: dict[str, Any]) -> float:
    info = item.get("volumeInfo", {})
    title = str(info.get("title", ""))
    authors = " ".join(info.get("authors", []))
    score = _catalog_text_score(query, f"{title} {authors}")
    if info.get("publishedDate"):
        score += 1
    return score


def _catalog_text_score(query: str, text: str) -> float:
    normalized_query = _normalize_match_text(query)
    normalized_text = _normalize_match_text(text)
    terms = _meaningful_match_terms(normalized_query)
    score = _text_similarity(normalized_query, normalized_text) * 8
    if normalized_query and normalized_query in normalized_text:
        score += 8
    score += sum(2.5 for term in terms if term in normalized_text)
    score += _near_token_bonus(terms, normalized_text)
    if not _has_meaningful_anchor(terms, normalized_text):
        score = min(score, 2.5)
    return score


def _local_book_suggestions(query: str) -> list[dict[str, Any]]:
    suggestions = []
    for book in KNOWN_GUTENBERG_BOOKS:
        score = _catalog_match_score(query, book)
        if score >= 7:
            suggestions.append(
                {
                    "title": book["title"],
                    "authors": list(book["authors"]),
                    "sourceName": "Project Gutenberg",
                    "sourceUrl": f"https://www.gutenberg.org/ebooks/{book['id']}",
                    "availableText": True,
                    "hint": "可直接分析公版全文",
                    "score": round(score + 2, 3),
                }
            )

    for book in POPULAR_BOOK_SUGGESTIONS:
        score = _catalog_match_score(query, book)
        if score >= 7:
            suggestions.append(
                {
                    "title": book["title"],
                    "authors": list(book["authors"]),
                    "firstPublishYear": book.get("firstPublishYear"),
                    "sourceName": "Local suggestions",
                    "sourceUrl": f"https://openlibrary.org/search?q={quote(str(book['title']))}",
                    "availableText": False,
                    "hint": "可作为书名继续搜索",
                    "score": round(score, 3),
                }
            )
    return suggestions


def _internet_archive_suggestions(query: str, limit: int) -> list[dict[str, Any]]:
    url = INTERNET_ARCHIVE_SEARCH.format(query=quote(query))
    try:
        payload = _fetch_json(url, timeout=5)
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        return []

    docs = payload.get("response", {}).get("docs", []) if isinstance(payload, dict) else []
    suggestions = []
    for doc in docs[: max(3, limit)]:
        title = str(doc.get("title") or "").strip()
        if not title:
            continue
        identifier = doc.get("identifier", "")
        suggestions.append(
            {
                "title": title,
                "authors": _as_list(doc.get("creator"))[:4],
                "firstPublishYear": doc.get("year"),
                "sourceName": "Internet Archive",
                "sourceUrl": f"https://archive.org/details/{identifier}" if identifier else "https://archive.org/",
                "availableText": False,
                "hint": "可作为书名继续搜索",
                "score": round(_internet_archive_score(query, doc), 3),
            }
        )
    return suggestions


def _google_books_suggestions(query: str, limit: int) -> list[dict[str, Any]]:
    url = GOOGLE_BOOKS_SEARCH.format(query=quote(query))
    try:
        payload = _fetch_json(url, timeout=4)
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        return []

    items = payload.get("items", []) if isinstance(payload, dict) else []
    suggestions = []
    for item in items[: max(3, limit)]:
        info = item.get("volumeInfo", {})
        title = str(info.get("title") or "").strip()
        if not title:
            continue
        suggestions.append(
            {
                "title": title,
                "authors": info.get("authors", [])[:4],
                "firstPublishYear": _year_from_date(info.get("publishedDate")),
                "sourceName": "Google Books",
                "sourceUrl": info.get("infoLink") or f"https://books.google.com/books?id={item.get('id', '')}",
                "availableText": False,
                "hint": "可作为书名继续搜索",
                "score": round(_google_books_score(query, item), 3),
            }
        )
    return suggestions


def _open_library_suggestions(query: str, limit: int) -> list[dict[str, Any]]:
    url = (
        "https://openlibrary.org/search.json?q={query}"
        "&limit={limit}&fields=title,author_name,first_publish_year,language,key"
    ).format(query=quote(query), limit=max(3, min(limit, 10)))
    try:
        payload = _fetch_json(url, timeout=4)
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        return []

    docs = payload.get("docs", []) if isinstance(payload, dict) else []
    suggestions = []
    for doc in docs[: max(3, limit)]:
        title = str(doc.get("title") or "").strip()
        if not title:
            continue
        authors = doc.get("author_name") or []
        score = _open_library_score(query, doc) + _text_similarity(query, " ".join([title, *authors])) * 5
        suggestions.append(
            {
                "title": title,
                "authors": authors[:4],
                "firstPublishYear": doc.get("first_publish_year"),
                "sourceName": "Open Library",
                "sourceUrl": f"https://openlibrary.org{doc.get('key', '')}",
                "availableText": False,
                "hint": "可作为书名继续搜索",
                "score": round(score, 3),
            }
        )
    return suggestions


def _catalog_match_score(query: str, book: dict[str, Any]) -> float:
    normalized_query = _normalize_match_text(query)
    if not normalized_query:
        return 0

    candidates = [
        str(book.get("title", "")),
        *[str(author) for author in book.get("authors", [])],
        *[str(alias) for alias in book.get("aliases", [])],
    ]
    normalized_candidates = [_normalize_match_text(candidate) for candidate in candidates if candidate]
    query_terms = _meaningful_match_terms(normalized_query)
    score = max((_text_similarity(normalized_query, candidate) * 10 for candidate in normalized_candidates), default=0)

    has_anchor = False
    for candidate in normalized_candidates:
        if normalized_query == candidate:
            score += 12
            has_anchor = True
        elif normalized_query in candidate:
            score += 7
            has_anchor = True
        score += sum(1.8 for term in query_terms if term in candidate)
        score += sum(1.2 for term in query_terms if any(part.startswith(term) for part in candidate.split()))
        near_bonus = _near_token_bonus(query_terms, candidate)
        score += near_bonus
        has_anchor = has_anchor or _has_meaningful_anchor(query_terms, candidate)
    if not has_anchor:
        score = min(score, 2.5)
    return score


def _near_token_bonus(query_terms: list[str], candidate: str) -> float:
    candidate_terms = [part for part in candidate.split() if len(part) >= 4]
    bonus = 0.0
    for term in query_terms:
        if len(term) < 4 or not candidate_terms:
            continue
        best = max(_text_similarity(term, part) for part in candidate_terms)
        if best >= 0.82:
            bonus += 8
        elif best >= 0.74:
            bonus += 4
    return bonus


def _has_meaningful_anchor(query_terms: list[str], candidate: str) -> bool:
    candidate_terms = [part for part in candidate.split() if len(part) >= 4]
    for term in query_terms:
        if term in candidate:
            return True
        if candidate_terms and max(_text_similarity(term, part) for part in candidate_terms) >= 0.74:
            return True
    return False


def _meaningful_match_terms(value: str) -> list[str]:
    return [term for term in value.split() if len(term) >= 4 and term not in MATCH_STOP_WORDS]


def _text_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, _normalize_match_text(left), _normalize_match_text(right)).ratio()


def _add_suggestion(items: list[dict[str, Any]], seen: set[str], item: dict[str, Any]) -> None:
    key = _suggestion_key(item)
    if key in seen:
        return
    seen.add(key)
    items.append(item)


def _suggestion_key(item: dict[str, Any]) -> str:
    authors = item.get("authors") or []
    author = authors[0] if authors else ""
    return f"{_normalize_match_text(str(item.get('title', '')))}::{_normalize_match_text(str(author))}"


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [str(value)]


def _year_from_date(value: Any) -> str:
    if not value:
        return ""
    match = re.search(r"\d{4}", str(value))
    return match.group(0) if match else str(value)


def _choose_text_url(formats: dict[str, str]) -> str | None:
    preferred = []
    fallback = []
    for mime_type, url in formats.items():
        if not isinstance(url, str) or not url.startswith("http"):
            continue
        lowered = mime_type.lower()
        if "text/plain" in lowered and "zip" not in lowered:
            preferred.append(url)
        elif url.lower().endswith((".txt", ".txt.utf-8")):
            fallback.append(url)
    return (preferred or fallback or [None])[0]


def _strip_gutenberg_boilerplate(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    start_index = 0
    end_index = len(lines)

    for index, line in enumerate(lines[:800]):
        upper = line.upper()
        if "START OF" in upper and "PROJECT GUTENBERG" in upper:
            start_index = index + 1
            break

    for index in range(len(lines) - 1, max(-1, len(lines) - 1200), -1):
        upper = lines[index].upper()
        if "END OF" in upper and "PROJECT GUTENBERG" in upper:
            end_index = index
            break

    return "\n".join(lines[start_index:end_index])


def _normalize_text(text: str) -> str:
    text = unescape(text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def _split_sentences(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text)
    raw_sentences = re.split(r"(?<=[.!?])\s+(?=[\"'“‘A-Z])", compact)
    sentences = []
    for sentence in raw_sentences:
        cleaned = _clean_sentence(sentence)
        if _is_good_sentence(cleaned):
            sentences.append(cleaned)
    return sentences


def _clean_sentence(sentence: str) -> str:
    sentence = sentence.strip(" \t\n\r\"'")
    sentence = sentence.replace("_", "")
    sentence = re.sub(r"\s+", " ", sentence)
    return sentence.strip()


def _is_good_sentence(sentence: str) -> bool:
    if not sentence:
        return False
    lowered = sentence.lower()
    if any(blocked in lowered for blocked in ("gutenberg", "http://", "https://", "ebook")):
        return False
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", sentence)
    if not 7 <= len(words) <= 36:
        return False
    if len(sentence) > 280:
        return False
    upper_letters = sum(1 for char in sentence if char.isupper())
    letters = sum(1 for char in sentence if char.isalpha())
    if letters and upper_letters / letters > 0.35:
        return False
    return True


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower().replace("'", "") for match in re.finditer(r"[A-Za-z][A-Za-z']+", text)]


def _extract_quotes(sentences: list[str]) -> list[dict[str, Any]]:
    scored = []
    seen = set()
    for index, sentence in enumerate(sentences):
        words = [word.lower().strip("'") for word in re.findall(r"[A-Za-z][A-Za-z'-]*", sentence)]
        if not words:
            continue

        normalized = re.sub(r"[^a-z]+", " ", sentence.lower()).strip()
        key = " ".join(normalized.split()[:10])
        if key in seen:
            continue
        seen.add(key)

        unique_ratio = len(set(words)) / len(words)
        cue_hits = len(set(words) & QUOTE_CUES)
        length_score = 1.0 - abs(len(words) - 18) / 36
        punctuation_score = 0.15 if any(mark in sentence for mark in (";", ":", ",")) else 0
        position_score = 0.2 if index < max(30, len(sentences) * 0.12) else 0
        score = unique_ratio * 2 + cue_hits * 0.75 + length_score + punctuation_score + position_score
        scored.append((score, sentence))

    scored.sort(reverse=True, key=lambda item: item[0])
    selected = []
    selected_terms: list[set[str]] = []
    for score, sentence in scored:
        terms = set(re.findall(r"[a-z]{4,}", sentence.lower()))
        if any(_jaccard(terms, existing) > 0.45 for existing in selected_terms):
            continue
        selected.append(
            {
                "text": _trim_words(sentence, 36),
                "note": _quote_note(sentence),
                "score": round(score, 2),
            }
        )
        selected_terms.append(terms)
        if len(selected) == 10:
            break
    return selected


def _quote_note(sentence: str) -> str:
    words = set(re.findall(r"[a-z]+", sentence.lower()))
    cues = sorted(words & QUOTE_CUES)
    if cues:
        return f"可关注主题：{', '.join(cues[:3])}"
    if ";" in sentence or ":" in sentence:
        return "句式有转折或解释关系，适合精读。"
    return "表达完整，适合做跟读和复述。"


def _extract_vocabulary(tokens: list[str], sentences: list[str]) -> list[dict[str, Any]]:
    counts = Counter(token for token in tokens if _is_candidate_word(token))
    if not counts:
        return []

    frequencies = list(counts.values())
    median = statistics.median(frequencies) if frequencies else 1
    candidates = []
    for word, count in counts.items():
        if count > max(80, median * 25):
            continue
        rarity = 1 / math.sqrt(count)
        score = len(word) * 1.4 + min(count, 8) * 0.25 + rarity
        if word.endswith(("tion", "ment", "ous", "ive", "ity", "ance", "ence")):
            score += 1.5
        candidates.append((score, word, count))

    candidates.sort(reverse=True)
    selected = [(word, count) for _, word, count in candidates[:16]]
    definitions = _lookup_definitions([word for word, _ in selected])
    vocabulary = []
    for word, count in selected:
        definition = definitions[word]
        vocabulary.append(
            {
                "word": word,
                "count": count,
                "definition": definition["definition"],
                "partOfSpeech": definition["partOfSpeech"],
                "example": _find_example_sentence(word, sentences),
                "memoryHint": _memory_hint(word),
            }
        )
    return vocabulary


def _is_candidate_word(word: str) -> bool:
    if len(word) < 7 or word in COMMON_WORDS:
        return False
    if not re.fullmatch(r"[a-z]+", word):
        return False
    if len(set(word)) <= 3:
        return False
    return True


def _lookup_definition(word: str) -> dict[str, str]:
    if word in BUILTIN_DEFINITIONS:
        return {"partOfSpeech": "", "definition": BUILTIN_DEFINITIONS[word]}

    try:
        payload = _fetch_json(DICTIONARY_API.format(word=quote(word)), timeout=2)
        entry = payload[0]
        meaning = entry.get("meanings", [{}])[0]
        definitions = meaning.get("definitions", [{}])
        definition = definitions[0].get("definition", "").strip()
        part = meaning.get("partOfSpeech", "").strip()
        if definition:
            return {"partOfSpeech": part, "definition": definition}
    except Exception:
        pass

    return {"partOfSpeech": "", "definition": "未找到在线释义，建议结合例句查词典。"}


def _lookup_definitions(words: list[str]) -> dict[str, dict[str, str]]:
    fallback = {"partOfSpeech": "", "definition": "未找到在线释义，建议结合例句查词典。"}
    definitions = {word: fallback for word in words}
    missing = []
    for word in words:
        if word in BUILTIN_DEFINITIONS:
            definitions[word] = {"partOfSpeech": "", "definition": BUILTIN_DEFINITIONS[word]}
        else:
            missing.append(word)

    if not missing:
        return definitions

    executor = ThreadPoolExecutor(max_workers=6)
    futures = {executor.submit(_lookup_definition, word): word for word in missing}
    try:
        for future in as_completed(futures, timeout=8):
            word = futures[future]
            try:
                definitions[word] = future.result()
            except Exception:
                definitions[word] = fallback
    except FuturesTimeout:
        pass
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    return definitions


def _find_example_sentence(word: str, sentences: list[str]) -> str:
    pattern = re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)
    for sentence in sentences:
        if pattern.search(sentence):
            return _trim_words(sentence, 28)
    return ""


def _memory_hint(word: str) -> str:
    suffix_hints = {
        "tion": "名词后缀，常表示动作或结果。",
        "ment": "名词后缀，常表示行为、状态或结果。",
        "ous": "形容词后缀，常表示具有某种性质。",
        "ive": "形容词后缀，常表示倾向或能力。",
        "ity": "名词后缀，常表示性质或状态。",
        "ance": "名词后缀，常表示行为或状态。",
        "ence": "名词后缀，常表示行为或状态。",
    }
    for suffix, hint in suffix_hints.items():
        if word.endswith(suffix):
            return hint
    return "拆成音节读，再回到例句里记。"


def _extract_reading_focus(tokens: list[str]) -> list[dict[str, Any]]:
    counts = Counter(token for token in tokens if len(token) >= 5 and token not in COMMON_WORDS)
    focus = []
    for word, count in counts.most_common(12):
        if word in BUILTIN_DEFINITIONS or word in QUOTE_CUES or count >= 4:
            focus.append({"term": word, "count": count})
        if len(focus) == 8:
            break
    return focus


def _trim_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip(",;:") + "..."


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)
