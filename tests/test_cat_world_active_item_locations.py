import asyncio
import os
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.database import Base
from app import main as m
from app.models import CatWorldState


class JsonRequest:
    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        return self.payload


class CatWorldActiveItemLocationTest(unittest.TestCase):
    def make_world(self, db, inventory=None, locations=None):
        m.seed_cat_world_scenes(db)
        state = CatWorldState(
            phone="13900000041",
            cats=m.encode_cat_world_cats(["siamese"]),
            selected_cat="siamese",
            inventory=m.encode_cat_world_inventory(inventory or {}),
            room_layout=m.encode_cat_world_room_layout({}),
            item_locations=m.encode_cat_world_item_locations(locations or {}),
            current_scene_key="main-room",
            cat_bonds=m.encode_cat_world_bonds({}),
            cat_care=m.encode_cat_world_care({}),
            litter_scenes=m.encode_cat_world_litter_scenes({}),
        )
        db.add(state)
        db.flush()
        for scene_key in ("main-room", "yard"):
            scene = m.cat_world_scene_row(db, scene_key)
            user_scene, _ = m.get_or_create_cat_world_user_scene(db, state, scene)
            user_scene.is_unlocked = True
            db.add(user_scene)
        room_cat = m.create_cat_world_cat_profile(db, state, "siamese", "test")
        away_cat = m.create_cat_world_cat_profile(db, state, "siamese", "test")
        room_cat.current_scene_key = "main-room"
        away_cat.current_scene_key = "yard"
        state.selected_cat_profile = room_cat.profile_id
        db.flush()
        return state, room_cat, away_cat

    def test_active_food_and_cat_grass_keep_their_scene(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            state, room_cat, away_cat = self.make_world(db)
            state.active_food_item = "daily-kibble"
            state.active_food_cat_id = away_cat.profile_id
            state.active_food_at = datetime.utcnow() - timedelta(minutes=1)
            state.active_care_item = m.CAT_WORLD_CAT_GRASS_ITEM_ID
            state.active_care_cat_id = room_cat.profile_id
            state.active_care_at = datetime.utcnow() - timedelta(minutes=1)
            db.flush()

            food = m.cat_world_active_food(db, state)
            care = m.cat_world_active_care_payload(db, state)
            mood = m.cat_world_mood(db, state, {}, ["siamese"], 500, {}, {})
            scenes = {scene["id"]: scene for scene in m.cat_world_scene_catalog_payload(db, state)}

            self.assertTrue(food["active"])
            self.assertFalse(food["inCurrentScene"])
            self.assertEqual(food["sceneId"], "yard")
            self.assertFalse(mood["activeFood"]["active"])
            self.assertTrue(mood["activeFood"]["activeElsewhere"])
            self.assertTrue(care["active"])
            self.assertEqual(care["sceneId"], "main-room")
            self.assertTrue(scenes["yard"]["hasActiveFood"])
            self.assertFalse(scenes["yard"]["hasActiveCare"])
            self.assertTrue(scenes["main-room"]["hasActiveCare"])

            state.current_scene_key = "yard"
            care = m.cat_world_active_care_payload(db, state)
            self.assertFalse(care["active"])
            self.assertTrue(care["activeElsewhere"])

    def test_room_deodorizer_only_reaches_cats_in_current_room(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            state, room_cat, away_cat = self.make_world(db, {"room-deodorizer": 1})
            now = datetime.utcnow()
            room_payload = m.cat_world_cat_profile_payload(room_cat)
            away_payload = m.cat_world_cat_profile_payload(away_cat)
            room_log = m.get_or_create_cat_world_daily_log(
                db, state.phone, room_cat.profile_id, date.today(), now, room_payload
            )
            away_log = m.get_or_create_cat_world_daily_log(
                db, state.phone, away_cat.profile_id, date.today(), now, away_payload
            )
            room_log.mood_score = 50
            away_log.mood_score = 50
            db.flush()

            with (
                patch.object(m, "require_cat_world_phone", return_value=state.phone),
                patch.object(m, "get_or_create_cat_world_state", return_value=state),
                patch.object(m, "apply_cat_world_hourly_decay", return_value=False),
                patch.object(m, "serialize_cat_world_payload", return_value={"testPayload": True}),
            ):
                result = asyncio.run(
                    m.vue_cat_world_use_consumable_api(
                        JsonRequest({"itemId": "room-deodorizer"}),
                        db,
                    )
                )

            self.assertTrue(result["ok"])
            self.assertEqual([effect["catId"] for effect in result["effect"]["effects"]], [room_cat.profile_id])
            self.assertEqual(room_log.mood_score, 55)
            self.assertEqual(away_log.mood_score, 50)
            self.assertNotIn("room-deodorizer", m.parse_cat_world_inventory(state.inventory))

    def test_away_cat_cannot_be_cared_for_or_fed_from_another_room(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            state, _, away_cat = self.make_world(
                db,
                {m.CAT_WORLD_BATH_ITEM_ID: 1, "daily-kibble": 1},
            )
            state.active_food_item = "daily-kibble"
            state.active_food_cat_id = away_cat.profile_id
            state.active_food_at = datetime.utcnow()
            db.flush()

            with (
                patch.object(m, "require_cat_world_phone", return_value=state.phone),
                patch.object(m, "get_or_create_cat_world_state", return_value=state),
            ):
                with self.assertRaisesRegex(HTTPException, "不在当前房间"):
                    asyncio.run(
                        m.vue_cat_world_use_consumable_api(
                            JsonRequest({"itemId": m.CAT_WORLD_BATH_ITEM_ID, "catId": away_cat.profile_id}),
                            db,
                        )
                    )
                with self.assertRaisesRegex(HTTPException, "不能隔着房间喂"):
                    asyncio.run(
                        m.vue_cat_world_food_nibble_api(
                            JsonRequest({"catId": away_cat.profile_id}),
                            db,
                        )
                    )

            inventory = m.parse_cat_world_inventory(state.inventory)
            self.assertEqual(inventory[m.CAT_WORLD_BATH_ITEM_ID], 1)

    def test_cat_with_active_food_cannot_be_carried_to_another_scene(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            state, _, away_cat = self.make_world(db)
            state.active_food_item = "daily-kibble"
            state.active_food_cat_id = away_cat.profile_id
            state.active_food_at = datetime.utcnow()
            db.flush()

            with (
                patch.object(m, "require_cat_world_phone", return_value=state.phone),
                patch.object(m, "get_or_create_cat_world_state", return_value=state),
            ):
                with self.assertRaisesRegex(HTTPException, "正在进食"):
                    asyncio.run(
                        m.vue_cat_world_select_cat_api(
                            JsonRequest(
                                {
                                    "catId": away_cat.breed_id,
                                    "profileId": away_cat.profile_id,
                                    "moveToCurrentScene": True,
                                }
                            ),
                            db,
                        )
                    )

            self.assertEqual(away_cat.current_scene_key, "yard")

    def test_new_timed_items_cannot_overwrite_items_active_in_another_scene(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            inventory = {"chicken-broth": 1, m.CAT_WORLD_CAT_GRASS_ITEM_ID: 2}
            state, room_cat, away_cat = self.make_world(db, inventory)
            state.active_food_item = "daily-kibble"
            state.active_food_cat_id = away_cat.profile_id
            state.active_food_at = datetime.utcnow()
            state.active_care_item = m.CAT_WORLD_CAT_GRASS_ITEM_ID
            state.active_care_cat_id = away_cat.profile_id
            state.active_care_at = datetime.utcnow()
            db.flush()

            with (
                patch.object(m, "require_cat_world_phone", return_value=state.phone),
                patch.object(m, "get_or_create_cat_world_state", return_value=state),
            ):
                with self.assertRaisesRegex(HTTPException, "还在进食"):
                    asyncio.run(
                        m.vue_cat_world_play_api(
                            JsonRequest({"itemId": "chicken-broth"}),
                            db,
                        )
                    )
                with self.assertRaisesRegex(HTTPException, "还在互动"):
                    asyncio.run(
                        m.vue_cat_world_use_consumable_api(
                            JsonRequest(
                                {
                                    "itemId": m.CAT_WORLD_CAT_GRASS_ITEM_ID,
                                    "catId": room_cat.profile_id,
                                }
                            ),
                            db,
                        )
                    )

            remaining = m.parse_cat_world_inventory(state.inventory)
            self.assertEqual(remaining["chicken-broth"], 1)
            self.assertEqual(remaining[m.CAT_WORLD_CAT_GRASS_ITEM_ID], 2)
            self.assertEqual(state.active_food_cat_id, away_cat.profile_id)
            self.assertEqual(state.active_care_cat_id, away_cat.profile_id)

    def test_food_progress_reads_the_target_cats_scene_environment(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            inventory = {"daily-kibble": 1}
            state, _, away_cat = self.make_world(
                db,
                inventory,
                {},
            )
            favorite_decor_id = m.cat_world_cat_profile_payload(away_cat)["favoriteDecorIds"][0]
            inventory[favorite_decor_id] = 1
            state.inventory = m.encode_cat_world_inventory(inventory)
            state.item_locations = m.encode_cat_world_item_locations({favorite_decor_id: "second-floor"})
            reading_room = m.cat_world_scene_row(db, "second-floor")
            reading_scene, _ = m.get_or_create_cat_world_user_scene(db, state, reading_room)
            reading_scene.is_unlocked = True
            reading_scene.layout = m.encode_cat_world_room_layout({favorite_decor_id: {"x": 45, "y": 25}})
            away_cat.current_scene_key = "second-floor"
            state.active_food_item = "daily-kibble"
            state.active_food_cat_id = away_cat.profile_id
            state.active_food_at = datetime.utcnow()
            db.flush()

            with patch.object(m, "apply_cat_world_hourly_decay", return_value=False) as decay:
                effect = m.cat_world_apply_active_food_progress(
                    db,
                    state,
                    inventory,
                    {},
                    now=state.active_food_at,
                )

            decay_inventory = decay.call_args.args[2]
            favorite_count = decay.call_args.args[3]
            self.assertEqual(effect["sceneId"], "second-floor")
            self.assertIn(favorite_decor_id, decay_inventory)
            self.assertEqual(favorite_count, 1)


if __name__ == "__main__":
    unittest.main()
