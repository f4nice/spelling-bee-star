import os
import unittest
from datetime import date, datetime


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.main import (
    CAT_WORLD_CAT_BY_ID,
    CAT_WORLD_DEFAULT_CAT_ID,
    apply_cat_world_hourly_decay,
    cat_world_agent_payload,
    cat_world_behavior_allows_mischief,
    cat_world_behavior_hourly_change,
    cat_world_cat_payload,
    cat_world_cat_traits,
    cat_world_current_behavior,
    cat_world_default_agent_state,
    cat_world_wake_recovery_minutes,
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

    def test_wake_recovery_lasts_two_hours_then_returns_to_normal_behavior(self):
        first_hour = datetime(2026, 7, 27, 23, 30)
        second_hour = datetime(2026, 7, 28, 0, 30)
        after_recovery = datetime(2026, 7, 28, 1, 0)

        self.assertEqual(cat_world_wake_recovery_minutes(first_hour, self.traits), 90)
        self.assertEqual(cat_world_wake_recovery_minutes(second_hour, self.traits), 30)
        self.assertEqual(cat_world_wake_recovery_minutes(after_recovery, self.traits), 0)

        change = cat_world_behavior_hourly_change(
            self.log,
            self.traits,
            {},
            0,
            second_hour,
            litter_count=4,
            bath_mood_penalty=3,
            cat=self.cat,
        )
        self.assertEqual(change["behavior"]["key"], "waking")
        self.assertEqual(change["label"], "睡醒缓冲")
        self.assertGreaterEqual(change["moodDelta"], 1)

        behavior = cat_world_current_behavior(
            {"dailyMoodKey": "grumpy", "activityBias": 50, "socialNeed": 50},
            self.traits,
            24,
            80,
            after_recovery,
        )
        self.assertEqual(behavior["key"], "sulking")

    def test_waking_payload_is_calm_and_defers_mischief(self):
        wake_at = datetime(2026, 7, 27, 23, 30)
        self.log.energy_score = 70
        payload = cat_world_agent_payload(
            self.log,
            self.cat,
            self.traits,
            inventory={"reading-lamp": 1},
            room_layout={"reading-lamp": {"x": 30, "y": 30}},
            now=wake_at,
        )

        self.assertEqual(payload["currentBehavior"]["key"], "waking")
        self.assertEqual(payload["dailyGoal"]["key"], "wake-recovery")
        self.assertEqual(payload["dailyGoal"]["damageRisk"], 0.0)
        self.assertEqual(payload["careNeed"]["key"], "wake-recovery")
        self.assertEqual(payload["careNeed"]["status"], "calm")
        self.assertIn("不会立刻闹情绪或捣蛋", payload["careTip"])
        self.assertFalse(cat_world_behavior_allows_mischief(payload["currentBehavior"]))


if __name__ == "__main__":
    unittest.main()
