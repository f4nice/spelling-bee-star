import asyncio
import os
import unittest
from datetime import date, datetime
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


# These regressions must never inherit a real development or production database.
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from app.database import Base
from app import main as m
from app.models import CatWorldState


class JsonRequest:
    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        return self.payload


class CatWorldToyTargetTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.addCleanup(self.db.close)
        m.seed_cat_world_scenes(self.db)
        self.state = CatWorldState(
            phone="13900000081",
            cats=m.encode_cat_world_cats(["siamese"]),
            selected_cat="siamese",
            inventory=m.encode_cat_world_inventory({"rolling-ball": 1, "daily-kibble": 2}),
            room_layout=m.encode_cat_world_room_layout({}),
            item_locations=m.encode_cat_world_item_locations({"rolling-ball": "main-room"}),
            current_scene_key="main-room",
            cat_bonds=m.encode_cat_world_bonds({}),
            cat_care=m.encode_cat_world_care({}),
            litter_scenes=m.encode_cat_world_litter_scenes({}),
        )
        self.db.add(self.state)
        self.db.flush()
        self.first = m.create_cat_world_cat_profile(self.db, self.state, "siamese", "test")
        self.second = m.create_cat_world_cat_profile(self.db, self.state, "siamese", "test")
        self.first.current_scene_key = "main-room"
        self.second.current_scene_key = "main-room"
        self.state.selected_cat_profile = self.first.profile_id
        self.logs = {}
        for profile in (self.first, self.second):
            log = m.get_or_create_cat_world_daily_log(
                self.db,
                self.state.phone,
                profile.profile_id,
                date.today(),
                datetime.utcnow(),
                m.cat_world_cat_profile_payload(profile),
            )
            log.mood_score = 40
            log.energy_score = 80
            log.toy_count = 0
            log.food_count = 0
            log.agent_state = m.encode_cat_world_agent_state({"energyOffset": 0})
            self.logs[profile.profile_id] = log
        self.db.commit()
        for patcher in (
            patch.object(m, "require_cat_world_phone", return_value=self.state.phone),
            patch.object(m, "get_or_create_cat_world_state", return_value=self.state),
            patch.object(m, "cat_world_active_scene_layout", return_value={}),
            patch.object(m, "apply_cat_world_hourly_decay", return_value=False),
            patch.object(m, "serialize_cat_world_payload", return_value={"testPayload": True}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def play(self, payload):
        return asyncio.run(m.vue_cat_world_play_api(JsonRequest(payload), self.db))

    def assert_only_cat_played(self, result, target, untouched):
        target_log = self.logs[target.profile_id]
        untouched_log = self.logs[untouched.profile_id]
        self.assertTrue(result["ok"])
        self.assertEqual(result["effect"]["catId"], target.profile_id)
        self.assertEqual(result["effect"]["bond"]["catId"], target.profile_id)
        self.assertEqual(target_log.toy_count, 1)
        self.assertEqual(target_log.last_play_item, "rolling-ball")
        self.assertGreater(target_log.mood_score, 40)
        self.assertLess(target_log.energy_score, 80)
        self.assertEqual(untouched_log.toy_count, 0)
        self.assertEqual(untouched_log.mood_score, 40)
        self.assertEqual(untouched_log.energy_score, 80)
        self.assertEqual(self.state.selected_cat_profile, self.first.profile_id)
        self.assertEqual(self.state.selected_cat, "siamese")
        self.assertEqual(m.parse_cat_world_inventory(self.state.inventory)["rolling-ball"], 1)

    def test_explicit_profile_targets_second_cat_of_same_breed_without_changing_main_cat(self):
        self.assertEqual(self.first.breed_id, self.second.breed_id)
        result = self.play({"itemId": "rolling-ball", "catId": self.second.profile_id})
        self.assert_only_cat_played(result, self.second, self.first)

    def test_omitted_target_retains_selected_main_cat_behavior(self):
        result = self.play({"itemId": "rolling-ball"})
        self.assert_only_cat_played(result, self.first, self.second)

    def assert_toy_target_rejected_without_changes(self, cat_id):
        self.db.commit()
        before_state = (
            self.state.selected_cat_profile,
            self.state.selected_cat,
            self.state.inventory,
            self.state.cat_bonds,
            self.state.last_play_item,
            self.state.last_played_at,
        )
        before_logs = {
            profile_id: (log.toy_count, log.mood_score, log.energy_score, log.agent_state)
            for profile_id, log in self.logs.items()
        }
        with self.assertRaises(HTTPException) as rejected:
            self.play({"itemId": "rolling-ball", "catId": cat_id})
        self.assertEqual(rejected.exception.status_code, 400)
        self.assertEqual(
            (
                self.state.selected_cat_profile,
                self.state.selected_cat,
                self.state.inventory,
                self.state.cat_bonds,
                self.state.last_play_item,
                self.state.last_played_at,
            ),
            before_state,
        )
        self.assertEqual(
            {
                profile_id: (log.toy_count, log.mood_score, log.energy_score, log.agent_state)
                for profile_id, log in self.logs.items()
            },
            before_logs,
        )
        self.assertFalse(self.db.dirty)

    def test_unknown_profile_is_rejected_instead_of_falling_back(self):
        self.assert_toy_target_rejected_without_changes("missing-cat-profile")

    def test_breed_id_is_not_accepted_as_an_explicit_individual_target(self):
        self.assert_toy_target_rejected_without_changes("siamese")

    def test_cat_in_another_room_is_rejected_instead_of_falling_back(self):
        self.second.current_scene_key = "yard"
        self.assert_toy_target_rejected_without_changes(self.second.profile_id)

    def test_inactive_cat_is_rejected_instead_of_falling_back(self):
        self.second.is_active = False
        self.assert_toy_target_rejected_without_changes(self.second.profile_id)

    def test_another_accounts_cat_is_rejected_instead_of_falling_back(self):
        self.second.phone = "13900000082"
        self.assert_toy_target_rejected_without_changes(self.second.profile_id)

    def assert_food_chooses_hungry_cat(self, requested_cat_id):
        self.logs[self.second.profile_id].energy_score = 20
        self.db.flush()
        result = self.play({"itemId": "daily-kibble", "catId": requested_cat_id})
        self.assertTrue(result["ok"])
        self.assertEqual(result["effect"]["catId"], self.second.profile_id)
        self.assertEqual(self.state.active_food_cat_id, self.second.profile_id)
        self.assertEqual(self.logs[self.second.profile_id].food_count, 1)
        self.assertGreater(self.logs[self.second.profile_id].energy_score, 20)
        self.assertEqual(self.logs[self.first.profile_id].food_count, 0)
        self.assertEqual(self.logs[self.first.profile_id].energy_score, 80)
        self.assertEqual(self.state.selected_cat_profile, self.first.profile_id)
        self.assertEqual(m.parse_cat_world_inventory(self.state.inventory)["daily-kibble"], 1)

    def test_food_ignores_explicit_main_cat_and_still_feeds_lowest_energy_cat(self):
        self.assert_food_chooses_hungry_cat(self.first.profile_id)

    def test_food_ignores_unknown_cat_id_and_still_uses_existing_food_policy(self):
        self.assert_food_chooses_hungry_cat("missing-cat-profile")

    def test_daily_food_effect_ignores_optional_toy_target(self):
        self.logs[self.second.profile_id].energy_score = 20
        self.db.flush()
        effect = m.cat_world_apply_daily_effect(
            self.db,
            self.state,
            m.CAT_WORLD_SHOP_BY_ID["daily-kibble"],
            m.parse_cat_world_inventory(self.state.inventory),
            {},
            "food",
            target_cat_id=self.first.profile_id,
        )
        self.assertEqual(effect["catId"], self.second.profile_id)
        self.assertEqual(self.logs[self.second.profile_id].food_count, 1)
        self.assertEqual(self.logs[self.first.profile_id].food_count, 0)
        self.assertEqual(self.state.selected_cat_profile, self.first.profile_id)


if __name__ == "__main__":
    unittest.main()
