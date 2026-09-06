import asyncio
import os
import unittest
from unittest.mock import patch

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


class CatWorldItemPositionMemoryTest(unittest.TestCase):
    def make_world(self, db):
        m.seed_cat_world_scenes(db)
        state = CatWorldState(
            phone="13900000051",
            cats=m.encode_cat_world_cats(["siamese"]),
            selected_cat="siamese",
            inventory=m.encode_cat_world_inventory({"cloud-rug": 1, "rolling-ball": 1}),
            room_layout=m.encode_cat_world_room_layout({}),
            item_locations=m.encode_cat_world_item_locations(
                {"cloud-rug": "main-room", "rolling-ball": "yard"}
            ),
            current_scene_key="main-room",
            cat_bonds=m.encode_cat_world_bonds({}),
            cat_care=m.encode_cat_world_care({}),
            litter_scenes=m.encode_cat_world_litter_scenes({}),
        )
        db.add(state)
        db.flush()
        main_scene = m.cat_world_scene_row(db, "main-room")
        yard_scene = m.cat_world_scene_row(db, "yard")
        main_user_scene, _ = m.get_or_create_cat_world_user_scene(db, state, main_scene)
        yard_user_scene, _ = m.get_or_create_cat_world_user_scene(db, state, yard_scene)
        main_user_scene.is_unlocked = True
        yard_user_scene.is_unlocked = True
        main_user_scene.layout = m.encode_cat_world_room_layout(
            {"cloud-rug": {"x": 42, "y": 61}}
        )
        yard_user_scene.layout = m.encode_cat_world_room_layout(
            {
                "cloud-rug": {"x": 74, "y": 68},
                "rolling-ball": {"x": 28, "y": 72},
            }
        )
        db.add_all([main_user_scene, yard_user_scene])
        db.flush()
        return state, main_user_scene, yard_user_scene

    def test_moving_an_item_restores_the_destination_rooms_remembered_position(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            state, main_user_scene, yard_user_scene = self.make_world(db)
            with (
                patch.object(m, "require_cat_world_phone", return_value=state.phone),
                patch.object(m, "cat_world_locked_state", return_value=state),
                patch.object(m, "serialize_cat_world_payload", return_value={"snapshot": True}),
            ):
                stored = asyncio.run(
                    m.vue_cat_world_item_location_api(
                        JsonRequest({"itemId": "cloud-rug", "locationId": "storage"}),
                        db,
                    )
                )
                result = asyncio.run(
                    m.vue_cat_world_item_location_api(
                        JsonRequest({"itemId": "cloud-rug", "locationId": "yard"}),
                        db,
                    )
                )

            db.refresh(main_user_scene)
            db.refresh(yard_user_scene)
            self.assertFalse(stored["itemLocation"]["restoredPosition"])
            self.assertIsNone(stored["itemLocation"]["position"])
            self.assertTrue(result["itemLocation"]["restoredPosition"])
            self.assertEqual(result["itemLocation"]["position"], {"x": 74.0, "y": 68.0})
            self.assertEqual(
                m.parse_cat_world_scene_json(main_user_scene.layout, {})["cloud-rug"],
                {"x": 42.0, "y": 61.0},
            )
            self.assertEqual(
                m.parse_cat_world_scene_json(yard_user_scene.layout, {})["cloud-rug"],
                {"x": 74.0, "y": 68.0},
            )
            inventory = m.parse_cat_world_inventory(state.inventory)
            locations = m.parse_cat_world_item_locations(state.item_locations, inventory)
            self.assertEqual(locations["cloud-rug"], "yard")

    def test_saving_visible_furniture_keeps_hidden_item_position_memory(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            state, _, yard_user_scene = self.make_world(db)
            state.current_scene_key = "yard"
            state.item_locations = m.encode_cat_world_item_locations(
                {"cloud-rug": "main-room", "rolling-ball": "yard"}
            )
            db.flush()
            with (
                patch.object(m, "require_cat_world_phone", return_value=state.phone),
                patch.object(m, "cat_world_apply_favorite_decor_rewards", return_value=[]),
                patch.object(m, "serialize_cat_world_payload", return_value={"snapshot": True}),
            ):
                asyncio.run(
                    m.vue_cat_world_room_layout_api(
                        JsonRequest(
                            {
                                "sceneId": "yard",
                                "layout": {"rolling-ball": {"x": 36, "y": 76}},
                            }
                        ),
                        db,
                    )
                )

            db.refresh(yard_user_scene)
            saved = m.parse_cat_world_scene_json(yard_user_scene.layout, {})
            self.assertEqual(saved["cloud-rug"], {"x": 74.0, "y": 68.0})
            self.assertEqual(saved["rolling-ball"], {"x": 36.0, "y": 76.0})


if __name__ == "__main__":
    unittest.main()
