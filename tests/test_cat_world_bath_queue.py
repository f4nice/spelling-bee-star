import asyncio
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app import main as m
from app.database import Base
from app.models import CatWorldState


class JsonRequest:
    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        return self.payload


class CatWorldBathQueueTest(unittest.TestCase):
    def make_world(self, db, inventory=None):
        m.seed_cat_world_scenes(db)
        state = CatWorldState(
            phone="13900000123",
            cats=m.encode_cat_world_cats(["siamese"]),
            selected_cat="siamese",
            inventory=m.encode_cat_world_inventory(inventory or {}),
            room_layout=m.encode_cat_world_room_layout({}),
            item_locations=m.encode_cat_world_item_locations({}),
            current_scene_key="main-room",
            cat_bonds=m.encode_cat_world_bonds({}),
            cat_care=m.encode_cat_world_care({}),
            bath_queue=m.encode_cat_world_bath_queue({}),
            litter_scenes=m.encode_cat_world_litter_scenes({}),
        )
        db.add(state)
        db.flush()
        profile = m.create_cat_world_cat_profile(db, state, "siamese", "bath-test")
        profile.current_scene_key = "main-room"
        state.selected_cat_profile = profile.profile_id
        db.flush()
        return state, profile

    def new_db(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.addCleanup(engine.dispose)
        db = Session(engine, expire_on_commit=False)
        self.addCleanup(db.close)
        return db

    def test_queue_then_supply_starts_one_cat_and_reserves_one_kit(self):
        db = self.new_db()
        state, profile = self.make_world(db, {"bubble-bathtub": 1, m.CAT_WORLD_BATH_ITEM_ID: 3})
        with (
            patch.object(m, "require_cat_world_phone", return_value=state.phone),
            patch.object(m, "cat_world_locked_state", return_value=state),
            patch.object(m, "serialize_cat_world_payload", return_value={"state": {}}),
        ):
            queued = asyncio.run(m.vue_cat_world_bath_queue_api(JsonRequest({"catId": profile.profile_id}), db))
            self.assertTrue(queued["ok"])
            self.assertEqual(m.parse_cat_world_bath_queue(state.bath_queue)["queue"][0]["catId"], profile.profile_id)

            supplied = asyncio.run(
                m.vue_cat_world_bath_supply_api(JsonRequest({"quantity": 2}), db)
            )

        self.assertTrue(supplied["ok"])
        self.assertEqual(m.parse_cat_world_inventory(state.inventory)[m.CAT_WORLD_BATH_ITEM_ID], 1)
        bath = m.parse_cat_world_bath_queue(state.bath_queue)
        self.assertEqual(bath["supply"], 1)
        self.assertEqual(bath["active"]["catId"], profile.profile_id)
        self.assertEqual(bath["queue"], [])

    def test_duplicate_queue_and_missing_bathtub_are_rejected(self):
        db = self.new_db()
        state, profile = self.make_world(db, {m.CAT_WORLD_BATH_ITEM_ID: 1})
        with (
            patch.object(m, "require_cat_world_phone", return_value=state.phone),
            patch.object(m, "cat_world_locked_state", return_value=state),
            patch.object(m, "serialize_cat_world_payload", return_value={"state": {}}),
        ):
            asyncio.run(m.vue_cat_world_bath_queue_api(JsonRequest({"catId": profile.profile_id}), db))
            with self.assertRaisesRegex(HTTPException, "已经在洗澡中或排队"):
                asyncio.run(m.vue_cat_world_bath_queue_api(JsonRequest({"catId": profile.profile_id}), db))
            with self.assertRaisesRegex(HTTPException, "先购买泡泡浴缸"):
                asyncio.run(m.vue_cat_world_bath_supply_api(JsonRequest({"quantity": 1}), db))

    def test_expired_active_bath_updates_care_and_starts_next_cat(self):
        db = self.new_db()
        state, first = self.make_world(db, {m.CAT_WORLD_BATH_ITEM_ID: 0})
        second = m.create_cat_world_cat_profile(db, state, "siamese", "bath-test-2")
        second.current_scene_key = "main-room"
        now = datetime.utcnow().replace(microsecond=0)
        state.cat_care = m.encode_cat_world_care({first.profile_id: {"lastBathAt": now.isoformat() + "Z", "bathCount": 1}})
        state.bath_queue = m.encode_cat_world_bath_queue(
            {
                "supply": 1,
                "active": {
                    "catId": first.profile_id,
                    "startedAt": (now - timedelta(seconds=20)).isoformat() + "Z",
                    "endsAt": (now - timedelta(seconds=1)).isoformat() + "Z",
                },
                "queue": [{"catId": second.profile_id, "queuedAt": now.isoformat() + "Z"}],
            }
        )
        db.flush()

        result = m.cat_world_bath_queue_tick(db, state, now=now)
        bath = m.parse_cat_world_bath_queue(state.bath_queue)
        care = m.parse_cat_world_care(state.cat_care)

        self.assertTrue(result["changed"])
        self.assertEqual(result["completed"][0]["catId"], first.profile_id)
        self.assertEqual(care[first.profile_id]["bathCount"], 2)
        self.assertEqual(bath["active"]["catId"], second.profile_id)
        self.assertEqual(bath["supply"], 0)
        self.assertEqual(bath["queue"], [])

    def test_legacy_consumable_request_uses_queue_once(self):
        db = self.new_db()
        state, profile = self.make_world(db, {m.CAT_WORLD_BATH_ITEM_ID: 1})
        with (
            patch.object(m, "require_cat_world_phone", return_value=state.phone),
            patch.object(m, "cat_world_locked_state", return_value=state),
            patch.object(m, "serialize_cat_world_payload", return_value={"state": {}}),
        ):
            result = asyncio.run(
                m.vue_cat_world_use_consumable_api(
                    JsonRequest({"itemId": m.CAT_WORLD_BATH_ITEM_ID, "catId": profile.profile_id}),
                    db,
                )
            )
        self.assertTrue(result["ok"])
        self.assertEqual(m.parse_cat_world_inventory(state.inventory).get(m.CAT_WORLD_BATH_ITEM_ID, 0), 0)
        bath = m.parse_cat_world_bath_queue(state.bath_queue)
        self.assertEqual(bath["active"]["catId"], profile.profile_id)


if __name__ == "__main__":
    unittest.main()
