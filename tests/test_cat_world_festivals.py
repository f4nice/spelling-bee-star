import asyncio
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app import main as m
from app.database import Base
from app.models import CatWorldBlindBoxDraw, CatWorldFestivalEarning, CatWorldState, WordList, Word, WordListItem, ChallengeProgress
from app.services import cat_world_festivals as f


def utc(value):
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


class FestivalTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)

    def earn(self, amount, key, when="2026-09-24T16:00:00", phone="13900000000", source="spelling"):
        return f.record_festival_earning(self.db, phone=phone, source=source,
                                        event_key=key, base_energy=amount, now=utc(when))

    def test_beijing_boundaries_and_gap_for_both_campaigns(self):
        for key, before, opening, last, end in (
            ("mid-autumn-2026", "2026-09-24T15:59:59", "2026-09-24T16:00:00", "2026-09-27T15:59:59", "2026-09-27T16:00:00"),
            ("national-day-2026", "2026-09-30T15:59:59", "2026-09-30T16:00:00", "2026-10-07T15:59:59", "2026-10-07T16:00:00"),
        ):
            for instant, status in ((before, "upcoming"), (opening, "active"), (last, "active"), (end, "ended")):
                with self.subTest(key=key, instant=instant):
                    self.assertEqual(f.festival_sale_window(key, utc(instant))["saleState"], status)
            self.assertFalse(self.earn(10, key + "before", before))
            self.assertTrue(self.earn(10, key + "open", opening))
            self.assertTrue(self.earn(10, key + "last", last))
            self.assertFalse(self.earn(10, key + "end", end))

    def test_daily_cap_replay_account_isolation_and_rewards_survive_end(self):
        self.assertTrue(self.earn(380, "essay-best-380", source="essay"))
        self.assertFalse(self.earn(380, "essay-best-380", source="essay"))
        self.assertTrue(self.earn(220, "debate-1", source="debate"))
        self.assertTrue(self.earn(50, "round-1", "2026-09-25T16:00:00", source="challenge_round"))
        self.assertTrue(self.earn(100, "other", phone="13900000001"))
        self.assertFalse(self.earn(1000, "grant", source="operating"))
        self.assertFalse(self.earn(1000, "habit", source="habit"))
        self.assertFalse(self.earn(100, "anonymous", phone=""))
        self.assertFalse(self.earn(0, "no-improvement", source="essay"))
        self.db.commit()
        day_one = f.festival_energy_source(self.db, "13900000000", utc("2026-09-25T15:59:59"))
        self.assertEqual(day_one["energy"], 500)
        self.assertEqual(day_one["campaign"]["remainingBonus"], 0)
        day_two = f.festival_energy_source(self.db, "13900000000", utc("2026-09-25T16:00:00"))
        self.assertEqual(day_two["todayEnergy"], 50)
        ended = f.festival_energy_source(self.db, "13900000000", utc("2026-10-08T00:00:00"))
        self.assertEqual(ended["energy"], 550)
        self.assertEqual(ended["todayEnergy"], 0)
        self.assertFalse(ended["campaign"]["visible"])

    def test_reward_rolls_back_with_learning_write(self):
        self.db.add(Word(word="rollback"))
        self.earn(2, "rolled-back")
        self.db.rollback()
        self.assertEqual(self.db.scalars(select(CatWorldFestivalEarning)).all(), [])
        self.assertEqual(self.db.scalars(select(Word)).all(), [])

    def test_spelling_and_completed_round_award_only_new_learning(self):
        word_list = WordList(name="Festival test")
        word = Word(word="moon")
        self.db.add_all([word_list, word])
        self.db.flush()
        self.db.add(WordListItem(word_list_id=word_list.id, word_id=word.id))
        self.db.add(ChallengeProgress(word_list_id=word_list.id, current_index=0, completed_count=0, completed_rounds=0))
        self.db.commit()
        with patch.object(f, "festival_now", return_value=f.festival_now(utc("2026-09-25T00:00:00"))):
            answer = m.apply_challenge_answer(self.db, word_list_id=word_list.id, action="spell",
                daily_count=1, start_count=0, session_correct=0, session_wrong=0,
                spelling="moon", answer_word_id=word.id, wrong_date="", reward_phone="13900000000")
            m.challenge_payload(self.db, word_list_id=word_list.id, daily_count=1, start_count=0,
                session_correct=answer["session_correct"], session_wrong=0, wrong_date=None,
                preloaded_current_word=answer["next_word"], reward_phone="13900000000")
            self.assertEqual(f.festival_energy_source(self.db, "13900000000")["energy"], 52)
            m.challenge_state(self.db, word_list)
            self.assertEqual(f.festival_energy_source(self.db, "13900000000")["energy"], 52)

    def purchase(self, series_key, now):
        import json
        body = json.dumps({"itemId": f"{series_key}-blind-box"}).encode()
        async def receive():
            return {"type": "http.request", "body": body}
        request = Request({"type": "http", "headers": []}, receive=receive)
        with patch.object(m, "require_cat_world_phone", return_value="13900000000"), \
             patch.object(f, "festival_now", return_value=f.festival_now(utc(now))), \
             patch.object(m, "serialize_cat_world_payload", return_value={"energy": {"earned": 10000, "available": 10000}}):
            return asyncio.run(m.vue_cat_world_purchase_api(request, self.db))

    def test_purchase_is_time_gated_costs_once_and_both_festivals_are_independent(self):
        m.seed_cat_world_scenes(self.db)
        m.seed_cat_world_limited_cat_stock(self.db)
        state = CatWorldState(phone="13900000000", energy_spent=0, cats='["mimi"]')
        self.db.add(state)
        self.db.commit()
        for series_key, before, active, after in (
            ("mid-autumn-2026", "2026-09-24T15:59:59", "2026-09-24T16:00:00", "2026-09-27T16:00:00"),
            ("national-day-2026", "2026-09-30T15:59:59", "2026-09-30T16:00:00", "2026-10-07T16:00:00"),
        ):
            spent = state.energy_spent
            with self.assertRaises(HTTPException) as denied:
                self.purchase(series_key, before)
            self.assertEqual(denied.exception.status_code, 409)
            self.assertEqual(state.energy_spent, spent)
            result = self.purchase(series_key, active)
            cat_id = result["blindBoxResult"]["cat"]["id"]
            self.assertEqual(state.energy_spent, spent + 1500)
            self.assertIn(cat_id, m.parse_cat_world_cats(state.cats))
            with self.assertRaises(HTTPException) as duplicate:
                self.purchase(series_key, active)
            self.assertEqual(duplicate.exception.status_code, 409)
            with self.assertRaises(HTTPException):
                self.purchase(series_key, after)
            self.assertEqual(state.energy_spent, spent + 1500)
            self.assertIn(cat_id, m.parse_cat_world_cats(state.cats))
        self.assertEqual(len(self.db.scalars(select(CatWorldBlindBoxDraw)).all()), 2)
        catalog = m.cat_world_blind_box_catalog_payload(self.db, state, m.parse_cat_world_cats(state.cats))
        seasonal = [s for s in catalog["series"] if s["timeLimited"]]
        self.assertEqual(len(seasonal), 2)
        for series in seasonal:
            self.assertTrue(series["drawn"])
            self.assertEqual([cat["oddsPercent"] for cat in series["cats"]], [50, 50])


if __name__ == "__main__":
    unittest.main()
