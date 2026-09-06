import asyncio
import os
import unittest
from datetime import date
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.database import Base
from app import main as m
from app.models import CatWorldDailyLog, CatWorldState


class JsonRequest:
    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        return self.payload


class CatWorldAgentEventTest(unittest.TestCase):
    def test_favorite_toy_event_rewards_the_individual_cat_profile(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            phone = "13900000021"
            state = CatWorldState(
                phone=phone,
                cats=m.encode_cat_world_cats(["siamese"]),
                selected_cat="siamese",
                inventory=m.encode_cat_world_inventory({"rolling-ball": 1}),
                room_layout=m.encode_cat_world_room_layout({}),
                item_locations=m.encode_cat_world_item_locations({"rolling-ball": "main-room"}),
                current_scene_key="main-room",
                cat_bonds=m.encode_cat_world_bonds({}),
                cat_care=m.encode_cat_world_care({}),
                litter_scenes=m.encode_cat_world_litter_scenes({}),
            )
            db.add(state)
            db.flush()
            profile = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            state.selected_cat_profile = profile.profile_id
            db.flush()

            request = JsonRequest(
                {
                    "catId": profile.profile_id,
                    "itemId": "rolling-ball",
                    "kind": "favorite-toy",
                }
            )
            with (
                patch.object(m, "require_cat_world_phone", return_value=phone),
                patch.object(m, "get_or_create_cat_world_state", return_value=state),
                patch.object(m, "cat_world_active_scene_layout", return_value={}),
                patch.object(m, "serialize_cat_world_payload", return_value={"testPayload": True}),
            ):
                result = asyncio.run(m.vue_cat_world_agent_event_api(request, db))

            self.assertTrue(result["recorded"])
            self.assertEqual(result["effect"]["catId"], profile.profile_id)
            self.assertEqual(result["effect"]["kind"], "favorite-toy")
            self.assertGreaterEqual(result["effect"]["moodGain"], 1)
            self.assertEqual(result["effect"]["bond"]["catId"], profile.profile_id)

            log = db.scalar(
                select(CatWorldDailyLog).where(
                    CatWorldDailyLog.phone == phone,
                    CatWorldDailyLog.log_date == date.today(),
                    CatWorldDailyLog.cat_id == profile.profile_id,
                )
            )
            self.assertIsNotNone(log)
            agent_state = m.parse_cat_world_agent_state(log.agent_state)
            self.assertEqual(agent_state["ambientEffectCount"], 1)
            self.assertIn("favorite-toy:rolling-ball", agent_state["ambientEventAt"])
            self.assertEqual(agent_state["events"][-1]["kind"], "favorite-toy")


if __name__ == "__main__":
    unittest.main()
