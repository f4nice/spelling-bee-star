from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import html
import re
from urllib.parse import urljoin

import httpx


CHINADAILY_HOME = "https://www.chinadaily.com.cn/"
HEADERS = {"User-Agent": "Mozilla/5.0"}


@dataclass(frozen=True)
class ChinaDailySection:
    key: str
    name: str
    url: str


SECTIONS = [
    ChinaDailySection("today", "Today", CHINADAILY_HOME),
    ChinaDailySection("china", "China", "https://www.chinadaily.com.cn/china"),
    ChinaDailySection("world", "World", "https://www.chinadaily.com.cn/world"),
    ChinaDailySection("business", "Business", "https://www.chinadaily.com.cn/business"),
    ChinaDailySection("culture", "Culture", "https://www.chinadaily.com.cn/culture"),
    ChinaDailySection("sports", "Sports", "https://www.chinadaily.com.cn/sports"),
]


def load_chinadaily_articles(limit_per_feed: int = 6) -> dict:
    sections = []
    today = datetime.now().strftime("%Y-%m-%d")
    for section in SECTIONS:
        try:
            articles = fetch_section_articles(section, limit=limit_per_feed, today=today)
            error = None
        except Exception as exc:
            articles = []
            error = str(exc)
        sections.append({"key": section.key, "name": section.name, "articles": articles, "error": error})
    return {
        "source": "China Daily",
        "source_url": CHINADAILY_HOME,
        "loaded_at": datetime.now(timezone.utc).isoformat(),
        "sections": sections,
    }


def get_chinadaily_article(section_key: str, article_index: int) -> dict:
    section = next((item for item in SECTIONS if item.key == section_key), None)
    if section is None:
        raise ValueError("Unknown China Daily section.")
    if article_index < 0:
        raise IndexError("Article index is out of range.")

    today = datetime.now().strftime("%Y-%m-%d")
    articles = fetch_section_articles(section, limit=max(article_index + 1, 12), today=today)
    try:
        article = articles[article_index]
    except IndexError as exc:
        raise IndexError("Article index is out of range.") from exc

    detail = fetch_article_detail(article["link"])
    article.update({key: value for key, value in detail.items() if value})
    return {"section": {"key": section.key, "name": section.name}, "article": article}


def fetch_section_articles(section: ChinaDailySection, limit: int, today: str) -> list[dict]:
    with httpx.Client(timeout=15, follow_redirects=True, headers=HEADERS) as client:
        response = client.get(section.url)
        response.raise_for_status()
    all_articles = extract_article_links(response.text, section.name)
    todays = [article for article in all_articles if article.get("published") == today]
    selected = todays or all_articles
    articles = selected[: max(1, limit)]
    for article in articles:
        try:
            detail = fetch_article_detail(article["link"])
        except Exception:
            continue
        for key in ("summary", "excerpt", "author", "image_url"):
            if detail.get(key):
                article[key] = detail[key]
    return articles


def extract_article_links(page_html: str, category: str) -> list[dict]:
    articles: list[dict] = []
    seen: set[str] = set()
    pattern = re.compile(r'<a[^>]+href=["\']([^"\']+/a/\d{6}/\d{2}/[^"\']+?\.html)["\'][^>]*>(.*?)</a>', re.I | re.S)
    for match in pattern.finditer(page_html):
        link = normalize_url(match.group(1))
        if link in seen:
            continue
        title = clean_text(match.group(2))
        if len(title) < 8:
            continue
        seen.add(link)
        articles.append(
            {
                "title": title,
                "link": link,
                "summary": "",
                "excerpt": "",
                "body": "",
                "author": "",
                "category": category,
                "published": published_from_url(link),
                "source": "China Daily",
            }
        )
    return articles


def fetch_article_detail(article_url: str) -> dict:
    with httpx.Client(timeout=15, follow_redirects=True, headers=HEADERS) as client:
        response = client.get(article_url)
        response.raise_for_status()
    page_html = response.text
    title = first_match_text(page_html, r"<h1[^>]*>(.*?)</h1>")
    body_html = first_match(page_html, r'<div[^>]+id=["\']Content["\'][^>]*>(.*?)</div>\s*</div>', flags=re.I | re.S)
    if not body_html:
        body_html = first_match(page_html, r'<div[^>]+class=["\'][^"\']*(?:article|content|main_art)[^"\']*["\'][^>]*>(.*?)</div>', flags=re.I | re.S)
    body = html_to_text(body_html or "")
    paragraphs = [line.strip() for line in body.splitlines() if line.strip()]
    summary = paragraphs[0] if paragraphs else ""
    return {
        "title": title,
        "summary": summary,
        "excerpt": "\n".join(paragraphs[:2])[:420],
        "body": body,
        "image_url": extract_main_image(page_html, article_url),
        "published": published_from_url(article_url),
        "source": "China Daily",
    }


def extract_main_image(page_html: str, article_url: str) -> str:
    meta_patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
    ]
    for pattern in meta_patterns:
        image_url = normalize_url(first_match(page_html, pattern), base_url=article_url)
        if is_news_image(image_url):
            return image_url

    attr_pattern = re.compile(
        r'<img[^>]+(?:data-original|data-src|src)=["\']([^"\']+)["\'][^>]*>',
        re.I | re.S,
    )
    for match in attr_pattern.finditer(page_html):
        image_url = normalize_url(match.group(1), base_url=article_url)
        if is_news_image(image_url):
            return image_url
    return ""


def is_news_image(value: str) -> bool:
    if not value:
        return False
    lowered = value.lower()
    blocked = (
        "spacer",
        "logo",
        "icon",
        "search",
        "qr",
        "avatar",
        "image_e/",
        "button",
        "banner",
    )
    if any(token in lowered for token in blocked):
        return False
    return bool(re.search(r"\.(?:jpg|jpeg|png|webp)(?:\?|$)", lowered))


def normalize_url(value: str, base_url: str = CHINADAILY_HOME) -> str:
    if not value:
        return ""
    if value.startswith("//"):
        return "https:" + value
    return urljoin(base_url, value)


def published_from_url(value: str) -> str:
    match = re.search(r"/a/(\d{4})(\d{2})/(\d{2})/", value)
    if not match:
        return ""
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"


def first_match(page_html: str, pattern: str, flags: int = re.I | re.S) -> str:
    match = re.search(pattern, page_html, flags)
    return match.group(1) if match else ""


def first_match_text(page_html: str, pattern: str) -> str:
    return clean_text(first_match(page_html, pattern))


def clean_text(value: str) -> str:
    return " ".join(html_to_text(value).split())


def html_to_text(value: str) -> str:
    value = re.sub(r"(?is)<(script|style).*?</\1>", " ", value or "")
    value = re.sub(r"(?i)<br\s*/?>|</p\s*>|</div\s*>|</li\s*>|</h\d\s*>", "\n", value)
    value = re.sub(r"(?s)<[^>]+>", " ", value)
    value = html.unescape(value)
    value = re.sub(r"[ \t\r\f\v]+", " ", value)
    value = re.sub(r"\n\s*\n+", "\n", value)
    return value.strip()
