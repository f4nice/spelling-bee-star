import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app import main as m
from app.database import Base
from app.models import Word, WordList, WordListItem
from app.services.list_completion_jobs import ListCompletionJobs, TEXT_FIELDS, missing_text_fields


COMPLETE = dict(phonetic="/word/", part_of_speech="n.", english_definition="A meaning.",
                chinese_definition="中文释义", english_example="This is an example.")


class DeferredThread:
    created = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.created.append(self)

    def start(self):
        pass


class ListCompletionTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(self.engine)
        self.db = self.factory()
        self.list = WordList(name="Current list")
        self.other_list = WordList(name="Other list")
        self.db.add_all([self.list, self.other_list])
        self.db.commit()
        DeferredThread.created.clear()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def word(self, name, *, list_id=None, **fields):
        word = Word(word=name, **fields)
        self.db.add(word)
        self.db.flush()
        self.db.add(WordListItem(word_id=word.id, word_list_id=list_id or self.list.id))
        self.db.commit()
        return word

    def jobs(self, callback=None, **kwargs):
        return ListCompletionJobs(self.factory, callback or AsyncMock(), thread_factory=DeferredThread, **kwargs)

    def test_selection_uses_same_five_trimmed_fields_as_filter(self):
        for field in TEXT_FIELDS:
            for empty in (None, "", " \n\t", 0, False):
                with self.subTest(field=field, empty=empty):
                    values = dict(COMPLETE, **{field: empty, field + "_locked": True})
                    self.assertEqual(missing_text_fields(SimpleNamespace(**values)), [field])
        self.assertEqual(missing_text_fields(SimpleNamespace(**COMPLETE, enrichment_status="failed")), [])

    def test_start_selects_only_incomplete_words_in_requested_list(self):
        complete = self.word("complete", **COMPLETE)
        missing = self.word("missing", **dict(COMPLETE, chinese_definition="  "))
        locked = self.word("locked", **dict(COMPLETE, english_example=None), english_example_locked=True)
        other = self.word("other", list_id=self.other_list.id)
        manager = self.jobs()
        with patch.object(m, "LIST_COMPLETION_JOBS", manager):
            self.assertIsNone(m.vue_list_completion_status(self.list.id, self.db))
            job = m.vue_start_list_completion(self.list.id, "1", self.db)
            self.assertEqual(job["total"], 2)
            self.assertEqual(manager.queue[0][1], [missing.id, locked.id])
            self.assertNotIn(complete.id, manager.queue[0][1])
            self.assertNotIn(other.id, manager.queue[0][1])
            self.assertEqual(m.vue_list_completion_status(self.list.id, self.db)["id"], job["id"])

    def test_routes_require_write_token_existing_list_and_matching_job(self):
        manager = self.jobs()
        with patch.object(m, "LIST_COMPLETION_JOBS", manager):
            for token in ("", "0", "wrong"):
                with self.assertRaises(HTTPException) as raised:
                    m.vue_start_list_completion(self.list.id, token, self.db)
                self.assertEqual(raised.exception.status_code, 403)
                with self.assertRaises(HTTPException) as raised:
                    m.vue_stop_list_completion(self.list.id, "any", token, self.db)
                self.assertEqual(raised.exception.status_code, 403)
            with self.assertRaises(HTTPException) as raised:
                m.vue_start_list_completion(99999, "1", self.db)
            self.assertEqual(raised.exception.status_code, 404)
            with self.assertRaises(HTTPException):
                m.vue_list_completion_status(99999, self.db)
            with self.assertRaises(HTTPException):
                m.vue_stop_list_completion(self.list.id, "unknown", "1", self.db)
            job = manager.start(self.other_list.id, [123])
            with self.assertRaises(HTTPException):
                m.vue_stop_list_completion(self.list.id, job["id"], "1", self.db)

    def http_client(self):
        # Exercise the real route definitions without main.app's startup,
        # production database, login middleware, or external services.
        app = FastAPI()
        for route in m.app.routes:
            if route.path.startswith("/api/vue/lists/{word_list_id}/completion"):
                app.add_api_route(route.path, route.endpoint, methods=route.methods)
        app.dependency_overrides[m.get_db] = lambda: self.db
        return TestClient(app)

    def test_http_status_null_start_form_raw_job_and_restored_status(self):
        self.word("http")
        manager = self.jobs()
        url = f"/api/vue/lists/{self.list.id}/completion"
        with patch.object(m, "LIST_COMPLETION_JOBS", manager), self.http_client() as client:
            self.assertIsNone(client.get(url).json())
            response = client.post(url + "/start", data={"edit_token": "1"})
            self.assertEqual(response.status_code, 200)
            job = response.json()
            self.assertEqual(job["total"], 1)
            self.assertEqual(job["status"], "queued")
            self.assertNotIn("job", job)  # No inconsistent envelope.
            self.assertEqual(client.get(url).json()["id"], job["id"])
            self.assertEqual(client.post(url + "/start", data={"edit_token": "1"}).json()["id"], job["id"])

    def test_http_stop_returns_raw_job_and_cannot_stop_different_list(self):
        manager = self.jobs()
        job = manager.start(self.list.id, [123])
        with patch.object(m, "LIST_COMPLETION_JOBS", manager), self.http_client() as client:
            wrong = client.post(f"/api/vue/lists/{self.other_list.id}/completion/{job['id']}/stop", data={"edit_token": "1"})
            self.assertEqual(wrong.status_code, 404)
            stopped = client.post(f"/api/vue/lists/{self.list.id}/completion/{job['id']}/stop", data={"edit_token": "1"})
            self.assertEqual(stopped.status_code, 200)
            self.assertEqual(stopped.json()["status"], "stopped")
            self.assertEqual(stopped.json()["id"], job["id"])

    def test_http_validation_denies_missing_token_bad_id_and_missing_list_job(self):
        with patch.object(m, "LIST_COMPLETION_JOBS", self.jobs()), self.http_client() as client:
            root = f"/api/vue/lists/{self.list.id}/completion"
            self.assertEqual(client.post(root + "/start").status_code, 403)
            self.assertEqual(client.post(root + "/unknown/stop").status_code, 403)
            self.assertEqual(client.post(root + "/unknown/stop", data={"edit_token": "1"}).status_code, 404)
            self.assertEqual(client.get("/api/vue/lists/invalid/completion").status_code, 422)
            self.assertEqual(client.get("/api/vue/lists/99999/completion").status_code, 404)
            self.assertEqual(client.post("/api/vue/lists/99999/completion/start", data={"edit_token": "1"}).status_code, 404)

    def test_empty_job_finishes_without_worker(self):
        manager = self.jobs()
        job = manager.start(self.list.id, [])
        self.assertEqual(job["status"], "complete")
        self.assertEqual(job["total"], 0)
        self.assertEqual(DeferredThread.created, [])

    def test_active_starts_deduplicated_and_only_one_global_worker(self):
        first = self.word("first")
        second = self.word("second", list_id=self.other_list.id)
        seen = []

        async def complete(db, word, **kwargs):
            seen.append((word.word, kwargs["list_id"]))
            for field, value in COMPLETE.items():
                setattr(word, field, value)
            db.commit()

        manager = self.jobs(complete)
        job = manager.start(self.list.id, [first.id, first.id])
        duplicate = manager.start(self.list.id, [second.id])
        manager.start(self.other_list.id, [second.id])
        self.assertEqual(job["id"], duplicate["id"])
        self.assertEqual(job["total"], 1)
        self.assertEqual(len(DeferredThread.created), 1)
        manager._work()
        self.assertEqual(seen, [("first", self.list.id), ("second", self.other_list.id)])
        self.assertFalse(manager.worker_running)
        self.assertEqual(manager.current(self.list.id)["completed"], 1)
        self.assertEqual(manager.current(self.other_list.id)["completed"], 1)

    def test_queued_cancel_and_retry(self):
        word = self.word("queued")
        callback = AsyncMock()
        manager = self.jobs(callback)
        old = manager.start(self.list.id, [word.id])
        self.assertEqual(manager.stop(self.list.id, old["id"])["status"], "stopped")
        manager._work()
        callback.assert_not_awaited()
        retry = manager.start(self.list.id, [word.id])
        self.assertNotEqual(old["id"], retry["id"])
        self.assertEqual(retry["status"], "queued")

    def test_running_cancel_stops_after_current_word_commits(self):
        first = self.word("first")
        second = self.word("second")
        manager = None

        async def complete(db, word, **kwargs):
            job = manager.current(self.list.id)
            stopped = manager.stop(self.list.id, job["id"])
            self.assertEqual(stopped["status"], "stopping")
            # A second start while stopping must not launch another worker.
            self.assertEqual(manager.start(self.list.id, [second.id])["id"], job["id"])
            word.english_definition = "Saved before stopping."
            db.commit()

        manager = self.jobs(complete)
        manager.start(self.list.id, [first.id, second.id])
        manager._work()
        job = manager.current(self.list.id)
        self.assertEqual(job["status"], "stopped")
        self.assertEqual(job["done"], 1)
        self.db.expire_all()
        self.assertEqual(first.english_definition, "Saved before stopping.")
        self.assertIsNone(second.english_definition)

    def test_failure_rollback_does_not_poison_next_word_or_expose_secrets(self):
        first = self.word("failure")
        second = self.word("success")

        async def complete(db, word, **kwargs):
            if word.word == "failure":
                word.chinese_definition = "must roll back"
                db.flush()
                raise RuntimeError("https://secret:password@upstream.invalid")
            for field, value in COMPLETE.items():
                setattr(word, field, value)
            db.commit()

        manager = self.jobs(complete)
        manager.start(self.list.id, [first.id, second.id])
        manager._work()
        job = manager.current(self.list.id)
        self.assertEqual((job["status"], job["done"], job["failed"], job["completed"]), ("complete", 2, 1, 1))
        self.assertNotIn("password", str(job))
        self.db.expire_all()
        self.assertIsNone(first.chinese_definition)
        self.assertEqual(second.chinese_definition, COMPLETE["chinese_definition"])

    def test_timeout_continues_and_counts_failure(self):
        slow = self.word("slow")
        next_word = self.word("next")

        async def complete(db, word, **kwargs):
            if word.word == "slow":
                await asyncio.sleep(1)
            word.english_definition = "Some content"
            db.commit()

        manager = self.jobs(complete, word_timeout=0.01)
        manager.start(self.list.id, [slow.id, next_word.id])
        manager._work()
        job = manager.current(self.list.id)
        self.assertEqual((job["done"], job["failed"], job["partial"]), (2, 1, 1))
        self.assertIn("超时", job["results"][0]["message"])

    def test_interrupted_provider_reports_text_already_committed(self):
        complete = self.word("saved-complete")
        partial = self.word("saved-partial")

        async def provider(db, word, **kwargs):
            fields = COMPLETE if word.word == "saved-complete" else {"phonetic": "/saved/"}
            for field, value in fields.items():
                setattr(word, field, value)
            db.commit()
            await asyncio.sleep(1)

        manager = self.jobs(provider, word_timeout=0.01)
        manager.start(self.list.id, [complete.id, partial.id])
        manager._work()
        job = manager.current(self.list.id)
        self.assertEqual((job["completed"], job["partial"], job["failed"]), (1, 1, 0))
        self.assertEqual(job["results"][0]["missing_fields"], [])
        self.assertNotIn("phonetic", job["results"][1]["missing_fields"])

    def test_rechecks_membership_completeness_and_fully_locked_missing_fields(self):
        complete = self.word("complete", **COMPLETE)
        locked = self.word("locked", **dict(COMPLETE, english_example=None), english_example_locked=True)
        removed = self.word("removed")
        item = self.db.scalar(select(WordListItem).where(WordListItem.word_id == removed.id))
        self.db.delete(item)
        self.db.commit()
        callback = AsyncMock()
        manager = self.jobs(callback)
        manager.start(self.list.id, [complete.id, locked.id, removed.id])
        manager._work()
        job = manager.current(self.list.id)
        self.assertEqual(job["skipped"], 3)
        self.assertEqual(job["results"][1]["missing_fields"], ["english_example"])
        callback.assert_not_awaited()

    def test_returned_status_is_copy_not_shared_mutable_job(self):
        manager = self.jobs()
        job = manager.start(self.list.id, [123])
        job["status"] = "complete"
        snapshot = manager.current(self.list.id)
        snapshot["results"].append({"bad": "mutation"})
        self.assertEqual(manager.current(self.list.id)["status"], "queued")
        self.assertEqual(manager.current(self.list.id)["results"], [])

    def test_batch_wrapper_reuses_shared_spb_first_completion_rule(self):
        word = self.word("wrapped")
        with patch.object(m, "complete_word_from_sources", new=AsyncMock()) as complete:
            asyncio.run(m.complete_list_word_missing_fields(self.db, word, list_id=self.list.id))
            complete.assert_awaited_once_with(self.db, word, list_id=self.list.id, only_missing=True)

    def test_background_word_clears_server_caches_on_success_failure_and_cancellation(self):
        word = self.word("cache")
        for failure in (None, RuntimeError("failure"), asyncio.CancelledError()):
            with self.subTest(failure=failure), \
                 patch.object(m, "complete_word_from_sources", new=AsyncMock(side_effect=failure)), \
                 patch.object(m.word_detail_cache, "clear") as clear_detail, \
                 patch.object(m.public_stats_cache, "clear") as clear_stats:
                if failure is None:
                    asyncio.run(m.complete_list_word_missing_fields(self.db, word, list_id=self.list.id))
                else:
                    with self.assertRaises(type(failure)):
                        asyncio.run(m.complete_list_word_missing_fields(self.db, word, list_id=self.list.id))
                clear_detail.assert_called_once_with()
                clear_stats.assert_called_once_with()

    def test_batch_protects_existing_and_locked_values_even_inside_provider_commit(self):
        word = self.word("preserve", **dict(COMPLETE, chinese_definition=None, english_example=None),
                         english_example_locked=True, american_audio_url="/media/audio/manual.mp3", american_audio_locked=True,
                         british_audio_locked=True, image_url="/media/manual.png", image_locked=True)
        seen = []

        def pool(db, word, **kwargs):
            word.english_definition = "Pool replacement"
            word.british_audio_url = "/media/audio/pool.mp3"

        async def spb(db, word, **kwargs):
            self.assertTrue(kwargs["only_missing"])
            self.assertTrue(kwargs["search_all_groups"])
            self.assertEqual(word.english_definition, COMPLETE["english_definition"])
            self.assertIsNone(word.british_audio_url)
            seen.append("spb")
            word.english_definition = "Replacement"
            word.english_example = "Must stay empty because locked"
            word.american_audio_url = "/media/audio/replacement.mp3"
            word.american_audio_locked = False
            word.image_url = "/media/replacement.png"
            db.commit()  # The guard must work at internal commits too.

        async def online(db, word, **kwargs):
            seen.append("online")
            self.assertEqual(kwargs, {"include_images": False, "only_missing": True})
            self.assertEqual(word.english_definition, COMPLETE["english_definition"])
            word.chinese_definition = "补充的中文"
            word.enrichment_status = "done"
            db.commit()

        with patch.object(m, "apply_word_resource", side_effect=pool), \
             patch.object(m, "apply_spb_details_to_word", side_effect=spb), \
             patch.object(m, "enrich_word", side_effect=online), \
             patch.object(m, "remember_word_resource"):
            asyncio.run(m.complete_word_from_sources(self.db, word, list_id=self.list.id, only_missing=True))
        self.db.expire_all()
        self.assertEqual(seen, ["spb", "online"])
        self.assertEqual(word.english_definition, COMPLETE["english_definition"])
        self.assertEqual(word.chinese_definition, "补充的中文")
        self.assertIsNone(word.english_example)
        self.assertTrue(word.english_example_locked)
        self.assertEqual(word.american_audio_url, "/media/audio/manual.mp3")
        self.assertTrue(word.american_audio_locked)
        self.assertIsNone(word.british_audio_url)
        self.assertEqual(word.image_url, "/media/manual.png")

    def test_batch_keeps_concurrent_manual_edits_and_locks_after_provider_refresh(self):
        for internal_commit in (False, True):
            with self.subTest(internal_commit=internal_commit):
                word = self.word(f"concurrent-{internal_commit}", **dict(COMPLETE, chinese_definition=None),
                                 american_audio_url="/media/audio/original.mp3")

                async def spb(db, candidate, **kwargs):
                    # A separate request edits both previously existing and
                    # initially missing fields while this provider is awaited.
                    with self.factory() as editor:
                        edited = editor.get(Word, candidate.id)
                        edited.english_definition = "Manual correction during lookup"
                        edited.english_definition_locked = True
                        edited.english_definition_audio_url = "/media/audio/manual-definition.mp3"
                        edited.chinese_definition = "刚刚手动输入的中文"
                        edited.chinese_definition_locked = True
                        edited.english_example = None
                        edited.english_example_locked = True
                        edited.american_audio_url = "/media/audio/manual-recording.mp3"
                        edited.american_audio_locked = True
                        editor.commit()
                    db.refresh(candidate)
                    candidate.english_definition = "Stale provider response"
                    candidate.english_definition_locked = False
                    candidate.chinese_definition = "旧的在线释义"
                    candidate.english_example = "An unwanted example after explicit clearing."
                    candidate.american_audio_url = "/media/audio/stale.mp3"
                    if internal_commit:
                        db.commit()
                        db.refresh(candidate)

                with patch.object(m, "apply_word_resource"), \
                     patch.object(m, "apply_spb_details_to_word", side_effect=spb), \
                     patch.object(m, "enrich_word", new=AsyncMock()), \
                     patch.object(m, "remember_word_resource"):
                    asyncio.run(m.complete_word_from_sources(self.db, word, list_id=self.list.id, only_missing=True))
                with self.factory() as verifier:
                    saved = verifier.get(Word, word.id)
                    self.assertEqual(saved.english_definition, "Manual correction during lookup")
                    self.assertTrue(saved.english_definition_locked)
                    self.assertEqual(saved.english_definition_audio_url, "/media/audio/manual-definition.mp3")
                    self.assertEqual(saved.chinese_definition, "刚刚手动输入的中文")
                    self.assertTrue(saved.chinese_definition_locked)
                    self.assertIsNone(saved.english_example)
                    self.assertTrue(saved.english_example_locked)
                    self.assertEqual(saved.american_audio_url, "/media/audio/manual-recording.mp3")
                    self.assertTrue(saved.american_audio_locked)

    def test_real_spb_application_filters_existing_and_locked_fields_before_resource_remember(self):
        word = self.word("spb", **dict(COMPLETE, chinese_definition=None, english_example=None), english_example_locked=True)
        row = dict(COMPLETE, english_definition="Different SPB meaning", spb_text_source="spb-miniprogram")
        group = {"prefix": "current"}

        def remember(db, candidate, **kwargs):
            self.assertEqual(candidate.english_definition, COMPLETE["english_definition"])
            self.assertIsNone(candidate.english_example)
            self.assertFalse(kwargs["override_text"])
            self.assertFalse(kwargs["override_media"])

        with patch.object(m, "spb_candidate_groups_for_word", return_value=[group]), \
             patch.object(m, "find_spb_source_row_for_word", return_value=row), \
             patch.object(m, "prepare_spb_rows_with_local_audio", new=AsyncMock(return_value=[dict(row)])), \
             patch.object(m, "remember_word_resource", side_effect=remember):
            asyncio.run(m.apply_spb_details_to_word(self.db, word, only_missing=True))
        self.assertEqual(word.english_definition, COMPLETE["english_definition"])
        self.assertIsNone(word.english_example)
        self.assertTrue(word.english_example_locked)
        self.assertEqual(word.chinese_definition, COMPLETE["chinese_definition"])


if __name__ == "__main__":
    unittest.main()
