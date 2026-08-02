import os
import unittest
from datetime import datetime, timedelta


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.main import (
    CAT_WORLD_DEFAULT_SCENE_KEY,
    cat_world_clean_litter_for_scene,
    cat_world_litter_scenes,
    cat_world_refresh_litter,
    encode_cat_world_litter_scenes,
)
from app.models import CatWorldState


class CatWorldLitterLocationTest(unittest.TestCase):
    def make_state(self, **overrides):
        values = {
            "phone": "13700000000",
            "current_scene_key": "yard",
            "litter_count": 0,
            "litter_ready_count": 0,
            "litter_scenes": "{}",
        }
        values.update(overrides)
        return CatWorldState(**values)

    def test_legacy_litter_stays_in_main_room_and_empty_yard_is_clean(self):
        now = datetime(2026, 8, 2, 12, 0, 0)
        state = self.make_state(
            litter_scenes=None,
            litter_count=3,
            litter_updated_at=now - timedelta(hours=2),
            litter_started_at=now - timedelta(hours=2),
        )

        status = cat_world_refresh_litter(
            state,
            {},
            [CAT_WORLD_DEFAULT_SCENE_KEY],
            now,
        )

        self.assertEqual(status["count"], 0)
        self.assertFalse(status["hasLitter"])
        self.assertEqual(cat_world_litter_scenes(state)[CAT_WORLD_DEFAULT_SCENE_KEY]["count"], 3)

    def test_litter_is_generated_only_where_a_cat_lives(self):
        now = datetime(2026, 8, 2, 12, 0, 0)
        state = self.make_state(
            litter_scenes=encode_cat_world_litter_scenes(
                {
                    "yard": {
                        "count": 0,
                        "catCount": 1,
                        "updatedAt": (now - timedelta(hours=9)).isoformat() + "Z",
                    }
                }
            )
        )

        status = cat_world_refresh_litter(state, {}, ["yard"], now)

        self.assertEqual(status["count"], 1)
        self.assertEqual(status["addedCount"], 1)
        self.assertNotIn(CAT_WORLD_DEFAULT_SCENE_KEY, cat_world_litter_scenes(state))

    def test_scene_without_cats_does_not_accrue_litter(self):
        now = datetime(2026, 8, 2, 12, 0, 0)
        state = self.make_state(
            litter_scenes=encode_cat_world_litter_scenes(
                {
                    "yard": {
                        "count": 0,
                        "catCount": 1,
                        "updatedAt": (now - timedelta(days=2)).isoformat() + "Z",
                    }
                }
            )
        )

        status = cat_world_refresh_litter(state, {}, [], now)

        self.assertEqual(status["count"], 0)
        self.assertEqual(status["addedCount"], 0)
        self.assertEqual(cat_world_litter_scenes(state)["yard"]["catCount"], 0)

    def test_cleaning_current_scene_keeps_other_scene_litter(self):
        state = self.make_state(
            litter_scenes=encode_cat_world_litter_scenes(
                {
                    CAT_WORLD_DEFAULT_SCENE_KEY: {"count": 2},
                    "yard": {"count": 1},
                }
            )
        )

        remaining = cat_world_clean_litter_for_scene(state, "yard")
        scenes = cat_world_litter_scenes(state)

        self.assertEqual(remaining, 0)
        self.assertEqual(scenes["yard"]["count"], 0)
        self.assertEqual(scenes[CAT_WORLD_DEFAULT_SCENE_KEY]["count"], 2)


if __name__ == "__main__":
    unittest.main()
