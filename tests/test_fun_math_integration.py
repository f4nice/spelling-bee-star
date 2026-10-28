"""Math routes and cat-energy integration; all state is isolated SQLite."""

import asyncio
import json
import os
import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app import main as m
from app.database import Base
from app.models import AdminUserSetting, CatWorldEnergyGrant


PHONE = "13900000000"
OTHER_PHONE = "13900000001"


def math_request(payload=None, *, raw=None, path="/api/vue/fun-math/answer", method="POST"):
    body = raw if raw is not None else json.dumps(payload).encode("utf-8")

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    return Request({"type": "http", "method": method, "path": path,
                    "headers": [], "query_string": b"", "server": ("testserver", 80),
                    "scheme": "http"}, receive)


class FunMathIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        self.db.add(AdminUserSetting(phone=PHONE, username="Math Test", role="admin", is_active=True))
        self.db.commit()
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)

    def grant(self, *, phone=PHONE, amount=100, source=None, when=datetime(2026, 10, 28, 4)):
        self.db.add(CatWorldEnergyGrant(phone=phone, amount=amount, reason="Isolated math reward",
                    granted_by_phone=source or m.FUN_MATH_GRANT_SOURCE, created_at=when))
        self.db.commit()

    def test_no_math_rewards_has_zero_total_and_daily_energy(self):
        source = m.cat_world_math_energy_source(self.db, PHONE, date(2026, 10, 28))
        self.assertEqual(source["key"], "fun_math")
        self.assertEqual(source["label"], "趣味数学")
        self.assertEqual(source["energyPerUnit"], 100)
        self.assertEqual([source[k] for k in ("energy", "value", "todayValue", "todayEnergy")], [0, 0, 0, 0])

    def test_math_is_a_distinct_source_and_not_double_counted_as_special_reward(self):
        self.grant()
        self.grant(amount=37, source="admin-account")
        self.grant(amount=23, source=m.CAT_WORLD_DEBATE_ENERGY_GRANT_SOURCE)
        self.grant(phone=OTHER_PHONE, amount=500)
        math = m.cat_world_math_energy_source(self.db, PHONE, date(2026, 10, 28))
        operating = m.cat_world_operating_energy_source(self.db, PHONE, date(2026, 10, 28))
        debate = m.cat_world_debate_energy_source(self.db, PHONE, date(2026, 10, 28))
        self.assertEqual(math["energy"], 100)
        self.assertEqual(math["grantCount"], 1)
        self.assertEqual(operating["energy"], 37)
        self.assertEqual(debate["energy"], 23)
        # Stub only unrelated sources, preserving the actual grant aggregators.
        with patch.object(m, "cat_world_essay_energy_source", return_value={"energy": 0}), \
             patch.object(m, "cat_world_learning_habit_source", return_value={"energy": 0}), \
             patch.object(m, "festival_energy_source", return_value={"energy": 0}):
            self.assertEqual(m.cat_world_earned_energy(self.db, PHONE, {"points": 7}), 167)
            self.assertEqual(m.cat_world_earned_energy(self.db, OTHER_PHONE, {"points": 7}), 507)

    def test_today_uses_beijing_midnight_utc_boundaries(self):
        for when in (datetime(2026, 10, 27, 15, 59, 59), datetime(2026, 10, 27, 16),
                     datetime(2026, 10, 28, 15, 59, 59), datetime(2026, 10, 28, 16)):
            self.grant(when=when)
        self.grant(phone=OTHER_PHONE, when=datetime(2026, 10, 27, 16))
        source = m.cat_world_math_energy_source(self.db, PHONE, date(2026, 10, 28))
        self.assertEqual(source["energy"], 400)
        self.assertEqual(source["todayEnergy"], 200)
        self.assertEqual(source["todayValue"], 2)
        self.assertEqual(source["todayGrantCount"], 2)

    def test_default_math_day_is_beijing_not_host_day(self):
        self.grant(when=datetime(2026, 10, 27, 17))

        class Clock(datetime):
            @classmethod
            def utcnow(cls):
                return datetime(2026, 10, 27, 17, 30)

        with patch.object(m, "datetime", Clock):
            source = m.cat_world_math_energy_source(self.db, PHONE)
        self.assertEqual(source["todayEnergy"], 100)

    def test_today_rows_display_question_count_and_fixed_rate(self):
        self.grant()
        self.grant()
        source = m.cat_world_math_energy_source(self.db, PHONE, date(2026, 10, 28))
        rows = m.cat_world_today_energy_source_rows({}, {}, {}, {}, math_source=source)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["key"], "fun_math")
        self.assertEqual(rows[0]["value"], 2)
        self.assertEqual(rows[0]["unit"], "题")
        self.assertEqual(rows[0]["energyPerUnit"], 100)
        self.assertEqual(rows[0]["energy"], 200)

    def test_real_correct_submission_credits_cat_energy_once_even_during_festival(self):
        now = datetime(2026, 10, 31, 4, tzinfo=timezone.utc)
        day = m.fun_math_daily_payload(self.db, PHONE, now=now)["day"]
        started = m.fun_math_start_question(self.db, PHONE, 1, day, now=now)
        question = started["questions"][0]
        answer = str(question["left"] * question["right"])
        first = m.fun_math_submit_answer(self.db, PHONE, 1, day, answer, now=now)
        replay = m.fun_math_submit_answer(self.db, PHONE, 1, day, answer, now=now)
        self.assertEqual(first["result"]["awardedEnergy"], 100)
        self.assertEqual(replay["result"]["awardedEnergy"], 0)
        self.assertEqual(len(self.db.scalars(select(CatWorldEnergyGrant)).all()), 1)
        self.assertEqual(m.cat_world_math_energy_source(self.db, PHONE, date(2026, 10, 31))["energy"], 100)
        self.assertEqual(m.cat_world_operating_energy_source(self.db, PHONE)["energy"], 0)
        self.assertEqual(m.cat_world_earned_energy(self.db, PHONE, {"points": 0}), 100)

    def test_all_api_entrypoints_reject_anonymous_before_services_are_called(self):
        with patch.object(m, "authenticated_phone_from_request", return_value=""), \
             patch.object(m, "fun_math_daily_payload") as daily, \
             patch.object(m, "fun_math_start_question") as start, \
             patch.object(m, "fun_math_submit_answer") as answer:
            for endpoint, is_async in ((m.vue_fun_math_api, False), (m.vue_fun_math_start_api, True),
                                       (m.vue_fun_math_answer_api, True)):
                with self.subTest(endpoint=endpoint.__name__), self.assertRaises(HTTPException) as error:
                    call = endpoint(math_request({}), self.db)
                    asyncio.run(call) if is_async else call
                self.assertEqual(error.exception.status_code, 401)
            daily.assert_not_called()
            start.assert_not_called()
            answer.assert_not_called()

    def test_disabled_account_cannot_start_or_submit(self):
        user = self.db.scalar(select(AdminUserSetting).where(AdminUserSetting.phone == PHONE))
        user.is_active = False
        self.db.commit()
        with patch.object(m, "authenticated_phone_from_request", return_value=PHONE):
            for endpoint in (m.vue_fun_math_start_api, m.vue_fun_math_answer_api):
                with self.subTest(endpoint=endpoint.__name__), self.assertRaises(HTTPException) as error:
                    asyncio.run(endpoint(math_request({"questionId": 1, "day": "2026-10-28"}), self.db))
                self.assertEqual(error.exception.status_code, 403)

    def test_api_uses_authenticated_identity_not_client_phone_and_is_not_cacheable(self):
        payload = {"day": "2026-10-28", "questionId": 1, "answer": "123456", "phone": OTHER_PHONE,
                   "reward": 999999, "serverNow": "2099-01-01T00:00:00Z"}
        response_data = {"day": "2026-10-28", "earnedEnergy": 100}
        with patch.object(m, "authenticated_phone_from_request", return_value=PHONE), \
             patch.object(m, "fun_math_daily_payload", return_value=response_data) as daily, \
             patch.object(m, "fun_math_start_question", return_value=response_data) as start, \
             patch.object(m, "fun_math_submit_answer", return_value=response_data) as answer:
            responses = [m.vue_fun_math_api(math_request(method="GET"), self.db),
                         asyncio.run(m.vue_fun_math_start_api(math_request(payload), self.db)),
                         asyncio.run(m.vue_fun_math_answer_api(math_request(payload), self.db))]
            daily.assert_called_once_with(self.db, PHONE)
            start.assert_called_once_with(self.db, PHONE, 1, "2026-10-28")
            answer.assert_called_once_with(self.db, PHONE, 1, "2026-10-28", "123456")
            for response in responses:
                self.assertEqual(response.headers["cache-control"], "no-store")
                self.assertEqual(json.loads(response.body), response_data)

    def test_post_rejects_invalid_json_and_non_object_bodies_without_service_calls(self):
        with patch.object(m, "authenticated_phone_from_request", return_value=PHONE), \
             patch.object(m, "fun_math_start_question") as start, \
             patch.object(m, "fun_math_submit_answer") as answer:
            for raw in (b"{invalid", b"[]", b"null", b"true", b'"text"', b"42"):
                for endpoint in (m.vue_fun_math_start_api, m.vue_fun_math_answer_api):
                    with self.subTest(raw=raw, endpoint=endpoint.__name__), self.assertRaises(HTTPException) as error:
                        asyncio.run(endpoint(math_request(raw=raw), self.db))
                    self.assertEqual(error.exception.status_code, 400)
            start.assert_not_called()
            answer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
