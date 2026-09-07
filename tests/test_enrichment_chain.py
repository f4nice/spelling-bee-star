import asyncio
import os
import unittest
from unittest.mock import AsyncMock, patch

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import Base
from app.models import Word
from app.services import enrichment as e
from app.services.dictionary import DictionaryEntry


COMPLETE = dict(phonetic="/test/", part_of_speech="v.",
                english_definition="To wash clothing.", chinese_definition="洗衣服。",
                english_example="They launder clothing every day.")


class EnrichmentChainTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.word = Word(word="launder", american_audio_url="/media/audio/us.mp3",
                         british_audio_url="/media/audio/gb.mp3")
        self.db.add(self.word)
        self.db.commit()
        self.providers = {}
        for name in ("FreeDictionaryClient", "YoudaoDictionaryClient", "MerriamWebsterWebClient",
                     "CambridgeDictionaryClient", "WordnikDictionaryClient", "MerriamWebsterClient"):
            self.providers[name] = self.mock(getattr(e, name), "lookup", side_effect=RuntimeError("no entry"))
        self.translation = self.mock(e.TranslationClient, "translate_definition", return_value=None)
        self.teaching = self.mock(e.TeachingExampleClient, "generate", return_value=None)
        self.audio = self.mock(e.FreeDictionaryAudioClient, "lookup_audio", return_value=(None, None))
        self.store = self.mock(e, "_store_dictionary_audio", return_value=None)
        self.mock(e.ImageClient, "find_image", return_value=None)
        settings = Settings(_env_file=None, merriam_webster_api_key="", dashscope_api_key="")
        for name, value in (("get_settings", settings), ("lookup_reviewed_entry", None)):
            patcher = patch.object(e, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        # No test may accidentally send HTTP through a newly added provider.
        self.http = self.mock(__import__("httpx").AsyncClient, "send", side_effect=AssertionError("Unexpected HTTP"))

    def tearDown(self):
        self.http.assert_not_awaited()
        self.db.close()
        self.engine.dispose()

    def mock(self, target, name, **kwargs):
        mock = AsyncMock(**kwargs)
        patcher = patch.object(target, name, new=mock)
        patcher.start()
        self.addCleanup(patcher.stop)
        return mock

    def provider(self, name, entry):
        result = self.providers[name]
        result.side_effect = None
        result.return_value = entry
        return result

    def complete(self):
        return asyncio.run(e.enrich_word(self.db, self.word, include_images=False, only_missing=True))

    def test_partial_success_continues_to_next_provider_until_all_text_exists(self):
        calls = []

        async def free(word):
            calls.append("free")
            return DictionaryEntry(phonetic="/test/", part_of_speech="v.", source="Free")

        async def youdao(word):
            calls.append("youdao")
            return DictionaryEntry(english_definition=COMPLETE["english_definition"],
                                   chinese_definition=COMPLETE["chinese_definition"], source="Youdao")

        async def webster(word):
            calls.append("webster")
            return DictionaryEntry(english_definition="to WASH clothing!",
                                   english_example=COMPLETE["english_example"], source="Webster")

        for name, callback in (("FreeDictionaryClient", free), ("YoudaoDictionaryClient", youdao),
                               ("MerriamWebsterWebClient", webster)):
            self.providers[name].side_effect = callback
        self.complete()
        self.assertEqual(calls, ["free", "youdao", "webster"])
        self.providers["CambridgeDictionaryClient"].assert_not_awaited()
        self.providers["WordnikDictionaryClient"].assert_not_awaited()
        for field, value in COMPLETE.items():
            self.assertEqual(getattr(self.word, field), value)
        self.assertEqual(self.word.source, "Free | Youdao | Webster")
        self.assertEqual(self.word.enrichment_status, "done")
        self.assertIsNone(self.word.enrichment_error)
        self.translation.assert_not_awaited()
        self.teaching.assert_not_awaited()

    def test_configured_webster_api_is_first_and_complete_entry_stops_lookup(self):
        api = self.provider("MerriamWebsterClient", DictionaryEntry(**COMPLETE, source="Webster API"))
        settings = Settings(_env_file=None, merriam_webster_api_key="mock-key", dashscope_api_key="")
        with patch.object(e, "get_settings", return_value=settings):
            self.complete()
        api.assert_awaited_once_with("launder")
        self.providers["FreeDictionaryClient"].assert_not_awaited()
        self.providers["MerriamWebsterWebClient"].assert_not_awaited()
        self.assertEqual(self.word.enrichment_status, "done")

    def test_webster_access_denied_does_not_stop_remaining_sources(self):
        self.providers["MerriamWebsterWebClient"].side_effect = RuntimeError("HTTP 403")
        cambridge = self.provider("CambridgeDictionaryClient", DictionaryEntry(**COMPLETE))
        self.complete()
        self.providers["MerriamWebsterWebClient"].assert_awaited_once()
        cambridge.assert_awaited_once_with("launder")
        self.providers["WordnikDictionaryClient"].assert_not_awaited()
        self.assertEqual(self.word.enrichment_status, "done")
        self.assertIsNone(self.word.enrichment_error)

    def test_existing_and_locked_text_are_never_replaced(self):
        for field, value in COMPLETE.items():
            setattr(self.word, field, value)
        self.word.phonetic = " \t"
        self.word.chinese_definition = None
        self.word.chinese_definition_locked = True
        self.provider("FreeDictionaryClient", DictionaryEntry(
            phonetic="/new/", part_of_speech="noun", english_definition="Different meaning.",
            chinese_definition="不能填入", english_example="Must not replace."))
        self.complete()
        self.assertEqual(self.word.phonetic, "/new/")
        self.assertIsNone(self.word.chinese_definition)
        for field in ("part_of_speech", "english_definition", "english_example"):
            self.assertEqual(getattr(self.word, field), COMPLETE[field])
        self.translation.assert_not_awaited()
        self.teaching.assert_not_awaited()

    def test_different_sense_example_is_rejected_and_authored_example_is_labeled(self):
        for field, value in COMPLETE.items():
            setattr(self.word, field, value)
        self.word.english_example = None
        self.provider("FreeDictionaryClient", DictionaryEntry(
            part_of_speech="v.", english_definition="To conceal criminal money.",
            english_example="The gang laundered illegal money."))
        example = "【自编教学例句】They launder clothing every day."
        self.teaching.return_value = example
        self.complete()
        self.assertEqual(self.word.english_definition, COMPLETE["english_definition"])
        self.assertEqual(self.word.english_example, example)
        self.teaching.assert_awaited_once_with("launder", COMPLETE["english_definition"], "v.")
        self.assertEqual(self.word.enrichment_status, "done")

    def test_same_sense_example_is_used_without_authorship_claim(self):
        for field, value in COMPLETE.items():
            setattr(self.word, field, value)
        self.word.english_example = None
        self.provider("FreeDictionaryClient", DictionaryEntry(
            english_definition="TO WASH clothing!", english_example=COMPLETE["english_example"]))
        self.complete()
        self.assertEqual(self.word.english_example, COMPLETE["english_example"])
        self.assertNotIn("自编", self.word.english_example)
        self.teaching.assert_not_awaited()

    def test_chinese_only_first_result_is_preserved_when_later_english_is_found(self):
        self.provider("FreeDictionaryClient", DictionaryEntry(part_of_speech="vt.", chinese_definition="洗衣服。"))
        self.provider("YoudaoDictionaryClient", DictionaryEntry(
            phonetic="/test/", part_of_speech="verb", english_definition=COMPLETE["english_definition"],
            chinese_definition="新来源翻译", english_example=COMPLETE["english_example"]))
        self.complete()
        self.assertEqual(self.word.chinese_definition, "洗衣服。")
        self.assertEqual(self.word.english_definition, COMPLETE["english_definition"])
        self.assertEqual(self.word.part_of_speech, "vt.")
        self.assertEqual(self.word.enrichment_status, "done")
        self.translation.assert_not_awaited()

    def test_incompatible_part_of_speech_does_not_supply_definition_or_example(self):
        self.word.part_of_speech = "v."
        self.provider("FreeDictionaryClient", DictionaryEntry(
            part_of_speech="n.", english_definition="A person who washes clothes.",
            english_example="The launderer was busy.", chinese_definition="洗衣工"))
        self.complete()
        self.assertIsNone(self.word.english_definition)
        self.assertIsNone(self.word.english_example)
        self.assertIsNone(self.word.chinese_definition)
        self.teaching.assert_not_awaited()
        self.assertEqual(self.word.enrichment_status, "partial")

    def test_different_sense_cannot_supply_missing_part_of_speech_for_retained_definition(self):
        for field, value in COMPLETE.items():
            setattr(self.word, field, value)
        self.word.part_of_speech = None
        self.provider("FreeDictionaryClient", DictionaryEntry(
            part_of_speech="noun", english_definition="A person who washes clothing."))
        self.complete()
        self.assertIsNone(self.word.part_of_speech)
        self.assertEqual(self.word.english_definition, COMPLETE["english_definition"])
        self.assertEqual(self.word.enrichment_status, "partial")

    def test_no_trusted_definition_means_no_generated_example_or_translation(self):
        self.provider("FreeDictionaryClient", DictionaryEntry(part_of_speech="n.", chinese_definition="洗衣工"))
        self.complete()
        self.teaching.assert_not_awaited()
        self.translation.assert_not_awaited()
        self.assertIsNone(self.word.english_example)
        self.assertEqual(self.word.enrichment_status, "partial")
        self.assertIn("英文释义", self.word.enrichment_error)

    def test_legacy_encyclopedia_context_never_drives_translation_or_teaching(self):
        for pos in ("abstract:", "abstract", "unknown", "wikipedia"):
            with self.subTest(pos=pos):
                self.word.part_of_speech = pos
                self.word.english_definition = "An encyclopedia paragraph about an unrelated album."
                self.complete()
                self.translation.assert_not_awaited()
                self.teaching.assert_not_awaited()
                self.assertIsNone(self.word.chinese_definition)
                self.assertIsNone(self.word.english_example)
                self.assertEqual(self.word.enrichment_status, "partial")

    def test_translator_uses_retained_definition_and_failure_keeps_partial_text(self):
        for field, value in COMPLETE.items():
            setattr(self.word, field, value)
        self.word.chinese_definition = None
        self.translation.side_effect = RuntimeError("HTTP 429 https://api.invalid/?key=SECRET")
        self.complete()
        self.translation.assert_awaited_once_with(COMPLETE["english_definition"])
        self.assertEqual(self.word.enrichment_status, "partial")
        self.assertIn("翻译服务暂不可用或限流", self.word.enrichment_error)
        self.assertNotIn("SECRET", self.word.enrichment_error)
        self.db.expire_all()
        self.assertEqual(self.db.get(Word, self.word.id).english_definition, COMPLETE["english_definition"])

    def test_all_providers_fail_returns_failed_with_safe_missing_field_reasons(self):
        for provider in self.providers.values():
            provider.side_effect = RuntimeError("https://private:SECRET@api.invalid")
        self.complete()
        self.assertEqual(self.word.enrichment_status, "failed")
        self.assertIn("仍缺音标、词性、英文释义、中文释义、英文例句", self.word.enrichment_error)
        self.assertIn("韦氏官网未返回可用词条", self.word.enrichment_error)
        self.assertNotIn("SECRET", self.word.enrichment_error)
        self.translation.assert_not_awaited()
        self.teaching.assert_not_awaited()

    def test_completed_text_is_committed_before_optional_audio_cancellation(self):
        self.word.american_audio_url = None
        self.word.british_audio_url = None
        self.provider("FreeDictionaryClient", DictionaryEntry(**COMPLETE))

        async def cancel_audio(word):
            with Session(self.engine) as verifier:
                saved = verifier.get(Word, self.word.id)
                self.assertEqual(saved.english_definition, COMPLETE["english_definition"])
                self.assertEqual(saved.english_example, COMPLETE["english_example"])
            raise asyncio.CancelledError()

        self.audio.side_effect = cancel_audio
        with self.assertRaises(asyncio.CancelledError):
            self.complete()
        self.db.rollback()
        self.db.expire_all()
        self.assertEqual(self.word.chinese_definition, COMPLETE["chinese_definition"])


if __name__ == "__main__":
    unittest.main()
