import asyncio
import os
import unittest
from datetime import date, datetime, timedelta
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
    def create_social_pair(self, db, phone="13900000022"):
        state = CatWorldState(
            phone=phone,
            cats=m.encode_cat_world_cats(["mimi", "siamese"]),
            selected_cat="mimi",
            inventory=m.encode_cat_world_inventory({}),
            room_layout=m.encode_cat_world_room_layout({}),
            item_locations=m.encode_cat_world_item_locations({}),
            current_scene_key="main-room",
            cat_bonds=m.encode_cat_world_bonds({}),
            cat_care=m.encode_cat_world_care({}),
            litter_scenes=m.encode_cat_world_litter_scenes({}),
        )
        db.add(state)
        db.flush()
        source = m.create_cat_world_cat_profile(db, state, "mimi", "test")
        partner = m.create_cat_world_cat_profile(db, state, "siamese", "test")
        source.current_scene_key = "main-room"
        partner.current_scene_key = "main-room"
        state.selected_cat_profile = source.profile_id
        db.flush()
        return state, source, partner

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
            favorite_toy_id = m.cat_world_cat_profile_payload(profile)["favoriteToyIds"][0]
            state.inventory = m.encode_cat_world_inventory({favorite_toy_id: 1})
            state.item_locations = m.encode_cat_world_item_locations({favorite_toy_id: "main-room"})
            db.flush()

            request = JsonRequest(
                {
                    "catId": profile.profile_id,
                    "itemId": favorite_toy_id,
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
            self.assertIn(f"favorite-toy:{favorite_toy_id}", agent_state["ambientEventAt"])
            self.assertEqual(agent_state["events"][-1]["kind"], "favorite-toy")

    def test_social_event_updates_both_cat_diaries(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            phone = "13900000022"
            state, source, partner = self.create_social_pair(db, phone)
            request = JsonRequest(
                {
                    "catId": source.profile_id,
                    "partnerCatId": partner.profile_id,
                    "kind": "cat-social",
                    "socialKind": "nuzzle",
                }
            )
            with (
                patch.object(m, "require_cat_world_phone", return_value=phone),
                patch.object(m, "get_or_create_cat_world_state", return_value=state),
                patch.object(m, "cat_world_active_scene_layout", return_value={}),
                patch.object(m, "apply_cat_world_hourly_decay"),
                patch.object(
                    m,
                    "cat_world_current_behavior",
                    return_value={"key": "active", "sleeping": False, "waking": False},
                ),
                patch.object(m, "serialize_cat_world_payload", return_value={"testPayload": True}),
            ):
                result = asyncio.run(m.vue_cat_world_agent_event_api(request, db))

            self.assertTrue(result["recorded"])
            self.assertEqual(result["effect"]["kind"], "cat-social")
            self.assertEqual(result["effect"]["socialKind"], "nuzzle")
            self.assertEqual(set(result["effect"]["catIds"]), {source.profile_id, partner.profile_id})
            self.assertEqual(len(result["effect"]["effects"]), 2)
            self.assertTrue(result["testPayload"])

            logs = db.scalars(
                select(CatWorldDailyLog).where(
                    CatWorldDailyLog.phone == phone,
                    CatWorldDailyLog.log_date == date.today(),
                )
            ).all()
            self.assertEqual(len(logs), 2)
            expected_token = f"cat-social:{':'.join(sorted((source.profile_id, partner.profile_id)))}"
            for log in logs:
                agent_state = m.parse_cat_world_agent_state(log.agent_state)
                self.assertEqual(agent_state["ambientEffectCount"], 1)
                self.assertEqual(agent_state["socialEventCount"], 1)
                self.assertIn(expected_token, agent_state["ambientEventAt"])
                self.assertEqual(agent_state["events"][-1]["kind"], "cat-social")

    def test_social_event_has_a_pair_cooldown(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            state, source, partner = self.create_social_pair(db, "13900000023")
            started_at = datetime(2026, 9, 6, 13, 0)
            with (
                patch.object(m, "cat_world_active_scene_layout", return_value={}),
                patch.object(m, "apply_cat_world_hourly_decay"),
                patch.object(
                    m,
                    "cat_world_current_behavior",
                    return_value={"key": "active", "sleeping": False, "waking": False},
                ),
            ):
                first = m.cat_world_apply_social_event(
                    db, state, source, partner.profile_id, "greet", now=started_at
                )
                db.commit()
                second = m.cat_world_apply_social_event(
                    db,
                    state,
                    source,
                    partner.profile_id,
                    "greet",
                    now=started_at + timedelta(minutes=10),
                )

            self.assertTrue(first["recorded"])
            self.assertFalse(second["recorded"])
            self.assertEqual(second["reason"], "cooldown")

    def test_social_event_rejects_cats_in_different_rooms(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            state, source, partner = self.create_social_pair(db, "13900000024")
            partner.current_scene_key = "yard"
            db.flush()

            with self.assertRaises(m.HTTPException) as error:
                m.cat_world_apply_social_event(db, state, source, partner.profile_id, "chase")

            self.assertEqual(error.exception.status_code, 400)
            self.assertIn("同一个房间", error.exception.detail)


if __name__ == "__main__":
    unittest.main()
