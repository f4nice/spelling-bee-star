import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import main as m
from app.config import Settings
from app.database import Base
from app.models import Word
from app.services import enrichment as e
from app.services.dictionary import DictionaryEntry


COMPLETE = dict(phonetic="/test/", part_of_speech="verb", english_definition="SPB meaning",
                chinese_definition="小程序释义", english_example="An SPB example.",
                american_audio_url="/media/audio/us.mp3", british_audio_url="/media/audio/gb.mp3")


class WordCompletionTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.word = Word(word="test")
        self.db.add(self.word)
        self.db.commit()
        for name in ("apply_word_resource", "remember_word_resource"):
            patcher = patch.object(m, name)
            patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_detail_payload_exposes_completion_state_for_recovery_reads(self):
        for status in ("pending", "done", "failed"):
            self.word.enrichment_status = status
            self.assertEqual(m.serialize_word(self.word)["enrichment_status"], status)

    def test_complete_spb_skips_online_lookup_and_clears_old_failure(self):
        self.word.enrichment_status = "failed"
        self.word.enrichment_error = "old error"

        async def spb(db, word, **kwargs):
            self.assertTrue(kwargs["search_all_groups"])
            self.assertEqual(kwargs["list_id"], 220)
            for field, value in COMPLETE.items():
                setattr(word, field, value)
            return True

        with patch.object(m, "apply_spb_details_to_word", side_effect=spb), \
             patch.object(m, "enrich_word", new=AsyncMock()) as online:
            asyncio.run(m.complete_word_from_sources(self.db, self.word, list_id=220))
            online.assert_not_awaited()
        self.assertEqual(self.word.enrichment_status, "done")
        self.assertIsNone(self.word.enrichment_error)

    def test_partial_spb_goes_first_then_online_only_missing(self):
        calls = []

        async def spb(db, word, **kwargs):
            calls.append("spb")
            word.english_definition = "SPB meaning"
            return True

        async def online(db, word, **kwargs):
            calls.append("online")
            self.assertEqual(word.english_definition, "SPB meaning")
            self.assertEqual(kwargs, {"include_images": False, "only_missing": True})

        with patch.object(m, "apply_spb_details_to_word", side_effect=spb), \
             patch.object(m, "enrich_word", side_effect=online):
            asyncio.run(m.complete_word_from_sources(self.db, self.word))
        self.assertEqual(calls, ["spb", "online"])

    def test_absent_or_unavailable_spb_still_uses_online(self):
        for result in (False, RuntimeError("upstream unavailable")):
            with self.subTest(result=result), \
                 patch.object(m, "apply_spb_details_to_word", new=AsyncMock(
                     return_value=result, side_effect=result if isinstance(result, Exception) else None)), \
                 patch.object(m, "enrich_word", new=AsyncMock()) as online:
                asyncio.run(m.complete_word_from_sources(self.db, self.word))
                online.assert_awaited_once()

    def test_online_preserves_existing_spb_text_even_without_locks(self):
        self.word.word = "abandon"  # Has a legacy Chinese rewrite override.
        for field, value in COMPLETE.items():
            setattr(self.word, field, value)
        self.word.phonetic = None
        entry = DictionaryEntry(phonetic="/online/", part_of_speech="noun",
                                english_definition="Different online sense",
                                chinese_definition="不同释义", english_example="Online example.")
        with patch.object(e, "get_settings", return_value=Settings(merriam_webster_api_key="")), \
             patch.object(e.FreeDictionaryClient, "lookup", new=AsyncMock(return_value=entry)):
            asyncio.run(e.enrich_word(self.db, self.word, include_images=False, only_missing=True))
        self.assertEqual(self.word.phonetic, "/online/")
        for field, value in COMPLETE.items():
            if field != "phonetic":
                self.assertEqual(getattr(self.word, field), value)

    def test_missing_chinese_translates_retained_spb_sense(self):
        for field, value in COMPLETE.items():
            setattr(self.word, field, value)
        self.word.chinese_definition = None
        entry = DictionaryEntry(english_definition="Different online sense", chinese_definition="不同释义")
        with patch.object(e, "get_settings", return_value=Settings(merriam_webster_api_key="")), \
             patch.object(e.FreeDictionaryClient, "lookup", new=AsyncMock(return_value=entry)), \
             patch.object(e.TranslationClient, "translate_definition", new=AsyncMock(return_value="匹配小程序释义")) as translate:
            asyncio.run(e.enrich_word(self.db, self.word, include_images=False, only_missing=True))
            translate.assert_awaited_once_with("SPB meaning")
        self.assertEqual(self.word.chinese_definition, "匹配小程序释义")

    def test_ordinary_list_word_can_resolve_spb_catalog(self):
        group = {"key": "beginner", "prefix": "SPB"}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "catalog.json"
            path.write_text(json.dumps([{"word": "test", "id": 123}]), encoding="utf-8")
            with patch.object(m, "all_spb_word_bank_groups", return_value=[group]), \
                 patch.object(m, "spb_cached_source_path", return_value=path):
                self.assertEqual(m.spb_catalog_groups_for_word("test"), [group])
                self.assertEqual(m.spb_catalog_groups_for_word("absent"), [])
        with patch.object(m, "spb_candidate_groups_for_word", return_value=[]), \
             patch.object(m, "spb_catalog_groups_for_word", return_value=[group]), \
             patch.object(m, "find_spb_source_row_for_word", return_value=None) as find:
            asyncio.run(m.apply_spb_details_to_word(self.db, self.word, search_all_groups=True))
            find.assert_called_once_with(group, "test")

    def test_unchanged_spb_match_does_not_switch_to_another_groups_sense(self):
        groups = [{"prefix": "current"}, {"prefix": "other"}]
        with patch.object(m, "spb_candidate_groups_for_word", return_value=groups), \
             patch.object(m, "find_spb_source_row_for_word", return_value={"word": "test"}) as find, \
             patch.object(m, "prepare_spb_rows_with_local_audio", new=AsyncMock(return_value=[{"word": "test"}])), \
             patch.object(m, "apply_spb_text_fields_to_word", return_value=False), \
             patch.object(m, "apply_imported_local_audio", return_value=False), \
             patch.object(m, "clear_misclassified_spb_audio_from_resource", return_value=False):
            self.assertFalse(asyncio.run(m.apply_spb_details_to_word(self.db, self.word)))
        find.assert_called_once_with(groups[0], "test")


if __name__ == "__main__":
    unittest.main()
