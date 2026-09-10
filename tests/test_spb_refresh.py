import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from app import main as m
from app.database import Base
from app.models import Word, WordList, WordListItem


class SpbRefreshTest(unittest.TestCase):
    def category_group(self):
        return {
            "key": "origin", "title": "词源单词", "subtitle": "Language Origin",
            "prefix": "SPB个人赛冠军词库-词源单词", "list_layout": "source_categories",
            "prefer_cached_source": True, "spb_product_id": 6,
            "sources": [
                {"key": "arabic", "title": "Arabic", "spb_flag": "Arabic", "source_file": "arabic.json"},
                {"key": "french", "title": "French", "spb_flag": "French", "source_file": "french.json"},
            ],
        }

    def test_explicit_category_refresh_bypasses_existing_cache_and_retains_raw_fields(self):
        group = self.category_group()
        live = {
            "Arabic": {"words": [{"id": 101, "word": "adjar", "kernel": "one"}]},
            "French": {"words": [{
                "id": 202, "word": "baguette", "kernel": "two", "internationalPhoneticAlphabet": "/baˈɡɛt/",
                "def": "a long thin loaf", "chinesemeaning": "法式长棍面包", "exp": "She bought a baguette.",
                "wordCompoundAudio": {"sentenceUrl": "https://example.test/baguette.mp3"},
            }]},
        }
        with tempfile.TemporaryDirectory() as temporary, patch.object(m, "MEDIA_DIR", Path(temporary)), \
             patch.object(m, "spb_source_dirs", return_value=[Path(temporary) / "spb"]):
            for source in m.spb_group_source_variants(group):
                self.assertTrue(m.cache_spb_miniprogram_source(source, {"words": [{"id": 1, "word": "old"}]}))
            with patch.object(m, "spb_miniprogram_get", side_effect=lambda _endpoint, params: live[params["code"]]) as api, \
                 patch.object(m, "fetch_spb_source_rows_from_url") as public:
                rows, _source = m.load_spb_source_rows(group, force_refresh=True)
                self.assertEqual(api.call_count, 2)
                public.assert_not_called()
            self.assertEqual([(row["word"], row["spb_word_id"], row["spb_category_key"]) for row in rows],
                             [("adjar", "101", "arabic"), ("baguette", "202", "french")])
            self.assertEqual(json.loads((Path(temporary) / "spb" / "french.json").read_text(encoding="utf-8")), live["French"])
            # Reading the fresh index does not issue fourteen new downloads per word.
            with patch.object(m, "spb_miniprogram_get") as api, patch.object(m, "fetch_spb_source_rows_from_url") as public:
                cached_rows, _source = m.load_spb_source_rows(group)
                self.assertEqual(cached_rows, rows)
                api.assert_not_called()
                public.assert_not_called()
            self.assertEqual(cached_rows[1]["phonetic"], "/baˈɡɛt/")
            self.assertEqual(cached_rows[1]["english_example"], "She bought a baguette.")
            self.assertEqual(cached_rows[1]["spb_product_flag"], "French")
            self.assertEqual(cached_rows[1]["spb_kernel"], "two")

    def test_partial_live_category_failure_keeps_old_cache_and_never_imports_partial_group(self):
        group = self.category_group()
        job_id = "test-origin-partial-live"
        m.SPB_SYNC_JOBS[job_id] = {"status": "queued"}
        try:
            with tempfile.TemporaryDirectory() as temporary, patch.object(m, "MEDIA_DIR", Path(temporary)), \
                 patch.object(m, "spb_source_dirs", return_value=[Path(temporary) / "spb"]):
                for source in m.spb_group_source_variants(group):
                    m.cache_spb_miniprogram_source(source, {"words": [{"id": 1, "word": "old"}]})
                old_french = (Path(temporary) / "spb" / "french.json").read_bytes()
                with patch.object(m, "spb_miniprogram_get", side_effect=[{"words": [{"id": 101, "word": "adjar"}]}, None]) as api, \
                     patch.object(m, "fetch_spb_source_rows_from_url") as public:
                    rows, _source = m.load_spb_source_rows(group, force_refresh=True)
                    self.assertEqual(rows, [])
                    self.assertEqual(api.call_count, 2)
                    public.assert_not_called()
                self.assertEqual((Path(temporary) / "spb" / "french.json").read_bytes(), old_french)
                self.assertIn("adjar", (Path(temporary) / "spb" / "arabic.json").read_text(encoding="utf-8"))
                with patch.object(m, "SessionLocal"), patch.object(m, "spb_collection_by_key", return_value={"groups": [group]}), \
                     patch.object(m, "spb_miniprogram_get", side_effect=[None, {"words": [{"id": 202, "word": "baguette"}]}]) as api, \
                     patch.object(m, "append_missing_spb_words") as append:
                    m.run_spb_refresh_all_job(job_id, "individual")
                    self.assertEqual(api.call_count, 2)
                    append.assert_not_called()
                job = m.spb_sync_job_snapshot(job_id)
                self.assertEqual(job["status"], "failed")
                self.assertEqual(job["results"][0]["status"], "failed")
                # The later successful category is still cached for normal lookups.
                self.assertIn("baguette", (Path(temporary) / "spb" / "french.json").read_text(encoding="utf-8"))
        finally:
            m.SPB_SYNC_JOBS.pop(job_id, None)

    def test_source_cache_write_failure_is_atomic_and_invalid_payload_keeps_previous_file(self):
        source = self.category_group()["sources"][0]
        with tempfile.TemporaryDirectory() as temporary, patch.object(m, "MEDIA_DIR", Path(temporary)):
            self.assertTrue(m.cache_spb_miniprogram_source(source, {"words": [{"id": 1, "word": "old"}]}))
            path = Path(temporary) / "spb" / "arabic.json"
            original = path.read_bytes()
            with patch.object(Path, "replace", side_effect=OSError("test replacement failure")), \
                 self.assertLogs("speakeasy.spb", level="WARNING"):
                self.assertFalse(m.cache_spb_miniprogram_source(source, {"words": [{"id": 2, "word": "new"}]}))
            self.assertEqual(path.read_bytes(), original)
            self.assertFalse(m.cache_spb_miniprogram_source(source, {"words": []}))
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(list(path.parent.glob("*.tmp")), [])
            self.assertFalse(m.cache_spb_miniprogram_source({"source_file": "../escape.json"}, {"words": ["bad"]}))

    def test_origin_catalog_finds_new_cached_word_without_network_and_reuses_provider_id(self):
        group = self.category_group()
        with tempfile.TemporaryDirectory() as temporary, patch.object(m, "MEDIA_DIR", Path(temporary)), \
             patch.object(m, "spb_source_dirs", return_value=[Path(temporary) / "spb"]), \
             patch.object(m, "all_spb_word_bank_groups", return_value=[group]):
            for source in m.spb_group_source_variants(group):
                word = "adjar" if source["key"] == "arabic" else "baguette"
                m.cache_spb_miniprogram_source(source, {"words": [{"id": 202, "word": word}]})
            with patch.object(m, "spb_miniprogram_get") as api, patch.object(m, "fetch_spb_source_rows_from_url") as public:
                self.assertEqual(m.spb_catalog_groups_for_word("BAGUETTE"), [group])
                row = m.find_spb_source_row_for_word(group, "baguette")
                self.assertEqual(row["spb_word_id"], "202")
                self.assertEqual(row["spb_category_key"], "french")
                api.assert_not_called()
                public.assert_not_called()
            with patch.object(m, "spb_miniprogram_get_async", new_callable=AsyncMock, return_value={"def": "a long thin loaf"}) as detail:
                asyncio.run(m.fetch_spb_word_detail_from_miniprogram(row, group))
                detail.assert_awaited_once_with(m.SPB_MINIPROGRAM_WORD_DETAIL_ENDPOINT, {"id": "202", "productFlag": "French"})

    def test_category_source_count_uses_updated_cache_instead_of_static_catalog_total(self):
        group = {**self.category_group(), "source_count": 2060}
        with tempfile.TemporaryDirectory() as temporary, patch.object(m, "MEDIA_DIR", Path(temporary)), \
             patch.object(m, "spb_source_dirs", return_value=[Path(temporary) / "spb"]), \
             patch.object(m, "spb_word_lists_for_group", return_value=[]), \
             patch.object(m, "batch_word_list_cards", return_value=[]):
            for source in m.spb_group_source_variants(group):
                m.cache_spb_miniprogram_source(source, {"words": [{"id": 1, "word": "example"}]})
            payload = m.serialize_spb_word_bank_group(None, group)
            self.assertEqual(payload["source_count"], 2)
            self.assertEqual(payload["cached_source_count"], 2)

    def test_explicit_sync_routes_fetch_in_worker_and_only_require_live_for_categories(self):
        for layout in ("source_categories", "chunks"):
            for endpoint in (m.vue_spb_sync_api, m.vue_spb_backfill_details_api):
                for authorized in (False, True):
                    with self.subTest(layout=layout, endpoint=endpoint.__name__, authorized=authorized):
                        group = {**self.category_group(), "list_layout": layout}
                        request = AsyncMock()
                        request.json.return_value = {"collection": "individual", "key": "origin"}
                        with patch.object(m, "spb_collection_group_by_keys", return_value=({"key": "individual"}, group)), \
                             patch.object(m, "spb_active_sync_job_for_collection", return_value=None), \
                             patch.object(m, "spb_words_for_group", return_value=[object()]), \
                             patch.object(m, "spb_miniprogram_authorization_configured", return_value=authorized), \
                             patch.object(m.asyncio, "to_thread", new_callable=AsyncMock, return_value=([], Path("missing.json"))) as threaded, \
                             patch.object(m, "append_missing_spb_words") as append:
                            with self.assertRaises(m.HTTPException) as raised:
                                asyncio.run(endpoint(request, None))
                            threaded.assert_awaited_once_with(m.load_spb_source_rows, group, force_refresh=layout == "source_categories")
                            append.assert_not_called()
                            if layout == "source_categories":
                                self.assertIn("已有缓存和词表保留", raised.exception.detail)
                                self.assertIn("全部" if authorized else "授权", raised.exception.detail)

    def test_language_origin_catalog_has_fourteen_category_sources(self):
        group = m.spb_collection_group_by_keys("individual", "origin")[1]
        sources = m.spb_group_source_variants(group)
        self.assertEqual(len(sources), 14)
        self.assertEqual(sum(source["source_count"] for source in sources), 2060)
        with patch.object(m, "spb_source_dirs", return_value=[m.BASE_DIR.parent / "spb_sources"]):
            self.assertEqual(m.count_spb_cached_source_words(group), 2060)
        self.assertEqual(
            [source["title"] for source in sources],
            [
                "Arabic", "Asian Languages", "Dutch", "Eponyms", "French", "German", "Greek",
                "Italian", "Japanese", "Latin", "New World Languages", "Old English",
                "Slavic Languages", "Spanish",
            ],
        )

    def test_category_sources_are_combined_with_category_identity(self):
        group = {
            "key": "origin",
            "sources": [
                {"key": "arabic", "title": "Arabic", "source_url": "https://example.test/arabic"},
                {"key": "dutch", "title": "Dutch", "source_url": "https://example.test/dutch"},
            ],
        }
        public_rows = [([{"word": "adjar"}], Path("arabic.json")), ([{"word": "beaker"}], Path("dutch.json"))]
        with patch.object(m, "fetch_spb_source_rows_from_miniprogram", return_value=([], Path())), \
             patch.object(m, "fetch_spb_source_rows_from_url", side_effect=public_rows):
            rows, source = m.load_spb_source_rows(group)
        self.assertEqual(source.name, "origin-categories.json")
        self.assertEqual(
            [(row["word"], row["spb_category_key"], row["spb_category_title"]) for row in rows],
            [("adjar", "arabic", "Arabic"), ("beaker", "dutch", "Dutch")],
        )

    def test_language_origin_import_creates_one_list_per_category(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        group = {
            "key": "origin",
            "title": "词源单词",
            "subtitle": "Language Origin",
            "prefix": "SPB个人赛冠军词库-词源单词",
            "list_layout": "source_categories",
            "sources": [
                {"key": "arabic", "title": "Arabic"},
                {"key": "dutch", "title": "Dutch"},
            ],
        }
        rows = [
            {"word": "adjar", "spb_category_key": "arabic"},
            {"word": "beaker", "spb_category_key": "dutch"},
            {"word": "bluff", "spb_category_key": "dutch"},
        ]
        with Session(engine) as db:
            word_ids, lists = m.import_spb_word_bank_rows(db, group, rows)
            self.assertEqual(len(word_ids), 3)
            self.assertEqual(
                [word_list.name for word_list in lists],
                [
                    "SPB个人赛冠军词库-词源单词-Arabic",
                    "SPB个人赛冠军词库-词源单词-Dutch",
                ],
            )
            self.assertEqual(
                [db.scalar(select(func.count(WordListItem.id)).where(WordListItem.word_list_id == word_list.id)) for word_list in lists],
                [1, 2],
            )
            before = set(db.execute(select(WordListItem.id, WordListItem.word_id, WordListItem.word_list_id)).all())
            list_ids = [word_list.id for word_list in lists]
            self.assertEqual(m.append_missing_spb_words(db, group, rows + [{"word": "berg", "spb_category_key": "dutch"}]), 1)
            self.assertEqual(m.append_missing_spb_words(db, group, rows + [{"word": "berg", "spb_category_key": "dutch"}]), 0)
            self.assertEqual([word_list.id for word_list in m.spb_word_lists_for_group(db, group)], list_ids)
            self.assertTrue(before.issubset(set(db.execute(select(WordListItem.id, WordListItem.word_id, WordListItem.word_list_id)).all())))
            self.assertEqual(db.scalar(select(func.count(WordListItem.id)).where(WordListItem.word_list_id == lists[1].id)), 3)
        engine.dispose()

    def test_miniprogram_detail_fields_include_definitions_and_phonetic(self):
        payload = {
            "def": "to move or extend in different directions from a common point : draw apart",
            "internationalPhoneticAlphabet": "/dɪvɜːrdʒ/",
            "websterPhoneticAlphabet": "other",
            "chinesemeaning": " 分叉；相悖；分歧；背离；偏离",
            "chinesedef": "分离",
            "exp": "An alternative example.",
            "wordCompoundAudio": {"definition": "", "sentence": "Opinions diverge."},
        }
        fields = m.spb_text_fields_from_payload(payload)
        self.assertEqual(fields["english_definition"], payload["def"])
        self.assertEqual(fields["chinese_definition"], payload["chinesemeaning"].strip())
        self.assertEqual(fields["phonetic"], payload["internationalPhoneticAlphabet"])
        self.assertEqual(fields["english_example"], payload["exp"])
        word = Word(word="diverge")
        self.assertTrue(m.apply_spb_text_fields_to_word(word, {**fields, "spb_text_source": "spb-miniprogram"}))
        self.assertEqual(word.english_definition, payload["def"])
        self.assertEqual(word.chinese_definition, payload["chinesemeaning"].strip())
        self.assertTrue(word.english_definition_locked)
        self.assertTrue(word.chinese_definition_locked)

    def test_miniprogram_text_fallbacks(self):
        fields = m.spb_text_fields_from_payload({"data": {
            "chinesemeaning": " ", "chinesedef": "分离",
            "internationalPhoneticAlphabet": "", "websterPhoneticAlphabet": "/test/",
            "exp": "An example.",
        }})
        self.assertEqual(fields["chinese_definition"], "分离")
        self.assertEqual(fields["phonetic"], "/test/")
        self.assertEqual(fields["english_example"], "An example.")

    def test_top_level_meaning_uses_matching_lexicon_audio(self):
        payload = {
            "def": "to stretch the neck to see better",
            "chinesemeaning": "伸长脖子",
            "exp": "She craned her neck to get a better view.",
            "durl": "https://cdn.spbcn.org/audio/lexicon/1/crane2.mp3",
            "eurl": "https://cdn.spbcn.org/audio/lexicon/1/crane3.mp3",
            "wordCompoundAudio": {
                "definition": "a big machine for lifting heavy things",
                "sentence": "The little hut was lifted away by a huge crane.",
                "definitionUrl": "https://cdn.spbcn.org/crane-definition.mp3",
                "sentenceUrl": "https://cdn.spbcn.org/crane-sentence.mp3",
            },
        }
        for wrapped in (payload, {"data": payload}):
            fields = m.spb_text_fields_from_payload(wrapped)
            audio = m.spb_audio_urls_from_payload(wrapped)
            self.assertEqual(fields["english_example"], payload["exp"])
            self.assertEqual(audio["english_definition_audio_url"], payload["durl"])
            self.assertEqual(audio["english_example_audio_url"], payload["eurl"])
        payload.pop("eurl")
        payload.pop("durl")
        audio = m.spb_audio_urls_from_payload(payload)
        self.assertEqual(audio["english_example_audio_url"], "")
        self.assertEqual(audio["english_definition_audio_url"], "")
        payload["exp"] = " "
        payload["def"] = ""
        self.assertEqual(m.spb_text_fields_from_payload(payload)["english_example"], payload["wordCompoundAudio"]["sentence"])
        self.assertEqual(m.spb_example_audio_url_from_payload(payload), payload["wordCompoundAudio"]["sentenceUrl"])

    def test_detail_audio_cache_keys_keep_text_identity_after_filename_limit(self):
        group = {"key": "x" * 100}
        for make_key in (m.spb_example_audio_source_key, m.spb_definition_audio_source_key):
            old_key = make_key(group, "crane", "A lifting machine.", "https://cdn.spbcn.org/old.mp3")
            new_key = make_key(group, "crane", "She craned her neck.", "https://cdn.spbcn.org/new.mp3")
            old_url = f"/media/audio/spb-crane-{old_key[:80]}.mp3"
            self.assertTrue(m.local_audio_url_matches_source_key(old_url, old_key))
            self.assertFalse(m.local_audio_url_matches_source_key(old_url, new_key))

    def test_fetch_previously_unsynced_group_splits_at_500(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        group = m.spb_collection_group_by_keys("individual", "intermediate")[1]
        with Session(engine) as db:
            self.assertEqual(m.append_missing_spb_words(db, group, [{"word": f"new{i}"} for i in range(501)]), 501)
            lists = m.spb_word_lists_for_group(db, group)
            counts = [db.scalar(select(func.count(WordListItem.id)).where(WordListItem.word_list_id == wl.id)) for wl in lists]
            self.assertEqual(counts, [500, 1])
        engine.dispose()

    def test_all_groups_continue_after_failure(self):
        groups = [{"key": key, "title": key} for key in ["beginner", "intermediate", "advanced"]]
        job_id = "test-refresh-all"
        m.SPB_SYNC_JOBS[job_id] = {"status": "queued"}
        try:
            with patch.object(m, "SessionLocal"), patch.object(m, "spb_collection_by_key", return_value={"groups": groups}), patch.object(m, "fetch_spb_source_rows_from_miniprogram", side_effect=[([{"word": "one"}], Path()), ([], Path()), ([{"word": "two"}], Path())]), patch.object(m, "append_missing_spb_words", return_value=1) as append:
                m.run_spb_refresh_all_job(job_id, "individual")
            job = m.spb_sync_job_snapshot(job_id)
            self.assertEqual(job["status"], "failed")
            self.assertEqual(job["processed"], 3)
            self.assertEqual([r["status"] for r in job["results"]], ["complete", "failed", "complete"])
            self.assertEqual(append.call_count, 2)
        finally:
            m.SPB_SYNC_JOBS.pop(job_id, None)

    def test_live_api_precedes_old_public_file(self):
        live = ([{"word": str(i)} for i in range(2400)], Path("live.json"))
        with patch.object(m, "fetch_spb_source_rows_from_miniprogram", return_value=live), patch.object(m, "fetch_spb_source_rows_from_url") as public:
            self.assertEqual(len(m.load_spb_source_rows({})[0]), 2400)
            public.assert_not_called()

    def test_public_fallback_without_authorization(self):
        public = ([{"word": "apple"}], Path("public.json"))
        with patch.object(m, "fetch_spb_source_rows_from_miniprogram", return_value=([], Path())), patch.object(m, "fetch_spb_source_rows_from_url", return_value=public):
            self.assertEqual(m.load_spb_source_rows({}), public)

    def test_append_100_preserves_2300_links_and_is_idempotent(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        group = m.spb_collection_group_by_keys("individual", "advanced")[1]
        with Session(engine) as db:
            lists = []
            for i in range(5):
                wl = WordList(name=f"{group['prefix']}-{i + 1}", sequence_offset=i * 500)
                db.add(wl)
                db.flush()
                lists.append(wl)
            words = [Word(word=f"term{i}") for i in range(2300)]
            db.add_all(words)
            db.flush()
            db.add_all([WordListItem(word_list_id=lists[i // 500].id, word_id=w.id) for i, w in enumerate(words)])
            db.commit()
            before = db.execute(select(WordListItem.id, WordListItem.word_id, WordListItem.word_list_id)).all()
            rows = [{"word": f"term{i}"} for i in range(2400)]
            self.assertEqual(m.append_missing_spb_words(db, group, rows), 100)
            self.assertEqual(len(m.spb_words_for_group(db, group)), 2400)
            self.assertEqual(db.scalar(select(func.count(WordListItem.id)).where(WordListItem.word_list_id == lists[-1].id)), 300)
            new_lists = [wl for wl in m.spb_word_lists_for_group(db, group) if m.is_spb_incremental_list(wl)]
            self.assertEqual(len(new_lists), 1)
            self.assertEqual(new_lists[0].name, f"{group['prefix']}-6-新增")
            self.assertEqual(db.scalar(select(func.count(WordListItem.id)).where(WordListItem.word_list_id == new_lists[0].id)), 100)
            self.assertTrue(set(before).issubset(set(db.execute(select(WordListItem.id, WordListItem.word_id, WordListItem.word_list_id)).all())))
            self.assertEqual(m.append_missing_spb_words(db, group, rows), 0)
            self.assertEqual(m.append_missing_spb_words(db, group, [{"word": f"term{i}"} for i in range(2901)]), 501)
            all_lists = m.spb_word_lists_for_group(db, group)
            self.assertEqual(all_lists[-1].name, f"{group['prefix']}-7-新增")
            self.assertEqual([db.scalar(select(func.count(WordListItem.id)).where(WordListItem.word_list_id == wl.id)) for wl in all_lists[-2:]], [500, 101])
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
