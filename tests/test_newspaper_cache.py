import json
import os
import unittest
from copy import deepcopy
from datetime import date, datetime, timedelta
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.database import Base
from app.models import CacheEntry, Word
from app import main as m
from app.services import newspaper_cache as n

URL = "https://www.chinadaily.com.cn/a/202609/06/content_123456.html"
ARTICLE = {"title": "A sample article", "link": URL, "body": "Full article body.", "summary": "Summary."}


def payload():
    return {"source": "China Daily", "source_url": "https://www.chinadaily.com.cn/",
            "loaded_at": datetime.now().isoformat(), "edition_date": date.today().isoformat(),
            "sections": [{"key": "today", "name": "Today", "articles": [deepcopy(ARTICLE)], "error": None}]}


class NewspaperCacheTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.cache = n.NewspaperCache(sessionmaker(bind=self.engine))
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)

    def seed(self, data=None, key=n.LIST_KEY, ttl=n.LIST_TTL):
        self.cache.store(self.db, key, data or payload(), ttl)
        self.db.commit()

    def test_fresh_snapshot_is_immediate_and_omits_bodies(self):
        self.seed()
        with patch.object(self.cache, "schedule_refresh") as refresh, patch.object(n, "load_chinadaily_articles") as source:
            result = self.cache.list_payload(self.db)
        self.assertFalse(result["cache"]["stale"])
        self.assertNotIn("body", result["sections"][0]["articles"][0])
        self.assertIn("body", self.cache.snapshot(self.db)[0]["sections"][0]["articles"][0])
        refresh.assert_not_called()
        source.assert_not_called()

    def test_yesterday_and_legacy_cache_are_shown_while_refreshing(self):
        data = payload()
        data["edition_date"] = (date.today() - timedelta(days=1)).isoformat()
        self.seed(data, key="chinadaily:list:2026-09-05:6")
        with patch.object(self.cache, "schedule_refresh") as refresh:
            result = self.cache.list_payload(self.db)
        self.assertEqual(result["sections"][0]["articles"][0]["title"], ARTICLE["title"])
        self.assertTrue(result["cache"]["stale"])
        refresh.assert_called_once()

    def test_initial_empty_cache_never_blocks_on_upstream(self):
        with patch.object(self.cache, "schedule_refresh"), patch.object(n, "load_chinadaily_articles") as source:
            self.assertEqual(self.cache.list_payload(self.db)["sections"], [])
        source.assert_not_called()

    def test_refresh_is_deduplicated_and_throttled(self):
        with patch.object(n, "Thread") as thread:
            self.assertTrue(self.cache.schedule_refresh())
            self.assertFalse(self.cache.schedule_refresh())
            self.cache._refreshing = False
            self.assertFalse(self.cache.schedule_refresh())
            thread.assert_called_once()

    def test_upstream_failure_does_not_overwrite_last_good_snapshot(self):
        self.seed()
        before = self.db.get(CacheEntry, n.LIST_KEY).payload
        with patch.object(n, "load_chinadaily_articles", return_value={"sections": []}), patch.object(n.LOGGER, "warning"):
            self.cache._refresh()
        self.db.expire_all()
        self.assertEqual(self.db.get(CacheEntry, n.LIST_KEY).payload, before)
        self.assertTrue(self.cache._last_error)

    def test_partial_failure_retains_old_section_and_duplicate_articles_are_safe(self):
        self.seed()
        new = payload()
        new["sections"] = [
            {"key": "today", "articles": [], "error": "timeout"},
            {"key": "china", "articles": [deepcopy(ARTICLE)], "error": None},
            {"key": "world", "articles": [deepcopy(ARTICLE)], "error": None},
        ]
        with patch.object(n, "load_chinadaily_articles", return_value=new):
            self.cache._refresh()
        self.db.expire_all()
        saved = json.loads(self.db.get(CacheEntry, n.LIST_KEY).payload)
        self.assertTrue(saved["sections"][0]["stale"])
        self.assertIsNone(saved["sections"][0]["error"])
        self.assertEqual(saved["sections"][0]["articles"][0]["body"], ARTICLE["body"])
        self.assertIsNotNone(self.db.get(CacheEntry, n.article_cache_key(URL)))
        self.assertFalse(self.cache._last_error)

    def test_pinned_article_uses_url_not_changed_list_position(self):
        self.seed()
        self.seed(ARTICLE, key=n.article_cache_key(URL), ttl=n.ARTICLE_TTL)
        with patch.object(n, "fetch_article_detail") as source:
            result = self.cache.article_payload(self.db, "today", 99, URL)
        self.assertEqual(result["article"]["link"], URL)
        source.assert_not_called()

    def test_first_article_visit_reuses_body_from_snapshot(self):
        self.seed()
        with patch.object(n, "fetch_article_detail") as source:
            result = self.cache.article_payload(self.db, "today", 0)
        self.assertEqual(result["article"]["body"], ARTICLE["body"])
        source.assert_not_called()

    def test_legacy_snapshot_fetches_only_the_selected_article_once(self):
        data = payload()
        data["sections"][0]["articles"][0].pop("body")
        self.seed(data)
        with patch.object(n, "fetch_article_detail", return_value={"body": "Downloaded once."}) as source:
            first = self.cache.article_payload(self.db, "today", 0)
            second = self.cache.article_payload(self.db, "today", 0)
        self.assertEqual(first, second)
        source.assert_called_once_with(URL)

    def test_expired_article_survives_upstream_failure(self):
        self.seed()
        self.seed(ARTICLE, key=n.article_cache_key(URL), ttl=timedelta(seconds=-1))
        with patch.object(n, "fetch_article_detail", side_effect=RuntimeError("network")):
            self.assertEqual(self.cache.article_payload(self.db, "today", 0)["article"]["body"], ARTICLE["body"])

    def test_arbitrary_hosts_ports_and_redirect_queries_are_rejected(self):
        for url in ["http://127.0.0.1/a/202609/06/test.html", URL + "?redirect=http://localhost", URL.replace(".com.cn", ".com.cn.evil.test"), URL.replace(".com.cn", ".com.cn:8888")]:
            with self.assertRaises(ValueError):
                self.cache.article_payload(self.db, "today", 0, url)


class WordDetailCacheTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.word = Word(word="fomentation")
        self.db.add(self.word)
        self.db.commit()
        m.word_detail_cache.clear()
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)
        self.addCleanup(m.word_detail_cache.clear)

    def read(self, edit=1, list_id=204):
        return m.vue_word_detail_api(self.word.id, edit=edit, list_id=list_id, challenge_day=None, challenge_status=None, db=self.db)

    def test_hits_are_isolated_by_word_revision_and_navigation_context(self):
        with patch.object(m, "word_detail_payload", return_value={"word": {"word": "fomentation"}}) as build:
            self.read()["word"]["word"] = "do not leak"
            self.assertEqual(self.read()["word"]["word"], "fomentation")
            self.assertEqual(build.call_count, 1)
            self.read(edit=0)
            self.read(list_id=205)
            self.assertEqual(build.call_count, 3)
            self.word.updated_at += timedelta(seconds=1)
            self.db.commit()
            self.read()
            self.assertEqual(build.call_count, 4)
            m.word_detail_cache.clear()
            self.read()
            self.assertEqual(build.call_count, 5)

    def test_audio_urls_remain_stable_until_word_changes(self):
        with patch.object(m, "apply_word_resource"), patch.object(m, "word_navigation_context", return_value={}), \
             patch.object(m, "word_media_sources", return_value={}), patch.object(m, "word_membership_tags", return_value=[]):
            first = m.word_detail_payload(self.db, self.word, 1, None, None, None)["audio_sources"]
            second = m.word_detail_payload(self.db, self.word, 1, None, None, None)["audio_sources"]
            self.assertEqual(first, second)
            self.word.updated_at += timedelta(seconds=1)
            changed = m.word_detail_payload(self.db, self.word, 1, None, None, None)["audio_sources"]
            self.assertNotEqual(first, changed)


if __name__ == "__main__":
    unittest.main()
