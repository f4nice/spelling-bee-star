import os
import unittest
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.database import Base
from app.main import (
    cat_world_play_time_earned_seconds,
    cat_world_play_time_payload,
    cat_world_play_time_reward_source,
    cat_world_update_play_time_session,
)
from app.models import CatWorldPlayTimeGrant, CatWorldState


class CatWorldPlayTimeTest(unittest.TestCase):
    def test_daily_spelling_unlocks_gradual_play_time_tiers(self):
        self.assertEqual(cat_world_play_time_earned_seconds(19), 0)
        self.assertEqual(cat_world_play_time_earned_seconds(20), 180)
        self.assertEqual(cat_world_play_time_earned_seconds(49), 180)
        self.assertEqual(cat_world_play_time_earned_seconds(50), 360)
        self.assertEqual(cat_world_play_time_earned_seconds(99), 360)
        self.assertEqual(cat_world_play_time_earned_seconds(100), 720)
        self.assertEqual(cat_world_play_time_earned_seconds(199), 720)
        self.assertEqual(cat_world_play_time_earned_seconds(200), 1200)

    def test_reward_time_stacks_on_top_of_spelling_time(self):
        today = date(2026, 7, 30)
        state = CatWorldState(
            phone="13900000000",
            play_time_date=today,
            play_time_used_seconds=120,
        )

        payload = cat_world_play_time_payload(
            state,
            100,
            reward_seconds=15 * 60,
            today=today,
        )

        self.assertEqual(payload["baseEarnedSeconds"], 720)
        self.assertEqual(payload["rewardMinutes"], 15)
        self.assertEqual(payload["earnedSeconds"], 1620)
        self.assertEqual(payload["remainingSeconds"], 1500)

    def test_reward_time_source_only_sums_the_requested_day(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        today = date(2026, 7, 30)
        with Session(engine) as db:
            db.add_all(
                [
                    CatWorldPlayTimeGrant(
                        phone="13900000000",
                        reward_date=today,
                        minutes=10,
                        reason="阅读奖励",
                        granted_by_phone="13900000000",
                    ),
                    CatWorldPlayTimeGrant(
                        phone="13900000000",
                        reward_date=today,
                        minutes=5,
                        reason="拼写加油",
                        granted_by_phone="13900000000",
                    ),
                    CatWorldPlayTimeGrant(
                        phone="13900000000",
                        reward_date=today - timedelta(days=1),
                        minutes=30,
                        reason="昨日奖励",
                        granted_by_phone="13900000000",
                    ),
                ]
            )
            db.commit()

            source = cat_world_play_time_reward_source(db, "13900000000", today)

        self.assertEqual(source["minutes"], 15)
        self.assertEqual(source["seconds"], 900)
        self.assertEqual(source["grantCount"], 2)

    def test_heartbeat_consumes_only_a_live_session(self):
        today = date(2026, 7, 30)
        started_at = datetime(2026, 7, 30, 8, 0, 0)
        state = CatWorldState(
            phone="13900000000",
            play_time_date=today,
            play_time_used_seconds=120,
            play_time_last_seen_at=started_at,
        )

        payload = cat_world_update_play_time_session(
            state,
            100,
            active=True,
            now=started_at + timedelta(seconds=10),
            today=today,
        )

        self.assertEqual(state.play_time_used_seconds, 130)
        self.assertEqual(payload["remainingSeconds"], 590)
        self.assertTrue(payload["sessionActive"])

    def test_stale_session_is_not_charged(self):
        today = date(2026, 7, 30)
        now = datetime(2026, 7, 30, 8, 0, 0)
        state = CatWorldState(
            phone="13900000000",
            play_time_date=today,
            play_time_used_seconds=120,
            play_time_last_seen_at=now - timedelta(minutes=2),
        )

        payload = cat_world_update_play_time_session(
            state,
            100,
            active=True,
            now=now,
            today=today,
        )

        self.assertEqual(state.play_time_used_seconds, 120)
        self.assertEqual(payload["remainingSeconds"], 600)

    def test_new_day_resets_usage(self):
        old_day = date(2026, 7, 29)
        today = date(2026, 7, 30)
        now = datetime(2026, 7, 30, 8, 0, 0)
        state = CatWorldState(
            phone="13900000000",
            play_time_date=old_day,
            play_time_used_seconds=590,
            play_time_last_seen_at=now - timedelta(hours=1),
        )

        payload = cat_world_play_time_payload(state, 200, now=now, today=today)

        self.assertEqual(state.play_time_used_seconds, 0)
        self.assertEqual(payload["remainingSeconds"], 1200)
        self.assertFalse(payload["sessionActive"])


if __name__ == "__main__":
    unittest.main()
