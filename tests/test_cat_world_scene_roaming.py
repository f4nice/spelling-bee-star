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

    def test_favorite_decor_rewards_only_cats_in_the_active_scene(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            m.seed_cat_world_scenes(db)
            inventory = {"moon-window": 1}
            layout = {"moon-window": {"x": 40, "y": 20}}
            state = self.make_state(
                db,
                inventory=inventory,
                layout=layout,
                locations={"moon-window": "main-room"},
            )
            room_cat = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            away_cat = m.create_cat_world_cat_profile(db, state, "siamese", "test")
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
            self.assertEqual(moves, [])
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
            inventory = {"moon-window": 1}
            layout = {"moon-window": {"x": 40, "y": 20}}
            state = self.make_state(
                db,
                inventory=inventory,
                layout=layout,
                locations={"moon-window": "main-room"},
            )
            self.unlock_scene(db, state, "yard")
            room_cat = m.create_cat_world_cat_profile(db, state, "siamese", "test")
            away_cat = m.create_cat_world_cat_profile(db, state, "siamese", "test")
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

            self.assertEqual(daily_logs[room_cat.profile_id]["favoriteActiveDecorIds"], ["moon-window"])
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
