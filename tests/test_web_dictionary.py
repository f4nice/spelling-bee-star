import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import Base
from app.models import Word
from app.services import enrichment as e
from app.services.dictionary import DictionaryEntry
from app.services.web_dictionary import parse_cambridge_entry


class WebDictionaryTest(unittest.TestCase):
    def test_exact_headword_and_same_sense(self):
        html = '''<div class="entry-body__el"><span class="hw">spondylitis</span>
        <span class="pos">noun</span><span class="us"><span class="ipa">spɒn</span></span>
        <div class="def-block"><div class="def">Inflammation of <a>spinal bones</a>:</div>
        <span class="trans">脊柱炎</span><span class="eg">The report mentioned spondylitis.</span></div>
        <div class="def-block"><div class="def">Another sense</div><span class="eg">Wrong sense.</span></div></div>'''
        entry = parse_cambridge_entry(html, "spondylitis", "https://dictionary.cambridge.org/example")
        self.assertEqual(entry.english_definition, "Inflammation of spinal bones")
        self.assertEqual(entry.english_example, "The report mentioned spondylitis.")
        self.assertEqual(entry.chinese_definition, "脊柱炎")
        self.assertEqual(entry.phonetic, "/spɒn/")
        with self.assertRaises(RuntimeError):
            parse_cambridge_entry(html, "other", "test")
        with self.assertRaises(RuntimeError):
            parse_cambridge_entry('<div class="ipa">word of the day</div>', "spondylitis", "test")

    def test_online_fallback_survives_optional_audio_failure(self):
        import asyncio
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            word = Word(word="spondylitis")
            db.add(word)
            db.commit()
            entry = DictionaryEntry(phonetic="/test/", part_of_speech="noun", english_definition="Inflammation of spinal bones", chinese_definition="脊柱炎", english_example="The report mentioned spondylitis.", source="https://dictionary.cambridge.org/example")
            with patch.object(e, "get_settings", return_value=Settings(merriam_webster_api_key="")), \
                 patch.object(e.FreeDictionaryClient, "lookup", new=AsyncMock(side_effect=RuntimeError("522"))), \
                 patch.object(e.CambridgeDictionaryClient, "lookup", new=AsyncMock(return_value=entry)), \
                 patch.object(e.FreeDictionaryAudioClient, "lookup_audio", new=AsyncMock(side_effect=RuntimeError("522"))), \
                 patch.object(e, "store_first_available_audio", new=AsyncMock(return_value="/media/audio/test.mp3")):
                asyncio.run(e.enrich_word(db, word, include_images=False))
            self.assertEqual(word.enrichment_status, "done")
            self.assertEqual(word.english_definition, entry.english_definition)
            self.assertEqual(word.chinese_definition, "脊柱炎")
            self.assertEqual(word.english_example, entry.english_example)
            self.assertEqual(word.source, entry.source)
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
