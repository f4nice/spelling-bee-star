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
        self.assertEqual(fields["english_example"], "Opinions diverge.")
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
