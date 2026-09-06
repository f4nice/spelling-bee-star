import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import Base
from app.models import Word
from app.services import enrichment as e
from app.services.youdao_dictionary import parse_youdao_entry, YoudaoDictionaryClient


def fixture():
    return {
        "ec": {"word": [{
            "return-phrase": {"l": {"i": "fomentation"}},
            "usphone": "ˌfoʊmenˈteɪʃn; ˌfoʊmənˈteɪʃn",
            "ukphone": "ˌfəʊmenˈteɪʃən",
            "trs": [{"tr": [{"l": {"i": ["n. 热敷；煽动"]}}]}],
        }]},
        "ee": {"word": {
            "return-phrase": {"l": {"i": "fomentation"}},
            "trs": [{"pos": "n.", "tr": [
                {"l": {"i": "A warm, moist application."}},
                {"l": {"i": "The stirring up of trouble."}},
            ]}],
        }},
        "blng_sents_part": {"sentence-pair": [
            {"sentence": "An unrelated example."},
            {"sentence-eng": "The book describes <b>fomentation</b> in detail."},
        ]},
        "oxford": {"encryptedData": "not-public-plaintext"},
    }


class YoudaoDictionaryTest(unittest.TestCase):
    def test_public_fields_and_exact_example(self):
        entry = parse_youdao_entry(fixture(), "Fomentation")
        self.assertEqual(entry.phonetic, "/ˌfoʊmenˈteɪʃn/")
        self.assertEqual(entry.part_of_speech, "n.")
        self.assertEqual(entry.english_definition, "A warm, moist application.; The stirring up of trouble.")
        self.assertEqual(entry.chinese_definition, "热敷；煽动")
        self.assertEqual(entry.english_example, "The book describes fomentation in detail.")
        self.assertEqual(entry.american_audio_url, "https://dict.youdao.com/dictvoice?audio=Fomentation&type=2")
        self.assertTrue(entry.british_audio_url.endswith("&type=1"))

    def test_scalar_and_list_shapes(self):
        payload = fixture()
        payload["ec"]["word"] = payload["ec"]["word"][0]
        payload["ec"]["word"]["return-phrase"]["l"]["i"] = ["fomentation"]
        payload["ec"]["word"]["trs"][0]["tr"][0]["l"]["i"] = "n. 热敷；煽动"
        payload["ee"]["word"] = [payload["ee"]["word"]]
        self.assertEqual(parse_youdao_entry(payload, "  fomentation  ").chinese_definition, "热敷；煽动")

    def test_does_not_mix_different_headwords_or_parts_of_speech(self):
        payload = fixture()
        payload["ee"]["word"]["trs"].append({"pos": "v.", "tr": [{"l": {"i": "Wrong verb sense."}}]})
        payload["ec"]["word"][0]["trs"].append({"tr": [{"l": {"i": "v. 错误动词义"}}]})
        entry = parse_youdao_entry(payload, "fomentation")
        self.assertNotIn("Wrong", entry.english_definition)
        self.assertNotIn("错误", entry.chinese_definition)
        payload["ee"]["word"]["return-phrase"]["l"]["i"] = "foment"
        self.assertIsNone(parse_youdao_entry(payload, "fomentation").english_definition)
        with self.assertRaisesRegex(RuntimeError, "不匹配"):
            parse_youdao_entry(payload, "other")

    def test_suggestions_and_premium_data_are_not_entries(self):
        for payload in (None, [], {}, {"input": "fomentation", "suggest": fixture()},
                        {"oxford": {"encryptedData": "data"}},
                        {"ec": {"word": {"return-phrase": {"l": {"i": "fomentation"}}}}}):
            with self.subTest(payload=payload), self.assertRaises(RuntimeError):
                parse_youdao_entry(payload, "fomentation")

    def test_rejects_fragment_and_substring_examples(self):
        payload = fixture()
        payload["blng_sents_part"]["sentence-pair"] = [
            {"sentence": "Fomentation"}, {"sentence": "This is not-fomentation here."},
            {"sentence": "A discussion of fomentations here."},
        ]
        self.assertIsNone(parse_youdao_entry(payload, "fomentation").english_example)

    def test_lookup_passes_query_as_params(self):
        import httpx
        async def run():
            response = httpx.Response(200, json=fixture(), request=httpx.Request("GET", "https://dict.youdao.com/jsonapi"))
            with patch("app.services.youdao_dictionary.httpx.AsyncClient.get", new=AsyncMock(return_value=response)) as get:
                entry = await YoudaoDictionaryClient().lookup("fomentation")
                get.assert_awaited_once_with("https://dict.youdao.com/jsonapi", params={"q": "fomentation"})
                self.assertIsNotNone(entry.english_definition)
        asyncio.run(run())

    def test_failed_primary_uses_youdao_without_retrying_primary_audio(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            word = Word(word="fomentation")
            db.add(word)
            db.commit()
            entry = parse_youdao_entry(fixture(), word.word)
            with patch.object(e, "get_settings", return_value=Settings(merriam_webster_api_key="")), \
                 patch.object(e.FreeDictionaryClient, "lookup", new=AsyncMock(side_effect=TimeoutError)), \
                 patch.object(e.YoudaoDictionaryClient, "lookup", new=AsyncMock(return_value=entry)) as youdao, \
                 patch.object(e.CambridgeDictionaryClient, "lookup", new=AsyncMock()) as cambridge, \
                 patch.object(e.FreeDictionaryAudioClient, "lookup_audio", new=AsyncMock()) as audio, \
                 patch.object(e.TranslationClient, "translate_definition", new=AsyncMock()) as translate, \
                 patch.object(e, "_store_dictionary_audio", new=AsyncMock(return_value="/media/audio/test.mp3")):
                asyncio.run(e.enrich_word(db, word, include_images=False, only_missing=True))
                youdao.assert_awaited_once_with("fomentation")
                cambridge.assert_not_awaited()
                audio.assert_not_awaited()
                translate.assert_not_awaited()
            self.assertEqual(word.enrichment_status, "done")
            self.assertEqual(word.chinese_definition, "热敷；煽动")
            self.assertEqual(word.english_example, entry.english_example)
            self.assertFalse(e.missing_dictionary_fields(word))
        engine.dispose()

    def test_new_fallback_keeps_existing_and_locked_fields(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            word = Word(word="fomentation", english_definition="SPB definition",
                        chinese_definition="手动释义", chinese_definition_locked=True,
                        english_example="SPB example.", british_audio_locked=True)
            db.add(word)
            db.commit()
            with patch.object(e, "get_settings", return_value=Settings(merriam_webster_api_key="")), \
                 patch.object(e.FreeDictionaryClient, "lookup", new=AsyncMock(side_effect=TimeoutError)), \
                 patch.object(e.YoudaoDictionaryClient, "lookup", new=AsyncMock(return_value=parse_youdao_entry(fixture(), word.word))), \
                 patch.object(e, "_store_dictionary_audio", new=AsyncMock(return_value="/media/audio/test.mp3")):
                asyncio.run(e.enrich_word(db, word, include_images=False, only_missing=True))
            self.assertEqual(word.enrichment_status, "done")
            self.assertEqual(word.english_definition, "SPB definition")
            self.assertEqual(word.chinese_definition, "手动释义")
            self.assertEqual(word.english_example, "SPB example.")
            self.assertIsNone(word.british_audio_url)
            self.assertIsNotNone(word.phonetic)
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
