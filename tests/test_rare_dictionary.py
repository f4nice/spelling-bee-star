import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import Base
from app.models import Word
from app.services import enrichment as e
from app.services import audio_storage as audio
from app.services.dictionary import DictionaryEntry
from app.services.reviewed_dictionary import lookup_reviewed_entry
from app.services.wordnik_dictionary import parse_wordnik_entry, WordnikDictionaryClient


HTML = '''<h1 id="headword">rareword</h1><div id="define">
<h3 class="source">from The Century Dictionary.</h3>
<ul><li><abbr title="partOfSpeech">noun</abbr> A <a>test</a> meaning.</li>
<li><abbr title="partOfSpeech">verb</abbr> Different sense.</li></ul></div>
<div class="module-examples">An unrelated page-wide example.</div>'''


class RareDictionaryTest(unittest.TestCase):
    def test_wordnik_exact_headword_and_first_sense(self):
        entry = parse_wordnik_entry(HTML, "Rareword", "test-source")
        self.assertEqual(entry.part_of_speech, "noun")
        self.assertEqual(entry.english_definition, "A test meaning.")
        self.assertEqual(entry.source, "test-source")
        self.assertIsNone(entry.english_example)
        self.assertIsNone(entry.phonetic)
        with self.assertRaises(RuntimeError):
            parse_wordnik_entry(HTML, "different", "test-source")
        with self.assertRaises(RuntimeError):
            parse_wordnik_entry('<h1 id="headword">rareword</h1><div id="define">Sorry, no definitions found.</div>', "rareword", "test")

    def test_wordnik_uses_lowercase_page_but_checks_returned_word(self):
        import httpx
        response = httpx.Response(200, text=HTML, request=httpx.Request("GET", "https://www.wordnik.com/words/rareword"))
        with patch("app.services.wordnik_dictionary.httpx.AsyncClient.get", new=AsyncMock(return_value=response)) as get:
            entry = asyncio.run(WordnikDictionaryClient().lookup("Rareword"))
            get.assert_awaited_once_with("https://www.wordnik.com/words/rareword")
        self.assertEqual(entry.english_definition, "A test meaning.")

    def test_reviewed_word_is_exact_and_authored_example_is_labeled(self):
        entry = lookup_reviewed_entry("Novanglian")
        self.assertIsNotNone(entry)
        self.assertIn("韦氏注音", entry.phonetic)
        self.assertIn("自编教学例句", entry.english_example)
        self.assertIn("merriam-webster.com", entry.source)
        self.assertIsNone(entry.american_audio_url)
        self.assertIsNone(lookup_reviewed_entry("no angling"))
        entry.english_definition = "changed"
        self.assertNotEqual(lookup_reviewed_entry("novanglian").english_definition, "changed")

    def test_reviewed_word_skips_unavailable_text_services(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            word = Word(word="Novanglian", english_definition="Retained SPB definition",
                        chinese_definition="原释义", english_example="Manual example.", english_example_locked=True)
            db.add(word); db.commit()
            with patch.object(e.FreeDictionaryClient, "lookup", new=AsyncMock()) as free, \
                 patch.object(e.YoudaoDictionaryClient, "lookup", new=AsyncMock()) as youdao, \
                 patch.object(e, "_store_dictionary_audio", new=AsyncMock(return_value=None)) as store:
                asyncio.run(e.enrich_word(db, word, include_images=False, only_missing=True))
                free.assert_not_awaited(); youdao.assert_not_awaited()
                self.assertTrue(all(not call.kwargs["include_dictionary"] for call in store.await_args_list))
            self.assertIn("韦氏注音", word.phonetic)
            self.assertEqual(word.english_definition, "Retained SPB definition")
            self.assertEqual(word.english_example, "Manual example.")
            self.assertEqual(word.enrichment_status, "done")
        engine.dispose()

    def test_wordnik_is_final_fallback_and_partial_text_is_saved(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            word = Word(word="rareword")
            db.add(word); db.commit()
            entry = DictionaryEntry(part_of_speech="noun", english_definition="A test meaning.", source="Wordnik")
            with patch.object(e, "get_settings", return_value=Settings(merriam_webster_api_key="")), \
                 patch.object(e.FreeDictionaryClient, "lookup", new=AsyncMock(side_effect=TimeoutError)), \
                 patch.object(e.YoudaoDictionaryClient, "lookup", new=AsyncMock(side_effect=RuntimeError("not found"))), \
                 patch.object(e.CambridgeDictionaryClient, "lookup", new=AsyncMock(side_effect=RuntimeError("not found"))), \
                 patch.object(e.WordnikDictionaryClient, "lookup", new=AsyncMock(return_value=entry)) as wordnik, \
                 patch.object(e.TranslationClient, "translate_definition", new=AsyncMock(return_value="测试释义")), \
                 patch.object(e, "_store_dictionary_audio", new=AsyncMock(return_value=None)):
                asyncio.run(e.enrich_word(db, word, include_images=False, only_missing=True))
                wordnik.assert_awaited_once_with("rareword")
            self.assertEqual(word.english_definition, "A test meaning.")
            self.assertEqual(word.chinese_definition, "测试释义")
            self.assertIsNone(word.english_example)
            self.assertIsNone(word.phonetic)
        engine.dispose()

    def test_audio_does_not_repeat_known_failed_dictionary_lookup(self):
        with patch.object(audio.FreeDictionaryAudioClient, "lookup_audio", new=AsyncMock()) as free, \
             patch.object(audio, "store_audio_candidate", new=AsyncMock(return_value="/media/audio/test.mp3")):
            result = asyncio.run(audio.store_first_available_audio("rareword", "us", e.AUDIO_DIR, include_dictionary=False))
            free.assert_not_awaited()
            self.assertEqual(result, "/media/audio/test.mp3")


if __name__ == "__main__":
    unittest.main()
