"""Excel new-list and continuation preservation; all databases/jobs are isolated."""
import asyncio
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from uuid import uuid4

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app import main as m
from app.database import Base
from app.models import ChallengeProgress, Word, WordList, WordListGroup, WordListItem, WordResourcePool


def snapshot(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


class ExcelImportPreservationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)
        self.old_list = WordList(name="Original", display_order=-10)
        self.new_list = WordList(name="New", display_order=-20)
        self.word = Word(word="KeePCase", phonetic="old phonetic", alternate_spellings="keep case",
            part_of_speech="n.", english_definition="original definition", chinese_definition="原释义",
            english_example="The original example.", note="original note", image_url="/media/images/original.webp",
            american_audio_url="/media/audio/original-us.mp3", british_audio_url="/media/audio/original-gb.mp3",
            english_definition_audio_url="/media/audio/original-def.mp3",
            english_example_audio_url="/media/audio/original-example.mp3", enrichment_status="ready")
        self.db.add_all([self.old_list, self.new_list, self.word])
        self.db.commit()
        self.pool = WordResourcePool(normalized_word="keepcase", display_word="KeePCase",
            english_definition="pool definition", use_count=7, source_word_id=self.word.id)
        self.progress = ChallengeProgress(word_list_id=self.old_list.id, current_index=1,
            completed_count=4, completed_rounds=2)
        self.db.add_all([self.pool, self.progress, WordListItem(word_list_id=self.old_list.id, word_id=self.word.id)])
        self.db.commit()
        self.original_word = snapshot(self.word)
        self.original_pool = snapshot(self.pool)
        self.original_progress = snapshot(self.progress)

    def replacement(self):
        return {"word":"keepcase", "phonetic":"new phonetic", "alternate_spellings":"changed spelling",
            "part_of_speech":"v.", "english_definition":"replacement definition", "chinese_definition":"新释义",
            "english_example":"A different example.", "note":"replacement note",
            "american_audio_url":"/media/audio/replacement-us.mp3",
            "british_audio_url":"/media/audio/replacement-gb.mp3",
            "english_definition_audio_url":"/media/audio/replacement-def.mp3",
            "english_example_audio_url":"/media/audio/replacement-example.mp3"}

    def assert_original_unchanged(self):
        self.db.expire_all()
        self.assertEqual(snapshot(self.db.get(Word,self.word.id)), self.original_word)
        self.assertEqual(snapshot(self.db.get(WordResourcePool,self.pool.id)), self.original_pool)
        self.assertEqual(snapshot(self.db.get(ChallengeProgress,self.progress.id)), self.original_progress)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(WordListItem).where(
            WordListItem.word_list_id==self.old_list.id, WordListItem.word_id==self.word.id)), 1)

    def test_preserve_mode_only_links_existing_word(self):
        eligible, progress = [], []
        with patch.object(m,"apply_word_resource") as apply, patch.object(m,"remember_word_resource") as remember:
            ids = m.import_rows([self.replacement()], self.db, self.new_list,
                progress_callback=progress.append, preserve_existing_words=True, enrichment_word_ids=eligible)
        self.assertEqual(ids,[self.word.id])
        self.assertEqual(eligible,[])
        self.assertEqual(progress,[1])
        apply.assert_not_called()
        remember.assert_not_called()
        self.assert_original_unchanged()
        self.assertEqual(self.db.scalar(select(func.count()).select_from(WordListItem).where(
            WordListItem.word_list_id==self.new_list.id)),1)

    def test_mixed_rows_schedule_only_new_word(self):
        eligible = []
        rows = [self.replacement(), {"word":"brandnew", "english_definition":"new entry"}]
        with patch.object(m,"apply_word_resource") as apply, patch.object(m,"remember_word_resource") as remember:
            ids = m.import_rows(rows,self.db,self.new_list,preserve_existing_words=True,enrichment_word_ids=eligible)
        self.assertEqual(len(ids),2)
        self.assertEqual(eligible,[ids[1]])
        self.assertEqual(self.db.get(Word,ids[1]).word,"brandnew")
        self.assertEqual(apply.call_count,1)
        self.assertEqual(remember.call_count,1)
        self.assert_original_unchanged()

    def test_default_merge_behavior_remains_available(self):
        eligible = []
        with patch.object(m,"apply_word_resource"), patch.object(m,"remember_word_resource"):
            ids = m.import_rows([self.replacement()],self.db,self.new_list,enrichment_word_ids=eligible)
        self.db.expire_all()
        self.assertEqual(ids,[self.word.id])
        self.assertEqual(eligible,ids)
        self.assertEqual(self.db.get(Word,self.word.id).english_definition,"replacement definition")
        self.assertEqual(self.db.get(Word,self.word.id).word,"keepcase")

    def test_repeated_new_word_is_linked_once_and_keeps_first_fields(self):
        eligible = []
        with patch.object(m,"apply_word_resource"), patch.object(m,"remember_word_resource"):
            ids = m.import_rows([{"word":"brandnew","english_definition":"first"},
                {"word":"brandnew","english_definition":"second"}],self.db,self.new_list,
                preserve_existing_words=True,enrichment_word_ids=eligible)
        self.assertEqual(ids,[ids[0],ids[0]])
        self.assertEqual(eligible,[ids[0]])
        self.assertEqual(self.db.get(Word,ids[0]).english_definition,"first")
        self.assertEqual(self.db.scalar(select(func.count()).select_from(WordListItem).where(
            WordListItem.word_list_id==self.new_list.id)),1)

    def run_job(self, rows, target="", name="New import"):
        job_id = uuid4().hex
        m.store_import_preview_job({"id":job_id,"status":"queued","total":len(rows),"processed":0})
        self.addCleanup(m.IMPORT_PREVIEW_JOBS.pop,job_id,None)
        with TemporaryDirectory() as temporary, patch.object(m,"PREVIEW_DIR",Path(temporary)), \
                patch.object(m,"SessionLocal",side_effect=lambda:Session(self.engine)), \
                patch.object(m,"start_enrichment_thread") as enrich:
            (Path(temporary)/f"{job_id}.json").write_text("{}",encoding="utf8")
            (Path(temporary)/f"{job_id}.xlsx").write_bytes(b"fixture")
            m.run_import_preview_job(job_id,rows,target,name)
            job = m.import_preview_job_snapshot(job_id)
            self.assertEqual(job["status"],"complete",job.get("message"))
            self.assertFalse((Path(temporary)/f"{job_id}.json").exists())
            self.assertFalse((Path(temporary)/f"{job_id}.xlsx").exists())
            calls = list(enrich.call_args_list)
        self.db.expire_all()
        return job["result"], calls

    def test_new_job_preserves_existing_and_enriches_only_new(self):
        result,calls = self.run_job([self.replacement(),{"word":"brandnew","english_definition":"new entry"}])
        self.assertEqual(result["existing_word_policy"],"preserve")
        self.assertEqual(result["count"],2)
        new_word = self.db.scalar(select(Word).where(Word.word=="brandnew"))
        self.assertEqual(calls[0].args,([new_word.id],))
        self.assertEqual(calls[0].kwargs,{"include_images":False})
        self.assert_original_unchanged()

    def test_existing_target_job_preserves_word_and_list_metadata(self):
        original_list = snapshot(self.old_list)
        result,calls = self.run_job([self.replacement()],str(self.old_list.id),"Must not rename")
        self.assertEqual(result["existing_word_policy"],"preserve")
        self.assertEqual(result["word_list_id"],self.old_list.id)
        self.assertEqual((result["added_count"],result["skipped_count"]),(0,1))
        self.assertEqual(calls,[])
        self.assertEqual(snapshot(self.db.get(WordList,self.old_list.id)),original_list)
        self.assert_original_unchanged()

    def test_continue_mixed_rows_only_appends_missing_links_and_enriches_new_words(self):
        shared = Word(word="shared",english_definition="shared original",enrichment_status="ready")
        self.db.add(shared)
        self.db.commit()
        self.db.add(WordListItem(word_list_id=self.new_list.id,word_id=shared.id))
        self.db.commit()
        shared_before = snapshot(shared)
        old_link_ids = list(self.db.scalars(select(WordListItem.id).where(
            WordListItem.word_list_id==self.old_list.id)).all())
        rows = [self.replacement(),{"word":"SHARED","english_definition":"must not replace"},
            {"word":"brandnew","english_definition":"new entry"}]
        result,calls = self.run_job(rows,str(self.old_list.id),self.old_list.name)
        new_word = self.db.scalar(select(Word).where(Word.word=="brandnew"))
        self.assertEqual((result["added_count"],result["skipped_count"]),(2,1))
        self.assertEqual(calls[0].args,([new_word.id],))
        links = self.db.scalars(select(WordListItem).where(
            WordListItem.word_list_id==self.old_list.id).order_by(WordListItem.id)).all()
        self.assertEqual([link.word_id for link in links],[self.word.id,shared.id,new_word.id])
        self.assertEqual([link.id for link in links[:1]],old_link_ids)
        self.assertEqual(snapshot(self.db.get(Word,shared.id)),shared_before)
        self.assert_original_unchanged()

    def test_repeated_continue_import_is_idempotent(self):
        rows = [self.replacement(),{"word":"brandnew","english_definition":"first"}]
        result,_ = self.run_job(rows,str(self.old_list.id),self.old_list.name)
        self.assertEqual(result["added_count"],1)
        words_before = [snapshot(word) for word in self.db.scalars(select(Word).order_by(Word.id))]
        pool_before = [snapshot(row) for row in self.db.scalars(select(WordResourcePool).order_by(WordResourcePool.id))]
        links_before = [snapshot(row) for row in self.db.scalars(select(WordListItem).order_by(WordListItem.id))]
        rows[1]["english_definition"] = "must not replace first"
        repeated,calls = self.run_job(rows,str(self.old_list.id),"Must not rename")
        self.assertEqual((repeated["added_count"],repeated["skipped_count"]),(0,2))
        self.assertEqual(calls,[])
        self.assertEqual([snapshot(word) for word in self.db.scalars(select(Word).order_by(Word.id))],words_before)
        self.assertEqual([snapshot(row) for row in self.db.scalars(select(WordResourcePool).order_by(WordResourcePool.id))],pool_before)
        self.assertEqual([snapshot(row) for row in self.db.scalars(select(WordListItem).order_by(WordListItem.id))],links_before)
        self.assert_original_unchanged()

    def test_large_continue_import_never_splits_clears_or_changes_group(self):
        group = WordListGroup(name="Original group",display_order=-30)
        self.db.add(group)
        self.db.flush()
        self.old_list.group_id = group.id
        self.old_list.sequence_offset = 500
        unrelated = WordList(name="Book-1",sequence_offset=77)
        self.db.add(unrelated)
        self.db.commit()
        self.db.add(WordListItem(word_list_id=unrelated.id,word_id=self.word.id))
        self.db.commit()
        lists_before = [snapshot(row) for row in self.db.scalars(select(WordList).order_by(WordList.id))]
        groups_before = [snapshot(row) for row in self.db.scalars(select(WordListGroup).order_by(WordListGroup.id))]
        with patch.object(m,"clear_word_list_items") as clear:
            result,calls = self.run_job([self.replacement() for _ in range(501)],str(self.old_list.id),"Book")
        clear.assert_not_called()
        self.assertEqual(result["split_word_lists"],[])
        self.assertEqual(result["word_list_id"],self.old_list.id)
        self.assertEqual((result["added_count"],result["skipped_count"]),(0,501))
        self.assertEqual(calls,[])
        self.assertEqual([snapshot(row) for row in self.db.scalars(select(WordList).order_by(WordList.id))],lists_before)
        self.assertEqual([snapshot(row) for row in self.db.scalars(select(WordListGroup).order_by(WordListGroup.id))],groups_before)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(WordListItem).where(
            WordListItem.word_list_id==unrelated.id)),1)
        self.assert_original_unchanged()

    def test_large_continue_preview_reports_one_existing_target(self):
        job_id = uuid4().hex
        self.addCleanup(m.IMPORT_PREVIEW_JOBS.pop,job_id,None)
        with TemporaryDirectory() as temporary, patch.object(m,"PREVIEW_DIR",Path(temporary)), \
                patch.object(m,"parse_words_from_preview",return_value=[self.replacement() for _ in range(501)]), \
                patch.object(m,"Thread") as thread:
            (Path(temporary)/f"{job_id}.json").write_text(json.dumps({"rows":[{"index":0}],"columns":["word"]}),encoding="utf8")
            response = asyncio.run(m.vue_import_preview(preview_id=job_id,word_list_id=str(self.old_list.id),
                word_list_name="Book",word_columns=["word"],selected_rows=[0],selected_columns=["word"],
                image_files=[],db=self.db))
        payload = json.loads(response.body)
        self.assertEqual(payload["job"]["total_lists"],1)
        self.assertIn("已有词表",payload["job"]["message"])
        thread.return_value.start.assert_called_once()
        self.assert_original_unchanged()

    def test_missing_and_invalid_targets_are_protected_new_lists(self):
        for target in ("", " ", "invalid", "999999"):
            with self.subTest(target=target):
                result,calls = self.run_job([self.replacement()],target)
                self.assertEqual(result["existing_word_policy"],"preserve")
                self.assertNotEqual(result["word_list_id"],self.old_list.id)
                self.assertEqual(calls,[])
                self.assert_original_unchanged()

    def test_new_job_with_same_name_creates_distinct_list(self):
        result,calls = self.run_job([self.replacement()],name=self.old_list.name)
        self.assertNotEqual(result["word_list_id"],self.old_list.id)
        self.assertEqual(calls,[])
        self.assert_original_unchanged()

    def test_new_auto_split_preserves_same_named_old_lists(self):
        group = WordListGroup(name="Book",display_order=-30)
        self.db.add(group)
        self.db.flush()
        old_splits = [WordList(name=f"Book-{number}",group_id=group.id,sequence_offset=number*50)
            for number in (1,2)]
        self.db.add_all(old_splits)
        self.db.commit()
        for old in old_splits:
            self.db.add(WordListItem(word_list_id=old.id,word_id=self.word.id))
        self.db.commit()
        old_snapshots = [snapshot(old) for old in old_splits]
        old_ids = {old.id for old in old_splits}
        group_before = snapshot(group)
        result,calls = self.run_job([self.replacement() for _ in range(501)],name="Book")
        new_ids = {row["id"] for row in result["split_word_lists"]}
        self.assertEqual(len(new_ids),2)
        self.assertTrue(new_ids.isdisjoint(old_ids))
        self.assertEqual(calls,[])
        for old,before in zip(old_splits,old_snapshots):
            self.assertEqual(snapshot(self.db.get(WordList,old.id)),before)
            self.assertEqual(self.db.scalar(select(func.count()).select_from(WordListItem).where(
                WordListItem.word_list_id==old.id)),1)
        self.assertEqual(snapshot(self.db.get(WordListGroup,group.id)),group_before)
        self.assert_original_unchanged()


if __name__ == "__main__":
    unittest.main()
