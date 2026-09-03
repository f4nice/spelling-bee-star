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
            new_lists = [wl for wl in m.spb_word_lists_for_group(db, group) if "-新增-" in wl.name]
            self.assertEqual(len(new_lists), 1)
            self.assertEqual(db.scalar(select(func.count(WordListItem.id)).where(WordListItem.word_list_id == new_lists[0].id)), 100)
            self.assertTrue(set(before).issubset(set(db.execute(select(WordListItem.id, WordListItem.word_id, WordListItem.word_list_id)).all())))
            self.assertEqual(m.append_missing_spb_words(db, group, rows), 0)
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
