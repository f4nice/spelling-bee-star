import os
import unittest
from datetime import date, datetime, timedelta


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.main import (
    cat_world_play_time_earned_seconds,
    cat_world_play_time_payload,
    cat_world_update_play_time_session,
)
from app.models import CatWorldState


class CatWorldPlayTimeTest(unittest.TestCase):
    def test_daily_spelling_unlocks_ten_and_twenty_minute_tiers(self):
        self.assertEqual(cat_world_play_time_earned_seconds(99), 0)
        self.assertEqual(cat_world_play_time_earned_seconds(100), 600)
        self.assertEqual(cat_world_play_time_earned_seconds(199), 600)
        self.assertEqual(cat_world_play_time_earned_seconds(200), 1200)

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
        self.assertEqual(payload["remainingSeconds"], 470)
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
        self.assertEqual(payload["remainingSeconds"], 480)

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
