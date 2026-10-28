import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import CatWorldEnergyGrant
from app.services import fun_math as m


NOW = datetime(2026, 10, 28, 4, 0, tzinfo=timezone.utc)
PHONE = "13900000000"
DAY = "2026-10-28"


class FunMathTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)

    def start(self, question_id=1, now=NOW, phone=PHONE, day=DAY):
        return m.start_question(self.db, phone, question_id, day, now)

    def submit(self, answer, question_id=1, now=NOW + timedelta(seconds=1), phone=PHONE, day=DAY):
        return m.submit_answer(self.db, phone, question_id, day, answer, now)

    def answer(self, payload, index=0):
        q = payload["questions"][index]
        return q["left"] * q["right"]

    def grants(self):
        return self.db.scalars(select(CatWorldEnergyGrant)).all()

    def test_daily_set_fixed_three_digits_unique_and_unstarted_hidden(self):
        first = m.get_daily_payload(self.db, PHONE, NOW)
        again = m.get_daily_payload(self.db, PHONE, NOW + timedelta(minutes=2))
        self.assertEqual(first["questions"], again["questions"])
        self.assertEqual(first["total"], 5)
        self.assertEqual(first["nextQuestionId"], 1)
        self.assertIsNone(first["activeQuestionId"])
        for q in first["questions"]:
            self.assertEqual(q, {"id": q["id"], "status": "pending", "reward": 0})
        row = self.db.scalar(select(m.MathDailySession))
        stored = json.loads(row.questions_json)
        pairs = set()
        for q in stored:
            self.assertTrue(100 <= q["left"] <= 999)
            self.assertTrue(100 <= q["right"] <= 999)
            pairs.add(tuple(sorted([q["left"], q["right"]])))
        self.assertEqual(len(pairs), 5)
        self.assertEqual(self.grants(), [])

    def test_generator_deduplicates_commuted_multiplications(self):
        with patch.object(m.secrets, "randbelow", side_effect=[1, 2, 2, 1, 3, 4, 5, 6, 7, 8, 9, 10]):
            qs = m._new_questions()
        self.assertEqual(len(qs), 5)
        self.assertEqual((qs[1]["left"], qs[1]["right"]), (103, 104))

    def test_start_and_refresh_do_not_reset_clock_or_leak_answer(self):
        started = self.start()
        refreshed = m.get_daily_payload(self.db, PHONE, NOW + timedelta(seconds=50))
        restarted = self.start(now=NOW + timedelta(seconds=60))
        self.assertEqual(started["questions"], refreshed["questions"])
        self.assertEqual(started["questions"], restarted["questions"])
        q = started["questions"][0]
        self.assertEqual(q["deadlineAt"], "2026-10-28T04:10:00.000000Z")
        self.assertNotIn("answer", q)
        self.assertNotIn("submittedAnswer", q)
        self.assertIsNone(started["nextQuestionId"])
        self.assertNotIn("left", started["questions"][1])

    def test_correct_awards_once_and_duplicate_different_answer_is_harmless(self):
        a = self.answer(self.start())
        result = self.submit(a)
        replay = self.submit(0)
        self.assertEqual(result["earnedEnergy"], 100)
        self.assertEqual(result["result"]["awardedEnergy"], 100)
        self.assertEqual(replay["result"]["awardedEnergy"], 0)
        self.assertEqual(replay["questions"][0]["submittedAnswer"], a)
        self.assertEqual(replay["questions"][0]["answer"], a)
        self.assertEqual(replay["nextQuestionId"], 2)
        self.assertEqual(len(self.grants()), 1)
        self.assertEqual(self.grants()[0].amount, 100)
        self.assertEqual(self.grants()[0].granted_by_phone, "fun-math")

    def test_wrong_answer_is_final_and_receives_no_energy(self):
        a = self.answer(self.start())
        wrong = self.submit(a + 1)
        self.assertEqual(wrong["questions"][0]["status"], "incorrect")
        self.assertEqual(wrong["questions"][0]["answer"], a)
        replay = self.submit(a)
        self.assertEqual(replay["result"]["status"], "incorrect")
        self.assertEqual(replay["earnedEnergy"], 0)
        self.assertEqual(self.grants(), [])

    def test_order_cannot_be_skipped_or_submitted_without_start(self):
        for call in (lambda: self.start(2), lambda: self.submit(0)):
            with self.assertRaises(HTTPException) as raised:
                call()
            self.assertEqual(raised.exception.status_code, 409)
        self.start()
        with self.assertRaises(HTTPException):
            self.start(2)

    def test_just_before_deadline_accepted(self):
        a = self.answer(self.start())
        result = self.submit(a, now=NOW + timedelta(seconds=600, microseconds=-1))
        self.assertEqual(result["result"]["awardedEnergy"], 100)

    def test_exact_deadline_expired_and_restart_does_not_reset(self):
        a = self.answer(self.start())
        result = self.submit(a, now=NOW + timedelta(seconds=600))
        restarted = self.start(now=NOW + timedelta(seconds=601))
        self.assertEqual(result["result"]["status"], "expired")
        self.assertEqual(restarted["questions"][0]["status"], "expired")
        self.assertEqual(result["nextQuestionId"], 2)
        self.assertEqual(self.grants(), [])

    def test_get_persists_expiry_and_reveals_only_finished_answer(self):
        a = self.answer(self.start())
        result = m.get_daily_payload(self.db, PHONE, NOW + timedelta(seconds=700))
        self.assertEqual(result["questions"][0]["answer"], a)
        self.assertEqual(result["questions"][0]["status"], "expired")
        self.assertNotIn("answer", result["questions"][1])
        self.assertEqual(result["earnedEnergy"], 0)
        # A stale client cannot replay an earlier timestamp (server supplies now).
        self.assertEqual(m.get_daily_payload(self.db, PHONE, NOW)["questions"][0]["status"], "expired")

    def test_five_correct_questions_cap_500_even_on_festival(self):
        now = datetime(2026, 10, 31, 4, 0, tzinfo=timezone.utc)
        for number in range(1, 6):
            payload = self.start(number, now, day="2026-10-31")
            result = self.submit(self.answer(payload, number - 1), number, now + timedelta(seconds=1), day="2026-10-31")
            now += timedelta(seconds=2)
        self.assertEqual(result["completed"], 5)
        self.assertEqual(result["correct"], 5)
        self.assertEqual(result["earnedEnergy"], 500)
        self.assertIsNone(result["nextQuestionId"])
        self.assertEqual(sum(g.amount for g in self.grants()), 500)

    def test_invalid_answers_do_not_consume_attempt(self):
        a = self.answer(self.start())
        for answer in (True, False, 3.0, "1e5", "1.0", "-1", -1, None, [], {}, "１２３", "9999999", 1000000):
            with self.subTest(answer=answer), self.assertRaises(HTTPException) as raised:
                self.submit(answer)
            self.assertEqual(raised.exception.status_code, 400)
        result = self.submit(f" {a} ")
        self.assertEqual(result["correct"], 1)

    def test_invalid_question_identifiers(self):
        for number in (0, 6, True, "1", 1.0, None):
            with self.subTest(number=number), self.assertRaises(HTTPException) as raised:
                self.start(number)
            self.assertEqual(raised.exception.status_code, 400)

    def test_accounts_have_independent_attempts_and_rewards(self):
        a = self.answer(self.start())
        self.submit(a)
        other = m.get_daily_payload(self.db, "13900000001", NOW)
        self.assertEqual(other["earnedEnergy"], 0)
        with self.assertRaises(HTTPException):
            self.submit(a, phone="13900000001")
        self.assertEqual([g.phone for g in self.grants()], [PHONE])

    def test_empty_phone_rejected(self):
        for phone in (None, "", " ", "x" * 33):
            with self.assertRaises(HTTPException) as raised:
                m.get_daily_payload(self.db, phone, NOW)
            self.assertEqual(raised.exception.status_code, 401)

    def test_beijing_rollover_caps_deadline_and_preserves_previous_rewards(self):
        before = datetime(2026, 10, 28, 15, 59, 30, tzinfo=timezone.utc)
        first = self.start(now=before)
        self.assertEqual(first["day"], "2026-10-28")
        self.assertEqual(first["questions"][0]["deadlineAt"], "2026-10-28T16:00:00.000000Z")
        self.submit(self.answer(first), now=before + timedelta(seconds=1))
        self.start(2, now=before + timedelta(seconds=2))
        after = datetime(2026, 10, 28, 16, 0, tzinfo=timezone.utc)
        fresh = m.get_daily_payload(self.db, PHONE, after)
        self.assertEqual(fresh["day"], "2026-10-29")
        self.assertEqual(fresh["earnedEnergy"], 0)
        self.assertEqual(fresh["nextQuestionId"], 1)
        with self.assertRaises(HTTPException) as raised:
            self.submit(0, 2, after)
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(len(self.grants()), 1)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(m.MathDailySession)), 2)

    def test_naive_datetimes_are_utc(self):
        result = m.get_daily_payload(self.db, PHONE, datetime(2026, 10, 28, 16, 1))
        self.assertEqual(result["day"], "2026-10-29")

    def test_grant_failure_rolls_back_correct_status(self):
        a = self.answer(self.start())
        original_add = self.db.add
        def fail_grant(instance, *args, **kwargs):
            if isinstance(instance, CatWorldEnergyGrant):
                raise RuntimeError("simulated grant insert failure")
            return original_add(instance, *args, **kwargs)
        with patch.object(self.db, "add", side_effect=fail_grant), self.assertRaises(RuntimeError):
            self.submit(a)
        self.assertEqual(m.get_daily_payload(self.db, PHONE, NOW)["questions"][0]["status"], "active")
        self.assertEqual(self.grants(), [])
        self.assertEqual(self.submit(a)["result"]["awardedEnergy"], 100)

    def test_stale_cas_retries_from_latest_state_without_duplicate_grant(self):
        a = self.answer(self.start())
        original_execute = self.db.execute
        missed = False
        class Conflict:
            rowcount = 0
        def conflict_once(statement, *args, **kwargs):
            nonlocal missed
            if getattr(statement, "is_update", False) and not missed:
                missed = True
                return Conflict()
            return original_execute(statement, *args, **kwargs)
        with patch.object(self.db, "execute", side_effect=conflict_once):
            result = self.submit(a)
        self.assertTrue(missed)
        self.assertEqual(result["result"]["awardedEnergy"], 100)
        self.assertEqual(len(self.grants()), 1)

    def test_exhausted_conflicts_return_retryable_error_without_rewards(self):
        a = self.answer(self.start())
        original_execute = self.db.execute
        class Conflict:
            rowcount = 0
        def always_conflict(statement, *args, **kwargs):
            if getattr(statement, "is_update", False):
                return Conflict()
            return original_execute(statement, *args, **kwargs)
        with patch.object(self.db, "execute", side_effect=always_conflict), self.assertRaises(HTTPException) as raised:
            self.submit(a)
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(self.grants(), [])
        self.assertEqual(m.get_daily_payload(self.db, PHONE, NOW)["questions"][0]["status"], "active")


class FunMathConcurrencyTest(unittest.TestCase):
    def test_concurrent_creation_start_and_submit_award_exactly_once(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = create_engine(f"sqlite+pysqlite:///{Path(directory) / 'math.db'}", connect_args={"timeout": 15})
            Base.metadata.create_all(engine)
            try:
                start_barrier = Barrier(4)
                def start():
                    with Session(engine) as db:
                        start_barrier.wait()
                        return m.start_question(db, PHONE, 1, DAY, NOW)
                with ThreadPoolExecutor(max_workers=4) as pool:
                    starts = list(pool.map(lambda _: start(), range(4)))
                self.assertTrue(all(s["questions"] == starts[0]["questions"] for s in starts))
                question = starts[0]["questions"][0]
                answer = question["left"] * question["right"]
                submit_barrier = Barrier(4)
                def submit():
                    with Session(engine) as db:
                        submit_barrier.wait()
                        return m.submit_answer(db, PHONE, 1, DAY, answer, NOW + timedelta(seconds=1))
                with ThreadPoolExecutor(max_workers=4) as pool:
                    results = list(pool.map(lambda _: submit(), range(4)))
                self.assertEqual(sum(r["result"]["awardedEnergy"] for r in results), 100)
                with Session(engine) as db:
                    self.assertEqual(db.scalar(select(func.count()).select_from(m.MathDailySession)), 1)
                    self.assertEqual(db.scalar(select(func.count()).select_from(CatWorldEnergyGrant)), 1)
                    self.assertEqual(m.get_daily_payload(db, PHONE, NOW + timedelta(seconds=2))["earnedEnergy"], 100)
            finally:
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
