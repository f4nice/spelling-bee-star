import os
import unittest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.database import Base
from app.main import (
    CAT_WORLD_INTERACTION_DURATION_CATALOG,
    CAT_WORLD_INTERACTION_DURATION_MAX_MS,
    CAT_WORLD_INTERACTION_DURATION_MIN_MS,
    cat_world_clamp_interaction_duration,
    cat_world_game_settings_payload,
    cat_world_interaction_duration_payload,
    save_cat_world_interaction_durations,
)
from app.models import CatWorldGameSetting


class CatWorldInteractionSettingsTest(unittest.TestCase):
    def test_catalog_defaults_are_available_to_admin_and_game(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            interaction_payload = cat_world_interaction_duration_payload(db)
            game_settings = cat_world_game_settings_payload(db)

        engine.dispose()
        self.assertEqual(len(interaction_payload["items"]), len(CAT_WORLD_INTERACTION_DURATION_CATALOG))
        self.assertEqual(interaction_payload["byItemId"]["study-desk"], 9000)
        self.assertEqual(interaction_payload["byItemId"]["bubble-bathtub"], 12000)
        self.assertEqual(game_settings["interactionDurations"], interaction_payload["byItemId"])
        self.assertEqual(game_settings["limits"]["interactionDurationMs"]["min"], 3000)

    def test_saved_durations_are_allowlisted_and_clamped(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            save_cat_world_interaction_durations(
                db,
                {
                    "study-desk": 16000,
                    "bubble-bathtub": 100,
                    "sea-window": 999999,
                    "unknown-item": 5000,
                },
            )
            db.commit()
            payload = cat_world_interaction_duration_payload(db)
            rows = db.scalars(select(CatWorldGameSetting)).all()

        engine.dispose()
        self.assertEqual(payload["byItemId"]["study-desk"], 16000)
        self.assertEqual(payload["byItemId"]["bubble-bathtub"], CAT_WORLD_INTERACTION_DURATION_MIN_MS)
        self.assertEqual(payload["byItemId"]["sea-window"], CAT_WORLD_INTERACTION_DURATION_MAX_MS)
        self.assertEqual(len(rows), 3)

    def test_invalid_duration_falls_back_without_breaking_limits(self):
        self.assertEqual(cat_world_clamp_interaction_duration("bad", 8500), 8500)
        self.assertEqual(cat_world_clamp_interaction_duration(float("inf"), 8500), 8500)
        self.assertEqual(cat_world_clamp_interaction_duration(-1, 8500), CAT_WORLD_INTERACTION_DURATION_MIN_MS)


if __name__ == "__main__":
    unittest.main()
