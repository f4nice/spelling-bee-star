import asyncio
import os
import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from starlette.requests import Request

from app import main as m
from app.database import Base
from app.models import (
    CatWorldBlindBoxDraw,
    CatWorldFestivalEarning,
    CatWorldLimitedItemStock,
    CatWorldState,
    WordList,
    Word,
    WordListItem,
    ChallengeProgress,
)
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
            ("halloween-2026", "2026-10-30T15:59:59", "2026-10-30T16:00:00", "2026-11-02T15:59:59", "2026-11-02T16:00:00"),
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
        partial = f.festival_energy_source(self.db, "13900000000", utc("2026-09-25T15:59:59"))
        self.assertEqual(partial["todayEnergy"], 1200)
        self.assertEqual(partial["campaign"]["dailyCap"], 1500)
        self.assertEqual(partial["campaign"]["remainingBonus"], 300)
        self.assertIn("1500", partial["campaign"]["rule"])
        self.assertTrue(self.earn(950, "more-learning"))
        self.assertTrue(self.earn(50, "round-1", "2026-09-25T16:00:00", source="challenge_round"))
        self.assertTrue(self.earn(100, "other", phone="13900000001"))
        self.assertFalse(self.earn(1000, "grant", source="operating"))
        self.assertFalse(self.earn(1000, "habit", source="habit"))
        self.assertFalse(self.earn(100, "anonymous", phone=""))
        self.assertFalse(self.earn(0, "no-improvement", source="essay"))
        self.db.commit()
        day_one = f.festival_energy_source(self.db, "13900000000", utc("2026-09-25T15:59:59"))
        self.assertEqual(day_one["energy"], 1500)
        self.assertEqual(day_one["campaign"]["remainingBonus"], 0)
        day_two = f.festival_energy_source(self.db, "13900000000", utc("2026-09-25T16:00:00"))
        self.assertEqual(day_two["todayEnergy"], 100)
        ended = f.festival_energy_source(self.db, "13900000000", utc("2026-10-08T00:00:00"))
        self.assertEqual(ended["energy"], 1600)
        self.assertEqual(ended["todayEnergy"], 0)
        self.assertTrue(ended["campaign"]["visible"])

    def test_weekend_and_festival_multipliers_use_beijing_day_and_do_not_retroactively_change_rows(self):
        self.assertEqual(f.reward_multiplier(date(2026, 10, 23)), 1)
        self.assertEqual(f.reward_multiplier(date(2026, 10, 24)), 2)
        self.assertEqual(f.reward_multiplier(date(2026, 10, 25)), 2)
        self.assertEqual(f.reward_multiplier(date(2026, 10, 31)), 3)
        self.assertEqual(f.reward_multiplier(date(2026, 11, 2)), 3)
        self.assertEqual(f.reward_multiplier(date(2026, 11, 3)), 1)

        self.assertFalse(self.earn(10, "weekday", "2026-10-23T12:00:00"))
        self.assertTrue(self.earn(10, "weekend", "2026-10-24T12:00:00"))
        self.assertTrue(self.earn(10, "halloween", "2026-10-31T12:00:00"))
        rows = self.db.scalars(select(CatWorldFestivalEarning)).all()
        self.assertEqual(sorted(row.base_energy for row in rows), [10, 20])
        source = f.festival_energy_source(self.db, "13900000000", utc("2026-10-31T12:00:00"))
        self.assertEqual(source["todayEnergy"], 20)
        self.assertEqual(source["campaign"]["todayMultiplier"], 3)

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
            self.assertEqual(f.festival_energy_source(self.db, "13900000000")["energy"], 104)
            m.challenge_state(self.db, word_list)
            self.assertEqual(f.festival_energy_source(self.db, "13900000000")["energy"], 104)

    def purchase(self, series_key, now):
        return self.purchase_item(f"{series_key}-blind-box", now)

    def purchase_item(self, item_id, now):
        import json
        body = json.dumps({"itemId": item_id}).encode()
        async def receive():
            return {"type": "http.request", "body": body}
        request = Request({"type": "http", "headers": []}, receive=receive)
        event_loop_policy = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
        previous_policy = asyncio.get_event_loop_policy()
        if event_loop_policy is not None:
            asyncio.set_event_loop_policy(event_loop_policy())
        try:
            with patch.object(m, "require_cat_world_phone", return_value="13900000000"), \
             patch.object(f, "festival_now", return_value=f.festival_now(utc(now))), \
             patch.object(m, "serialize_cat_world_payload", return_value={"energy": {"earned": 10000, "available": 10000}}):
                return asyncio.run(m.vue_cat_world_purchase_api(request, self.db))
        finally:
            if event_loop_policy is not None:
                asyncio.set_event_loop_policy(previous_policy)

    def test_purchase_is_time_gated_costs_once_and_both_festivals_are_independent(self):
        m.seed_cat_world_scenes(self.db)
        m.seed_cat_world_limited_cat_stock(self.db)
        state = CatWorldState(phone="13900000000", energy_spent=0, cats='["mimi"]')
        self.db.add(state)
        self.db.commit()
        for series_key, before, active, after in (
            ("mid-autumn-2026", "2026-09-24T15:59:59", "2026-09-24T16:00:00", "2026-09-27T16:00:00"),
            ("national-day-2026", "2026-09-30T15:59:59", "2026-09-30T16:00:00", "2026-10-07T16:00:00"),
            ("halloween-2026", "2026-10-30T15:59:59", "2026-10-30T16:00:00", "2026-11-02T16:00:00"),
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
        self.assertEqual(len(self.db.scalars(select(CatWorldBlindBoxDraw)).all()), 3)
        catalog = m.cat_world_blind_box_catalog_payload(self.db, state, m.parse_cat_world_cats(state.cats))
        seasonal = [s for s in catalog["series"] if s["timeLimited"]]
        self.assertEqual(len(seasonal), 3)
        for series in seasonal:
            self.assertTrue(series["drawn"])
            self.assertEqual([cat["oddsPercent"] for cat in series["cats"]], [50, 50])

    def test_halloween_items_are_time_limited_and_seeded(self):
        m.seed_cat_world_limited_item_stock(self.db)
        for item_id in ("halloween-pumpkin-lantern", "halloween-ghost-plush", "halloween-candy-bowl"):
            item = m.CAT_WORLD_SHOP_BY_ID[item_id]
            self.assertEqual(item["festivalId"], "halloween-2026")
            self.assertTrue(item["limited"])
            self.assertEqual(item["maxOwned"], 1)
            stock = self.db.scalar(select(CatWorldLimitedItemStock).where(CatWorldLimitedItemStock.item_id == item_id))
            self.assertIsNotNone(stock)
            self.assertEqual(stock.total_stock, 500)

    def test_halloween_goods_charge_once_and_preserve_existing_state_and_stock(self):
        m.seed_cat_world_scenes(self.db)
        m.seed_cat_world_limited_item_stock(self.db)
        old_stock = self.db.scalar(select(CatWorldLimitedItemStock).where(
            CatWorldLimitedItemStock.item_id == m.CAT_WORLD_LIMITED_GIFT_ITEM_ID))
        old_stock.total_stock = 27
        old_stock.claimed_count = 3
        old_stock.is_active = False
        state = CatWorldState(phone="13900000000", energy_spent=75, cats='["mimi"]',
                              inventory='{"rolling-ball":1,"daily-kibble":4}')
        self.db.add(state)
        self.db.commit()
        m.seed_cat_world_limited_item_stock(self.db)
        self.assertEqual((old_stock.total_stock, old_stock.claimed_count, old_stock.is_active), (27, 3, False))
        for item_id in m.CAT_WORLD_HALLOWEEN_ITEM_STOCK:
            before_spent = state.energy_spent
            stock = self.db.scalar(select(CatWorldLimitedItemStock).where(
                CatWorldLimitedItemStock.item_id == item_id))
            with self.assertRaises(HTTPException) as denied:
                self.purchase_item(item_id, "2026-10-30T15:59:59")
            self.assertEqual(denied.exception.status_code, 409)
            self.assertEqual((state.energy_spent, stock.claimed_count), (before_spent, 0))
            self.purchase_item(item_id, "2026-10-30T16:00:00")
            expected_spent = before_spent + m.CAT_WORLD_SHOP_BY_ID[item_id]["cost"]
            self.assertEqual((state.energy_spent, stock.claimed_count), (expected_spent, 1))
            self.purchase_item(item_id, "2026-10-31T12:00:00")
            self.assertEqual((state.energy_spent, stock.claimed_count), (expected_spent, 1))
            with self.assertRaises(HTTPException):
                self.purchase_item(item_id, "2026-11-02T16:00:00")
            inventory = m.parse_cat_world_inventory(state.inventory)
            self.assertEqual(inventory[item_id], 1)
            self.assertEqual(inventory["rolling-ball"], 1)
            self.assertEqual(inventory["daily-kibble"], 4)
            self.assertEqual(m.parse_cat_world_cats(state.cats), ["mimi"])

    def test_weekend_remaining_bonus_and_cross_month_campaign_label(self):
        self.earn(600, "weekend-cap", "2026-10-24T12:00:00")
        campaign = f.festival_energy_source(self.db, "13900000000", utc("2026-10-24T12:00:00"))["campaign"]
        self.assertEqual(campaign["todayMultiplier"], 2)
        self.assertEqual(campaign["remainingBonus"], 900)
        self.assertIn("10月31–11月2日", campaign["dateLabel"])

    def test_admin_can_manage_limited_decor_stock_without_resetting_claims(self):
        import json
        m.seed_cat_world_limited_item_stock(self.db)
        item_id = "halloween-pumpkin-lantern"
        stock = self.db.scalar(select(CatWorldLimitedItemStock).where(
            CatWorldLimitedItemStock.item_id == item_id))
        stock.claimed_count = 2
        self.db.commit()
        async def receive():
            return {"type": "http.request", "body": json.dumps({
                "itemId": item_id, "totalStock": 600, "isActive": True}).encode()}
        request = Request({"type": "http", "headers": []}, receive=receive)
        with patch.object(m, "require_admin_panel_access"), patch.object(m, "admin_cat_world_pricing_payload", return_value={}):
            result = asyncio.run(m.vue_admin_cat_world_limited_item_stock_api(request, self.db))
        self.assertTrue(result["ok"])
        self.assertEqual((stock.total_stock, stock.claimed_count), (600, 2))


if __name__ == "__main__":
    unittest.main()
