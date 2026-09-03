import os
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from app import main as m
from app.database import Base
from app.models import Word, WordList, WordListItem


class SpbRefreshTest(unittest.TestCase):
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
            self.assertEqual(db.scalar(select(func.count(WordListItem.id)).where(WordListItem.word_list_id == lists[-1].id)), 400)
            self.assertTrue(set(before).issubset(set(db.execute(select(WordListItem.id, WordListItem.word_id, WordListItem.word_list_id)).all())))
            self.assertEqual(m.append_missing_spb_words(db, group, rows), 0)
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
