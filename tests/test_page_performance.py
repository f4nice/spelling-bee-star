import asyncio
import os
import unittest
from datetime import date, timedelta
from unittest.mock import Mock, patch

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route
from starlette.testclient import TestClient

from app import main as m
from app.database import Base
from app.models import ChallengeDailyWord, ChallengeProgress, ChallengeSpellingAttempt, Word, WordList, WordListItem, WrongWord
from app.services.page_performance import PublicStatsCache, TextAssetGZipMiddleware, batch_challenge_states, batch_word_list_cards


class PagePerformanceTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        m.public_stats_cache.clear()
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)
        self.addCleanup(m.public_stats_cache.clear)

    def make_lists(self, count=4):
        words = [Word(word=f"word{i}", image_url="/media/cover.png" if i == 2 else None) for i in range(5)]
        lists = [WordList(name=f"list{i}") for i in range(count)]
        self.db.add_all(words + lists)
        self.db.flush()
        for item in lists:
            self.db.add(ChallengeProgress(word_list_id=item.id, completed_count=0, completed_rounds=0))
            self.db.add_all([WordListItem(word_list_id=item.id, word_id=word.id) for word in words])
        self.db.commit()
        return lists, words

    def test_batch_history_matches_legacy_including_unscoped_attempts(self):
        lists, words = self.make_lists()
        self.db.add_all([
            ChallengeDailyWord(challenge_date=date(2026, 8, 1), word_id=words[0].id, word_list_id=lists[0].id, correct_count=1),
            ChallengeDailyWord(challenge_date=date(2026, 8, 2), word_id=words[1].id, word_list_id=None, wrong_count=1),
            ChallengeSpellingAttempt(word_id=words[2].id, word_list_id=lists[1].id, typed_spelling="x", normalized_spelling="x", expected_spellings="[]"),
            ChallengeSpellingAttempt(word_id=words[3].id, word_list_id=None, typed_spelling="x", normalized_spelling="x", expected_spellings="[]"),
        ])
        self.db.commit()
        expected = {item.id: m.challenge_state(self.db, item) for item in lists}
        actual = batch_challenge_states(self.db, lists, m.challenge_state)
        self.assertEqual(actual, expected)
        self.assertEqual(actual[lists[0].id]["completed"], 2)
        self.assertEqual(actual[lists[2].id]["completed"], 1)

    def test_legacy_round_rollover_and_missing_progress_are_preserved(self):
        lists, words = self.make_lists(2)
        progress = self.db.query(ChallengeProgress).filter_by(word_list_id=lists[0].id).one()
        progress.completed_count = len(words)
        self.db.query(ChallengeProgress).filter_by(word_list_id=lists[1].id).delete()
        empty = WordList(name="empty")
        self.db.add(empty)
        self.db.commit()
        fallback = Mock(wraps=m.challenge_state)
        states = batch_challenge_states(self.db, lists + [empty], fallback)
        self.assertEqual(fallback.call_count, 2)
        self.assertEqual(states[lists[0].id]["completed_rounds"], 1)
        self.assertEqual(states[lists[0].id]["completed"], 0)
        self.assertEqual(states[empty.id]["total"], 0)

    def test_100_cards_need_at_most_five_queries(self):
        lists, words = self.make_lists(100)
        queries = []
        def record(*args):
            queries.append(args[2])
        event.listen(self.engine, "before_cursor_execute", record)
        try:
            cards = batch_word_list_cards(self.db, lists, m.challenge_state)
        finally:
            event.remove(self.engine, "before_cursor_execute", record)
        self.assertLessEqual(len(queries), 5)
        self.assertEqual(len(cards), 100)
        self.assertTrue(all(card["count"] == 5 for card in cards))
        self.assertTrue(all(card["cover_word"].id == words[2].id for card in cards))

    def test_pending_wrong_count_matches_legacy_union_and_correction_dates(self):
        lists, words = self.make_lists(1)
        day = date(2026, 8, 1)
        wrong_list = WordList(name=f"生词本 {day}")
        duplicate = WordList(name=f"生词本 {day}")
        self.db.add_all([wrong_list, duplicate])
        self.db.flush()
        self.db.add_all([
            WordListItem(word_list_id=wrong_list.id, word_id=words[0].id),
            WordListItem(word_list_id=duplicate.id, word_id=words[4].id),
            WrongWord(word_id=words[0].id, wrong_date=day),
            WrongWord(word_id=words[1].id, wrong_date=day),
            WrongWord(word_id=words[1].id, wrong_date=day + timedelta(days=3)),
            ChallengeDailyWord(word_id=words[1].id, challenge_date=day + timedelta(days=1), correct_count=1),
            ChallengeDailyWord(word_id=words[2].id, challenge_date=day, wrong_count=1),
            ChallengeDailyWord(word_id=words[2].id, challenge_date=day - timedelta(days=1), correct_count=1),
        ])
        self.db.commit()
        expected = sum(len(m.challenge_day_pending_wrong_word_ids(self.db, item)) for item in m.wrong_word_dates(self.db))
        self.assertEqual(m.pending_wrong_word_count(self.db), expected)
        self.assertEqual(expected, 3)

    def test_shell_never_reuses_another_account(self):
        request = Request({"type": "http", "headers": [], "path": "/api/vue/shell"})
        with patch.object(m, "authenticated_phone_from_request", side_effect=["account-a", "account-b"]), \
             patch.object(m, "get_or_create_admin_user", return_value=None), \
             patch.object(m, "admin_user_summary", side_effect=lambda admin, phone: {"phone": phone}), \
             patch.object(m, "get_daily_quote", return_value=None), \
             patch.object(m, "sidebar_challenge_progress", return_value=[]), \
             patch.object(m, "pending_wrong_word_count", return_value=7) as stats, \
             patch.object(m, "learning_growth_summary", return_value={"points": 12}), \
             patch.object(m, "ensure_version_matrix_file", return_value={}):
            first = m.vue_shell_api(request, self.db)
            second = m.vue_shell_api(request, self.db)
        self.assertEqual(first["currentUser"]["phone"], "account-a")
        self.assertEqual(second["currentUser"]["phone"], "account-b")
        self.assertEqual(stats.call_count, 1)


class PageDeliveryTest(unittest.TestCase):
    def test_cache_ttl_copy_isolation_and_invalidation(self):
        cache = PublicStatsCache(ttl=10)
        producer = Mock(return_value={"items": [1]})
        with patch("app.services.page_performance.monotonic", return_value=100):
            cache.get("db", producer)["items"].append(2)
            self.assertEqual(cache.get("db", producer), {"items": [1]})
            self.assertEqual(producer.call_count, 1)
        with patch("app.services.page_performance.monotonic", return_value=111):
            cache.get("db", producer)
        self.assertEqual(producer.call_count, 2)
        cache.clear()
        cache.get("db", producer)
        self.assertEqual(producer.call_count, 3)

    def test_compression_only_for_text_and_never_range(self):
        async def body(request):
            return Response("hello world " * 1000)
        app = Starlette(routes=[Route("/{path:path}", body)])
        app.add_middleware(TextAssetGZipMiddleware)
        with TestClient(app) as client:
            for path in ("/static/vue/game-AbCd1234.js", "/static/styles.css", "/api/vue/home"):
                response = client.get(path, headers={"Accept-Encoding": "gzip"})
                self.assertEqual(response.headers.get("Content-Encoding"), "gzip")
                self.assertLess(int(response.headers["Content-Length"]), 1000)
                self.assertEqual(len(response.content), 12000)
            for path in ("/login", "/media/audio/test.mp3"):
                self.assertNotIn("Content-Encoding", client.get(path).headers)
            self.assertNotIn("Content-Encoding", client.get("/static/styles.css", headers={"Range": "bytes=0-99"}).headers)

    def test_entry_revalidates_hashed_chunks_cache_and_mutations_invalidate(self):
        async def run(path, method="GET"):
            request = Request({"type": "http", "headers": [], "path": path, "method": method})
            async def next_handler(request):
                return Response("ok")
            return await m.add_cache_headers(request, next_handler)
        for path in ("/static/vue/app.css", "/static/vue/speakeasy-app.js"):
            self.assertIn("must-revalidate", asyncio.run(run(path)).headers["Cache-Control"])
        self.assertIn("immutable", asyncio.run(run("/static/vue/game-AbCd1234.js")).headers["Cache-Control"])
        with patch.object(m.public_stats_cache, "clear") as clear:
            asyncio.run(run("/api/challenge/1/answer", "POST"))
            clear.assert_called_once()
            asyncio.run(run("/api/vue/cat-world/play-time", "POST"))
            clear.assert_called_once()


if __name__ == "__main__":
    unittest.main()
