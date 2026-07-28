import os
import unittest
from datetime import date, datetime


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.main import (
    CAT_WORLD_CAT_BY_ID,
    CAT_WORLD_DEFAULT_CAT_ID,
    apply_cat_world_hourly_decay,
    cat_world_behavior_hourly_change,
    cat_world_cat_payload,
    cat_world_cat_traits,
    cat_world_current_behavior,
    cat_world_default_agent_state,
    encode_cat_world_agent_state,
)
from app.models import CatWorldDailyLog


class CatWorldSleepRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.phone = "13900000000"
        self.cat = cat_world_cat_payload(CAT_WORLD_CAT_BY_ID[CAT_WORLD_DEFAULT_CAT_ID])
        self.traits = {
            **cat_world_cat_traits(self.cat),
            "sleepStart": 23,
            "sleepEnd": 7,
            "nightOwl": False,
        }
        self.log_date = date(2026, 7, 28)
        self.log = CatWorldDailyLog(
            phone=self.phone,
            log_date=self.log_date,
            cat_id=self.cat["id"],
            mood_score=34,
            energy_score=30,
            last_decay_at=datetime(2026, 7, 27, 14, 0),
        )
        agent_state = cat_world_default_agent_state(
            self.log_date,
            self.cat,
            self.traits,
            self.phone,
        )
        agent_state.update(
            {
                "dailyMoodKey": "grumpy",
                "dailyMoodLabel": "今天不太高兴",
                "moodOffset": -10,
                "energyOffset": -3,
            }
        )
        self.log.agent_state = encode_cat_world_agent_state(agent_state)

    def test_sleep_recovers_mood_even_with_hygiene_penalties(self):
        change = cat_world_behavior_hourly_change(
            self.log,
            self.traits,
            {},
            0,
            datetime(2026, 7, 27, 18, 0),
            litter_count=4,
            bath_mood_penalty=3,
            cat=self.cat,
        )

        self.assertEqual(change["label"], "睡觉恢复")
        self.assertTrue(change["behavior"]["sleeping"])
        self.assertGreaterEqual(change["moodDelta"], 2)
        self.assertEqual(change["litterPenalty"], 1)
        self.assertEqual(change["bathPenalty"], 1)

    def test_waking_adds_calm_recovery_before_behavior_is_rechecked(self):
        wake_at = datetime(2026, 7, 27, 23, 0)
        change = cat_world_behavior_hourly_change(
            self.log,
            self.traits,
            {},
            0,
            wake_at,
            litter_count=4,
            bath_mood_penalty=3,
            cat=self.cat,
        )

        self.assertEqual(change["label"], "睡醒舒展")
        self.assertFalse(change["behavior"]["sleeping"])
        self.assertGreaterEqual(change["moodDelta"], 4)

        changed = apply_cat_world_hourly_decay(
            self.log,
            self.traits,
            {},
            0,
            wake_at,
            litter_count=4,
            bath_mood_penalty=3,
            cat=self.cat,
        )
        self.assertTrue(changed)
        adjusted_mood = self.log.mood_score - 10
        behavior = cat_world_current_behavior(
            {
                "dailyMoodKey": "grumpy",
                "activityBias": 50,
                "socialNeed": 50,
            },
            self.traits,
            adjusted_mood,
            self.log.energy_score - 3,
            wake_at,
        )
        self.assertGreaterEqual(adjusted_mood, 38)
        self.assertNotEqual(behavior["key"], "sulking")


if __name__ == "__main__":
    unittest.main()
