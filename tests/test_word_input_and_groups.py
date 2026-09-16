import asyncio
from io import BytesIO
import os
import unittest
from unittest.mock import AsyncMock, Mock, patch

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

import pandas as pd
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import main as m
from app.database import Base
from app.models import Word, WordList, WordListGroup, WordListItem
from app.services.excel_importer import parse_preview_from_excel, parse_words_from_preview


class WordInputAndGroupsTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.word_list = WordList(name="Test words")
        self.db.add(self.word_list)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_excel_preview_and_import_preserve_latin_accents_and_curly_apostrophes(self):
        words = ["pâtisserie", "fräulein", "objet d’art", "éclair", "naïve", "cafe\u0301"]
        content = BytesIO()
        pd.DataFrame({"Vocabulary": words + ["123", "中文", "bad🙂"]}).to_excel(content, index=False)
        preview = parse_preview_from_excel(content.getvalue())
        rows = parse_words_from_preview(preview, set(range(9)), {"Vocabulary"}, ["Vocabulary"])
        expected = words[:-1] + ["café"]
        self.assertEqual([row["word"] for row in rows], expected)
        ids = m.import_rows(rows, self.db, self.word_list)
        self.assertEqual([self.db.get(Word, word_id).word for word_id in ids], expected)

    def test_manual_add_accepts_same_spellings_and_saves_them(self):
        with patch.object(m, "start_enrichment_thread"):
            for word in ["pâtisserie", "fräulein", "objet d’art", "éclair"]:
                result = m.vue_create_word_in_list(
                    self.word_list.id, word=word, existing_word_id=None, phonetic="",
                    part_of_speech="n.", english_definition="", chinese_definition="",
                    english_example="", note="", db=self.db,
                )
                self.assertEqual(self.db.get(Word, result["word"]["id"]).word, word)
        for word in ["123", "中文", "bad🙂", "<script>", "a" * 129]:
            with self.subTest(word=word), self.assertRaises(HTTPException):
                m.clean_manual_word_text(word)

    def test_part_of_speech_edit_persists_and_updates_shared_resource(self):
        word = Word(word="test", part_of_speech="n.")
        self.db.add(word)
        self.db.commit()
        result = m.vue_update_word_field(word.id, "part_of_speech", "n.; v.", "1", self.db)
        self.db.expire_all()
        self.assertEqual(result["value"], "n.; v.")
        self.assertEqual(self.db.get(Word, word.id).part_of_speech, "n.; v.")
        self.assertEqual(m.get_word_resource(self.db, "test").part_of_speech, "n.; v.")

    def test_search_matches_chinese_and_alternate_spelling_with_literal_wildcards(self):
        word = Word(word="pâtisserie", alternate_spellings="patisserie", chinese_definition="法式糕点店")
        self.db.add(word)
        self.db.flush()
        self.db.add(WordListItem(word_list_id=self.word_list.id, word_id=word.id))
        self.db.commit()
        for query in ["糕点", "patisserie", "pâtisserie"]:
            result = m.vue_list_word_search_api(query, self.db)
            self.assertEqual([row["word"]["id"] for row in result["results"]], [word.id])
        for query in ["%", "_", "missing"]:
            self.assertEqual(m.vue_list_word_search_api(query, self.db)["results"], [])

    def test_group_reorder_survives_reload_and_retains_unlisted_groups(self):
        groups = [WordListGroup(name=name, display_order=i * 10) for i, name in enumerate(["A", "B", "C"], 1)]
        self.db.add_all(groups)
        self.db.commit()
        ids = [group.id for group in groups]
        self.word_list.group_id = ids[0]
        self.db.commit()
        request = Mock(json=AsyncMock(return_value={"ordered_ids": [ids[2], ids[0]]}))
        asyncio.run(m.vue_reorder_word_list_groups_api(request, self.db))
        self.db.expire_all()
        self.assertEqual([group.id for group in m.word_list_groups(self.db)], [ids[2], ids[0], ids[1]])
        self.assertEqual(self.db.get(WordList, self.word_list.id).group_id, ids[0])
        for invalid in [[ids[0], ids[0]], [9999], ["bad"], []]:
            request.json = AsyncMock(return_value={"ordered_ids": invalid})
            with self.assertRaises(HTTPException):
                asyncio.run(m.vue_reorder_word_list_groups_api(request, self.db))


if __name__ == "__main__":
    unittest.main()
