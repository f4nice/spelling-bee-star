"""Persistent, stale-while-refreshing newspaper snapshots and URL-keyed articles."""

from copy import deepcopy
from datetime import date, datetime, timedelta
from hashlib import sha256
import json
import logging
import re
from threading import Lock, Thread
from time import monotonic
from urllib.parse import urlparse

from sqlalchemy import select

from app.models import CacheEntry
from app.services.chinadaily import CHINADAILY_HOME, SECTIONS, fetch_article_detail, load_chinadaily_articles

LIST_KEY = "chinadaily:list:v2:6"
LIST_TTL = timedelta(minutes=45)
ARTICLE_TTL = timedelta(hours=6)
LOGGER = logging.getLogger(__name__)


def article_cache_key(url):
    return "chinadaily:article:v2:" + sha256(url.encode()).hexdigest()


def valid_article_url(url):
    try:
        parsed = urlparse(url)
        return (
            parsed.scheme == "https" and parsed.hostname in {"www.chinadaily.com.cn", "chinadaily.com.cn"}
            and parsed.port in {None, 443} and not parsed.username and not parsed.password
            and not parsed.query and not parsed.fragment
            and bool(re.fullmatch(r"/a/\d{6}/\d{2}/[A-Za-z0-9_-]+\.html", parsed.path))
        )
    except ValueError:
        return False


def has_articles(payload):
    return isinstance(payload, dict) and any(section.get("articles") for section in payload.get("sections", []))


class NewspaperCache:
    def __init__(self, session_factory):
        self.session_factory = session_factory
        self._lock = Lock()
        self._refreshing = False
        self._next_retry = 0
        self._last_error = ""

    def snapshot(self, db):
        entry = db.get(CacheEntry, LIST_KEY)
        if entry:
            payload = json.loads(entry.payload)
            if has_articles(payload):
                return payload, entry.expires_at
        # Reuse existing data immediately, including yesterday's newspaper.
        for entry in db.scalars(
            select(CacheEntry).where(CacheEntry.key.like("chinadaily:list:%"))
            .order_by(CacheEntry.updated_at.desc()).limit(8)
        ):
            payload = json.loads(entry.payload)
            if has_articles(payload):
                return payload, datetime.min
        return {"source": "China Daily", "source_url": CHINADAILY_HOME, "sections": []}, datetime.min

    def list_payload(self, db, force=False):
        payload, expires_at = self.snapshot(db)
        stale = expires_at <= datetime.utcnow() or payload.get("edition_date") != date.today().isoformat()
        if force or stale:
            self.schedule_refresh()
        result = deepcopy(payload)
        # Full bodies remain on the server; list navigation stays lightweight.
        for section in result.get("sections", []):
            for article in section.get("articles", []):
                article.pop("body", None)
        with self._lock:
            result["cache"] = {"refreshing": self._refreshing, "stale": stale, "error": self._last_error}
        return result

    def schedule_refresh(self):
        with self._lock:
            if self._refreshing or monotonic() < self._next_retry:
                return False
            self._refreshing = True
            self._next_retry = monotonic() + 30
            self._last_error = ""
        Thread(target=self._refresh, daemon=True, name="newspaper-cache-refresh").start()
        return True

    @staticmethod
    def store(db, key, payload, ttl):
        entry = db.get(CacheEntry, key)
        if entry is None:
            entry = CacheEntry(key=key)
            db.add(entry)
        entry.payload = json.dumps(payload, ensure_ascii=False)
        entry.expires_at = datetime.utcnow() + ttl

    def _refresh(self):
        try:
            # No request-scoped session is passed into the background thread.
            fresh = load_chinadaily_articles(limit_per_feed=6)
            if not has_articles(fresh):
                raise ValueError("No usable newspaper sections returned")
            with self.session_factory() as db:
                old, _ = self.snapshot(db)
                old_sections = {section["key"]: section for section in old.get("sections", [])}
                stored_urls = set()
                for index, section in enumerate(fresh["sections"]):
                    if not section.get("articles") and old_sections.get(section["key"], {}).get("articles"):
                        fresh["sections"][index] = {**old_sections[section["key"]], "error": None, "stale": True}
                        continue
                    for article in section.get("articles", []):
                        if article.get("body") and valid_article_url(article.get("link", "")) and article["link"] not in stored_urls:
                            self.store(db, article_cache_key(article["link"]), article, ARTICLE_TTL)
                            stored_urls.add(article["link"])
                fresh["edition_date"] = date.today().isoformat()
                self.store(db, LIST_KEY, fresh, LIST_TTL)
                db.commit()
        except Exception:
            LOGGER.warning("Newspaper refresh failed; retaining last successful snapshot", exc_info=True)
            with self._lock:
                self._last_error = "新闻源暂时不可用，已保留上次内容，请稍后再试。"
        finally:
            with self._lock:
                self._refreshing = False

    def article_payload(self, db, section_key, article_index, url=""):
        section_config = next((section for section in SECTIONS if section.key == section_key), None)
        if not section_config or article_index < 0:
            raise ValueError("Article not found")
        snapshot, snapshot_expires = self.snapshot(db)
        section = next((item for item in snapshot["sections"] if item["key"] == section_key), {})
        articles = section.get("articles", [])
        if url:
            if not valid_article_url(url):
                raise ValueError("Invalid article URL")
            article = next((item for item in articles if item.get("link") == url), {"link": url})
        else:
            if article_index >= len(articles):
                raise IndexError("Article not found")
            article = articles[article_index]
            url = article.get("link", "")
            if not valid_article_url(url):
                raise ValueError("Invalid article URL")
        entry = db.get(CacheEntry, article_cache_key(url))
        cached = json.loads(entry.payload) if entry else None
        if cached and entry.expires_at > datetime.utcnow():
            result = cached
        else:
            result = deepcopy(article)
            try:
                if not result.get("body") or (entry and entry.expires_at <= datetime.utcnow()) or snapshot_expires <= datetime.utcnow():
                    result.update({key: value for key, value in fetch_article_detail(url).items() if value})
                if not result.get("body"):
                    raise ValueError("Article body is temporarily unavailable")
                self.store(db, article_cache_key(url), result, ARTICLE_TTL)
                db.commit()
            except Exception:
                db.rollback()
                if not cached and not article.get("body"):
                    raise
                result = cached or article
        return {"section": {"key": section_key, "name": section_config.name}, "article": result}
