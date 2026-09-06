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


class CatWorldSceneRoamingTest(unittest.TestCase):
    def make_state(self, db, inventory=None, layout=None, locations=None):
        inventory = inventory or {}
        state = CatWorldState(
            phone="13900000031",
            cats=m.encode_cat_world_cats(["siamese"]),
            selected_cat="siamese",
            inventory=m.encode_cat_world_inventory(inventory),
            room_layout=m.encode_cat_world_room_layout(layout or {}),
            item_locations=m.encode_cat_world_item_locations(locations or {}),
            current_scene_key="main-room",
            cat_bonds=m.encode_cat_world_bonds({}),
            cat_care=m.encode_cat_world_care({}),
            litter_scenes=m.encode_cat_world_litter_scenes({}),
        )
        db.add(state)
        db.flush()
        main_scene = m.cat_world_scene_row(db, "main-room")
        main_user_scene, _ = m.get_or_create_cat_world_user_scene(db, state, main_scene)
        main_user_scene.is_unlocked = True
        db.add(main_user_scene)
        return state

    def unlock_scene(self, db, state, scene_key):
        scene = m.cat_world_scene_row(db, scene_key)
        user_scene, _ = m.get_or_create_cat_world_user_scene(db, state, scene)
        user_scene.is_unlocked = True
        db.add(user_scene)

    def test_cat_roams_to_its_favorite_unlocked_scene_once_per_period(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            m.seed_cat_world_scenes(db)
            state = self.make_state(db)
            self.unlock_scene(db, state, "yard")
            companion = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            profile = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            tired_cat = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            companion.current_scene_key = "main-room"
            profile.current_scene_key = "main-room"
            profile.favorite_scene_key = "yard"
            tired_cat.current_scene_key = "main-room"
            tired_cat.favorite_scene_key = "yard"
            state.selected_cat_profile = companion.profile_id
            state.active_food_cat_id = companion.profile_id
            db.flush()
            now = datetime(2026, 9, 7, 6, 0)
            tired_payload = m.cat_world_cat_profile_payload(tired_cat)
            tired_log = m.get_or_create_cat_world_daily_log(
                db,
                state.phone,
                tired_cat.profile_id,
                datetime.now().date(),
                now,
                tired_payload,
            )
            tired_log.energy_score = 5

            with patch.object(m, "cat_world_stable_ratio", return_value=0.0):
                moves, changed = m.cat_world_apply_autonomous_scene_roaming(
                    db,
                    state,
                    [companion, profile, tired_cat],
                    now,
                )

            self.assertTrue(changed)
            self.assertEqual(companion.current_scene_key, "main-room")
            self.assertEqual(profile.current_scene_key, "yard")
            self.assertEqual(tired_cat.current_scene_key, "main-room")
            self.assertEqual(len(moves), 1)
            self.assertEqual(moves[0]["catId"], profile.profile_id)
            self.assertEqual(moves[0]["fromSceneId"], "main-room")
            self.assertEqual(moves[0]["toSceneId"], "yard")
            self.assertEqual(moves[0]["occurredAt"], "2026-09-07T06:00:00Z")

            log = db.scalar(
                select(CatWorldDailyLog).where(
                    CatWorldDailyLog.phone == state.phone,
                    CatWorldDailyLog.cat_id == profile.profile_id,
                )
            )
            agent_state = m.parse_cat_world_agent_state(log.agent_state)
            self.assertEqual(agent_state["sceneRoamTo"], "yard")
            self.assertEqual(agent_state["events"][-1]["kind"], "scene-roam")

            with patch.object(m, "cat_world_stable_ratio", return_value=0.0):
                repeated_moves, repeated_changed = m.cat_world_apply_autonomous_scene_roaming(
                    db,
                    state,
                    [companion, profile, tired_cat],
                    now,
                )

            self.assertFalse(repeated_changed)
            self.assertEqual(repeated_moves, [])

            manual_now = datetime(2026, 9, 7, 10, 0)
            profile.current_scene_key = "main-room"
            m.cat_world_record_manual_scene_move(
                db,
                state,
                profile,
                "yard",
                "main-room",
                manual_now,
            )
            with patch.object(m, "cat_world_stable_ratio", return_value=0.0):
                held_moves, _ = m.cat_world_apply_autonomous_scene_roaming(
                    db,
                    state,
                    [companion, profile, tired_cat],
                    manual_now,
                )

            self.assertEqual(held_moves, [])
            self.assertEqual(profile.current_scene_key, "main-room")

    def test_selected_cat_can_roam_while_one_companion_keeps_the_active_room(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            m.seed_cat_world_scenes(db)
            state = self.make_state(db)
            self.unlock_scene(db, state, "yard")
            selected = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            companion = m.create_cat_world_cat_profile(db, state, "ragdoll", "test")
            selected.current_scene_key = "main-room"
            selected.favorite_scene_key = "yard"
            companion.current_scene_key = "main-room"
            companion.favorite_scene_key = "yard"
            state.selected_cat_profile = selected.profile_id
            db.flush()

            with (
                patch.object(m, "cat_world_stable_ratio", return_value=0.0),
                patch.object(
                    m,
                    "cat_world_current_behavior",
                    return_value={"key": "exploring", "sleeping": False},
                ),
            ):
                moves, changed = m.cat_world_apply_autonomous_scene_roaming(
                    db,
                    state,
                    [selected, companion],
                    datetime(2026, 9, 7, 10, 0),
                )

            self.assertTrue(changed)
            self.assertEqual(selected.current_scene_key, "yard")
            self.assertEqual(companion.current_scene_key, "main-room")
            self.assertEqual([move["catId"] for move in moves], [selected.profile_id])
            self.assertIn("去了猫咪外院", moves[0]["message"])

    def test_cat_prefers_a_room_containing_its_individual_favorite_item(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            m.seed_cat_world_scenes(db)
            state = self.make_state(db)
            self.unlock_scene(db, state, "yard")
            companion = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            profile = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            profile.profile_id = "siamese-profile-alpha"
            profile.favorite_scene_key = "main-room"
            profile.current_scene_key = "main-room"
            companion.current_scene_key = "main-room"
            state.selected_cat_profile = companion.profile_id
            state.active_food_cat_id = companion.profile_id
            favorite_toy_id = m.cat_world_cat_profile_payload(profile)["favoriteToyIds"][0]
            state.inventory = m.encode_cat_world_inventory({favorite_toy_id: 1})
            state.item_locations = m.encode_cat_world_item_locations({favorite_toy_id: "yard"})
            db.flush()

            with patch.object(m, "cat_world_stable_ratio", return_value=0.0):
                moves, changed = m.cat_world_apply_autonomous_scene_roaming(
                    db,
                    state,
                    [companion, profile],
                    datetime(2026, 9, 7, 6, 0),
                )

            self.assertTrue(changed)
            self.assertEqual(profile.current_scene_key, "yard")
            self.assertEqual(len(moves), 1)
            self.assertEqual(moves[0]["targetItemId"], favorite_toy_id)
            self.assertEqual(moves[0]["targetItemLabel"], m.CAT_WORLD_SHOP_BY_ID[favorite_toy_id]["label"])
            self.assertIn("喜欢的", moves[0]["reason"])
            self.assertIn(m.CAT_WORLD_SHOP_BY_ID[favorite_toy_id]["label"], moves[0]["message"])

    def test_waking_cat_stays_in_its_room_until_recovery_finishes(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            m.seed_cat_world_scenes(db)
            state = self.make_state(db)
            self.unlock_scene(db, state, "yard")
            companion = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            profile = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            companion.current_scene_key = "main-room"
            profile.current_scene_key = "main-room"
            profile.favorite_scene_key = "yard"
            state.selected_cat_profile = companion.profile_id
            db.flush()

            with (
                patch.object(m, "cat_world_stable_ratio", return_value=0.0),
                patch.object(
                    m,
                    "cat_world_current_behavior",
                    return_value={"key": "waking", "sleeping": False},
                ),
            ):
                moves, changed = m.cat_world_apply_autonomous_scene_roaming(
                    db,
                    state,
                    [companion, profile],
                    datetime(2026, 9, 7, 6, 0),
                )

            self.assertTrue(changed)
            self.assertEqual(moves, [])
            self.assertEqual(profile.current_scene_key, "main-room")

    def test_scene_catalog_explains_which_individual_cats_like_each_room(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            m.seed_cat_world_scenes(db)
            state = self.make_state(db)
            self.unlock_scene(db, state, "yard")
            first = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            second = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            first.profile_id = "siamese-profile-alpha"
            second.profile_id = "siamese-profile-beta"
            first.current_scene_key = "main-room"
            second.current_scene_key = "main-room"
            first_cat = m.cat_world_cat_profile_payload(first)
            second_cat = m.cat_world_cat_profile_payload(second)
            first_toy = first_cat["favoriteToyIds"][0]
            second_toy = second_cat["favoriteToyIds"][0]
            self.assertNotEqual(first_toy, second_toy)
            state.inventory = m.encode_cat_world_inventory({first_toy: 1, second_toy: 1})
            state.item_locations = m.encode_cat_world_item_locations(
                {first_toy: "yard", second_toy: "yard"}
            )
            db.flush()

            catalog = m.cat_world_scene_catalog_payload(db, state)
            yard = next(scene for scene in catalog if scene["id"] == "yard")
            main_room = next(scene for scene in catalog if scene["id"] == "main-room")

            self.assertEqual(yard["attractedCatCount"], 2)
            self.assertEqual(yard["attractionItemCount"], 2)
            self.assertEqual(
                {row["catId"] for row in yard["catAttractions"]},
                {first.profile_id, second.profile_id},
            )
            self.assertTrue(all(not row["resident"] for row in yard["catAttractions"]))
            self.assertEqual(main_room["attractedCatCount"], 0)

            state.damaged_items = m.encode_cat_world_damaged_items(
                {first_toy: {"reason": "test damage"}}
            )
            damaged_catalog = m.cat_world_scene_catalog_payload(db, state)
            damaged_yard = next(scene for scene in damaged_catalog if scene["id"] == "yard")

            self.assertEqual(damaged_yard["attractedCatCount"], 1)
            self.assertEqual(damaged_yard["catAttractions"][0]["catId"], second.profile_id)

    def test_favorite_decor_rewards_only_cats_in_the_active_scene(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            m.seed_cat_world_scenes(db)
            state = self.make_state(db)
            room_cat = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            away_cat = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            favorite_decor_id = m.cat_world_cat_profile_payload(room_cat)["favoriteDecorIds"][0]
            inventory = {favorite_decor_id: 1}
            layout = {favorite_decor_id: {"x": 40, "y": 20}}
            state.inventory = m.encode_cat_world_inventory(inventory)
            state.item_locations = m.encode_cat_world_item_locations({favorite_decor_id: "main-room"})
            main_scene = m.cat_world_scene_row(db, "main-room")
            main_user_scene, _ = m.get_or_create_cat_world_user_scene(db, state, main_scene)
            main_user_scene.layout = m.encode_cat_world_room_layout(layout)
            room_cat.current_scene_key = "main-room"
            away_cat.current_scene_key = "yard"
            db.flush()

            rewards = m.cat_world_apply_favorite_decor_rewards(
                db,
                state,
                inventory,
                layout,
                ["siamese"],
                datetime(2026, 9, 7, 6, 0),
            )

            self.assertEqual([reward["catId"] for reward in rewards], [room_cat.profile_id])

    def test_previous_daily_log_prevents_duplicate_roam_in_same_local_period(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            m.seed_cat_world_scenes(db)
            state = self.make_state(db)
            self.unlock_scene(db, state, "yard")
            companion = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            profile = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            companion.current_scene_key = "main-room"
            profile.current_scene_key = "main-room"
            profile.favorite_scene_key = "yard"
            state.selected_cat_profile = companion.profile_id
            now = datetime(2026, 9, 7, 0, 30)
            cat = m.cat_world_cat_profile_payload(profile)
            previous_log = m.get_or_create_cat_world_daily_log(
                db,
                state.phone,
                profile.profile_id,
                date.today() - timedelta(days=1),
                now,
                cat,
            )
            agent_state, _ = m.ensure_cat_world_agent_state(
                previous_log,
                cat,
                m.cat_world_cat_traits(cat),
            )
            agent_state["sceneRoamPeriod"] = m.cat_world_scene_roam_period_token(now)
            agent_state["sceneRoamTo"] = "main-room"
            previous_log.agent_state = m.encode_cat_world_agent_state(agent_state)
            db.add(previous_log)
            db.flush()

            with patch.object(m, "cat_world_stable_ratio", return_value=0.0):
                moves, changed = m.cat_world_apply_autonomous_scene_roaming(
                    db,
                    state,
                    [companion, profile],
                    now,
                )

            self.assertTrue(changed)
            self.assertNotIn(profile.profile_id, [move["catId"] for move in moves])
            self.assertEqual(profile.current_scene_key, "main-room")
            current_log = db.scalar(
                select(CatWorldDailyLog).where(
                    CatWorldDailyLog.phone == state.phone,
                    CatWorldDailyLog.cat_id == profile.profile_id,
                    CatWorldDailyLog.log_date == date.today(),
                )
            )
            current_state = m.parse_cat_world_agent_state(current_log.agent_state)
            self.assertEqual(current_state["sceneRoamPeriod"], m.cat_world_scene_roam_period_token(now))

    def test_daily_comfort_uses_items_from_each_cats_own_scene(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            m.seed_cat_world_scenes(db)
            state = self.make_state(db)
            self.unlock_scene(db, state, "yard")
            room_cat = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            away_cat = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            favorite_decor_id = m.cat_world_cat_profile_payload(room_cat)["favoriteDecorIds"][0]
            inventory = {favorite_decor_id: 1}
            layout = {favorite_decor_id: {"x": 40, "y": 20}}
            state.inventory = m.encode_cat_world_inventory(inventory)
            state.item_locations = m.encode_cat_world_item_locations({favorite_decor_id: "main-room"})
            main_scene = m.cat_world_scene_row(db, "main-room")
            main_user_scene, _ = m.get_or_create_cat_world_user_scene(db, state, main_scene)
            main_user_scene.layout = m.encode_cat_world_room_layout(layout)
            room_cat.current_scene_key = "main-room"
            away_cat.current_scene_key = "yard"
            db.flush()
            environments = {
                scene_key: m.cat_world_scene_environment(db, state, inventory, scene_key)
                for scene_key in {"main-room", "yard"}
            }

            daily_logs, _ = m.cat_world_apply_daily_decay(
                db,
                state,
                inventory,
                [room_cat, away_cat],
                layout,
                {},
                environments,
            )

            self.assertEqual(daily_logs[room_cat.profile_id]["favoriteActiveDecorIds"], [favorite_decor_id])
            self.assertEqual(daily_logs[away_cat.profile_id]["favoriteActiveDecorIds"], [])

    def test_cat_in_another_scene_cannot_damage_active_room_furniture(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            m.seed_cat_world_scenes(db)
            inventory = {"reading-lamp": 1}
            state = self.make_state(
                db,
                inventory=inventory,
                layout={"reading-lamp": {"x": 30, "y": 25}},
                locations={"reading-lamp": "main-room"},
            )
            away_cat = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            away_cat.current_scene_key = "yard"
            db.flush()

            with (
                patch.object(m, "cat_world_damage_attempt_ready", return_value=(True, "心情很差")),
                patch.object(m, "cat_world_damage_probability", return_value=1.0),
                patch.object(m, "cat_world_stable_ratio", return_value=0.0),
            ):
                damaged, changed = m.cat_world_apply_agent_damage_events(
                    db,
                    state,
                    inventory,
                    ["siamese"],
                    {},
                    m.CAT_WORLD_SHOP_BY_ID,
                )

            self.assertFalse(changed)
            self.assertEqual(damaged, {})

    def test_sleep_recovery_defers_room_damage_until_the_cat_is_active(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            m.seed_cat_world_scenes(db)
            inventory = {"reading-lamp": 1}
            state = self.make_state(
                db,
                inventory=inventory,
                layout={"reading-lamp": {"x": 30, "y": 25}},
                locations={"reading-lamp": "main-room"},
            )
            profile = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            profile.current_scene_key = "main-room"
            db.flush()

            with (
                patch.object(m, "cat_world_behavior_allows_mischief", return_value=False) as allows_mischief,
                patch.object(m, "cat_world_damage_attempt_ready", return_value=(True, "心情很差")),
                patch.object(m, "cat_world_damage_probability", return_value=1.0),
                patch.object(m, "cat_world_stable_ratio", return_value=0.0),
            ):
                damaged, changed = m.cat_world_apply_agent_damage_events(
                    db,
                    state,
                    inventory,
                    ["siamese"],
                    {},
                    m.CAT_WORLD_SHOP_BY_ID,
                )

            self.assertTrue(allows_mischief.called)
            self.assertFalse(changed)
            self.assertEqual(damaged, {})

    def test_room_interactions_target_a_cat_in_the_same_scene(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            m.seed_cat_world_scenes(db)
            state = self.make_state(db, inventory={"rolling-ball": 1})
            room_cat = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            away_cat = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            room_cat.current_scene_key = "main-room"
            away_cat.current_scene_key = "yard"
            state.selected_cat_profile = away_cat.profile_id
            db.flush()

            target_id = m.cat_world_effect_target_cat_id(
                db,
                state,
                {"rolling-ball": 1},
                {},
                "toy",
                "rolling-ball",
            )

            self.assertEqual(target_id, room_cat.profile_id)

            mood = m.cat_world_mood(
                db,
                state,
                {"rolling-ball": 1},
                ["siamese"],
                500,
                {},
                {},
            )
            self.assertEqual(mood["selectedCatId"], room_cat.profile_id)


if __name__ == "__main__":
    unittest.main()
