import os
import unittest
from datetime import UTC, date, datetime

from sqlalchemy import create_engine
from fastapi import HTTPException
from sqlalchemy.orm import Session


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.database import Base
from app.main import (
    CAT_WORLD_RENAME_CARD_ITEM_ID,
    CAT_WORLD_SHOP_BY_ID,
    cat_world_apply_cat_bond,
    cat_world_apply_learning_companion_rewards,
    cat_world_apply_pet_effect,
    cat_world_cat_profile_payload,
    cat_world_profile_favorite_item_ids,
    cat_world_consume_rename_card,
    cat_world_learning_companion_profile_id,
    cat_world_learning_companion_message,
    cat_world_normalize_nickname,
    cat_world_profile_learning_style,
    create_cat_world_cat_profile,
    encode_cat_world_bonds,
    encode_cat_world_care,
    encode_cat_world_cats,
    ensure_cat_world_agent_state,
    ensure_cat_world_cat_profiles,
    get_or_create_cat_world_daily_log,
    parse_cat_world_agent_state,
    parse_cat_world_bonds,
)
from app.models import CatWorldDailyLog, CatWorldState


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CatWorldIndividualProfileTest(unittest.TestCase):
    def test_learning_companion_stays_assigned_across_room_and_cat_changes(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            state = CatWorldState(
                phone="13900000003",
                cats=encode_cat_world_cats(["siamese"]),
                selected_cat="siamese",
                current_scene_key="main-room",
                inventory="{}",
            )
            db.add(state)
            db.flush()
            selected_elsewhere = create_cat_world_cat_profile(db, state, "siamese", "test")
            room_cat = create_cat_world_cat_profile(db, state, "siamese", "test")
            selected_elsewhere.current_scene_key = "outdoor-yard"
            room_cat.current_scene_key = "main-room"
            state.selected_cat_profile = selected_elsewhere.profile_id
            db.flush()

            self.assertEqual(
                cat_world_learning_companion_profile_id(
                    state,
                    [selected_elsewhere, room_cat],
                    [],
                ),
                room_cat.profile_id,
            )

            assigned_log = CatWorldDailyLog(
                phone=state.phone,
                log_date=date.today(),
                cat_id=selected_elsewhere.profile_id,
                mood_score=70,
                energy_score=70,
                last_decay_at=utc_now(),
                agent_state='{"learningCompanionAssigned": true}',
            )
            self.assertEqual(
                cat_world_learning_companion_profile_id(
                    state,
                    [selected_elsewhere, room_cat],
                    [assigned_log],
                ),
                selected_elsewhere.profile_id,
            )

    def test_daily_learning_milestones_reward_only_the_companion_cat_once(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            phone = "13900000002"
            state = CatWorldState(
                phone=phone,
                cats=encode_cat_world_cats(["siamese"]),
                selected_cat="siamese",
                inventory="{}",
            )
            db.add(state)
            db.flush()
            companion = create_cat_world_cat_profile(db, state, "siamese", "test")
            other_cat = create_cat_world_cat_profile(db, state, "siamese", "test")
            db.flush()
            companion_cat = cat_world_cat_profile_payload(companion)
            other_cat_payload = cat_world_cat_profile_payload(other_cat)
            now = utc_now()
            companion_log = get_or_create_cat_world_daily_log(
                db, phone, companion.profile_id, date.today(), now, companion_cat
            )
            other_log = get_or_create_cat_world_daily_log(
                db, phone, other_cat.profile_id, date.today(), now, other_cat_payload
            )
            companion_log.mood_score = 70
            other_log.mood_score = 70
            starting_habit = {
                "todaySpellingCount": 5,
                "todayHasEssay": False,
                "todayHasDebate": False,
                "todayBalanceComplete": False,
                "nextAction": "再完成 15 词",
            }
            starting_reward = cat_world_apply_learning_companion_rewards(
                state,
                companion_log,
                companion_cat,
                companion_cat["traits"],
                starting_habit,
                now,
            )

            self.assertEqual(starting_reward["statusKey"], "started")
            self.assertEqual(starting_reward["statusLabel"], "已陪你迈出第一步")
            self.assertEqual(starting_reward["newMilestones"], ["started"])
            self.assertEqual(starting_reward["newMoodGain"], 1)
            self.assertEqual(starting_reward["newBondGain"], 1)
            self.assertEqual(companion_log.mood_score, 71)

            habit = {
                "todaySpellingCount": 20,
                "todayHasEssay": True,
                "todayHasDebate": False,
                "todayBalanceComplete": True,
                "nextAction": "今日学习闭环已完成",
            }

            reward = cat_world_apply_learning_companion_rewards(
                state,
                companion_log,
                companion_cat,
                companion_cat["traits"],
                habit,
                now,
            )

            self.assertTrue(reward["changed"])
            self.assertEqual(reward["statusKey"], "loop")
            self.assertEqual(reward["learningStyle"], companion_cat["learningStyle"])
            self.assertEqual(reward["newMilestones"], ["warmup", "output", "loop"])
            self.assertEqual(reward["newMoodGain"], 7)
            self.assertEqual(reward["newBondGain"], 3)
            self.assertEqual(companion_log.mood_score, 78)
            self.assertEqual(other_log.mood_score, 70)
            bonds = parse_cat_world_bonds(state.cat_bonds)
            self.assertEqual(bonds[companion.profile_id]["score"], 22)
            self.assertNotIn(other_cat.profile_id, bonds)
            agent_state = parse_cat_world_agent_state(companion_log.agent_state)
            self.assertTrue(agent_state["learningCompanionAssigned"])
            self.assertEqual(
                set(agent_state["learningCompanionMilestones"]),
                {"started", "warmup", "output", "loop"},
            )
            companion_events = [
                event
                for event in agent_state.get("events", [])
                if event.get("kind") == "learning-companion"
            ]
            self.assertEqual(len(companion_events), 4)
            self.assertEqual(
                {event.get("label") for event in companion_events},
                {"5 词起步", "20 词热身", "英语输出", "今日学习闭环"},
            )
            self.assertEqual(len({event.get("message") for event in companion_events}), 4)

            duplicate = cat_world_apply_learning_companion_rewards(
                state,
                companion_log,
                companion_cat,
                companion_cat["traits"],
                habit,
                now,
            )
            self.assertFalse(duplicate["changed"])
            self.assertEqual(duplicate["newMoodGain"], 0)
            self.assertEqual(duplicate["newBondGain"], 0)
            self.assertEqual(companion_log.mood_score, 78)
            self.assertEqual(parse_cat_world_bonds(state.cat_bonds)[companion.profile_id]["score"], 22)

    def test_learning_companion_lines_follow_individual_temperament(self):
        calm = cat_world_learning_companion_message({"temperament": "calm"}, "warmup")
        chatty = cat_world_learning_companion_message({"temperament": "chatty"}, "warmup")
        gentle_start = cat_world_learning_companion_message({"temperament": "gentle"}, "started")

        self.assertNotEqual(calm, chatty)
        self.assertIn("20 词", calm)
        self.assertIn("听", chatty)
        self.assertIn("慢慢", gentle_start)

    def test_learning_companion_lines_follow_the_cat_learning_style(self):
        style = {"key": "idea-sparring"}
        message = cat_world_learning_companion_message(
            {"temperament": "calm"},
            "warmup",
            learning_style=style,
        )

        self.assertIn("AI Debate", message)

    def test_nickname_is_individual_and_validated(self):
        self.assertEqual(CAT_WORLD_SHOP_BY_ID[CAT_WORLD_RENAME_CARD_ITEM_ID]["cost"], 200)
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            state = CatWorldState(
                phone="13900000001",
                cats=encode_cat_world_cats(["siamese"]),
                selected_cat="siamese",
                inventory="{}",
            )
            db.add(state)
            db.flush()
            first = create_cat_world_cat_profile(db, state, "siamese", "test")
            second = create_cat_world_cat_profile(db, state, "siamese", "test")
            first.nickname = cat_world_normalize_nickname("  小闪电  ")
            db.flush()

            first_payload = cat_world_cat_profile_payload(first)
            second_payload = cat_world_cat_profile_payload(second)
            self.assertEqual(first_payload["nickname"], "小闪电")
            self.assertEqual(first_payload["displayLabel"], "小闪电")
            self.assertEqual(second_payload["nickname"], "")
            self.assertIn("暹罗猫", second_payload["displayLabel"])

        with self.assertRaises(HTTPException):
            cat_world_normalize_nickname("")
        with self.assertRaises(HTTPException):
            cat_world_normalize_nickname("名字超过十二个字符就不可以保存")
        with self.assertRaises(HTTPException):
            cat_world_normalize_nickname("坏\n名字")

        inventory = {CAT_WORLD_RENAME_CARD_ITEM_ID: 1}
        self.assertEqual(cat_world_consume_rename_card(inventory), 0)
        self.assertNotIn(CAT_WORLD_RENAME_CARD_ITEM_ID, inventory)
        with self.assertRaises(HTTPException):
            cat_world_consume_rename_card(inventory)

    def test_same_breed_cats_keep_individual_personality_and_state(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)

        with Session(engine) as db:
            phone = "13900000000"
            state = CatWorldState(
                phone=phone,
                cats=encode_cat_world_cats(["siamese"]),
                selected_cat="siamese",
                inventory="{}",
                cat_bonds=encode_cat_world_bonds(
                    {"siamese": {"score": 44, "totalGain": 26}}
                ),
                cat_care=encode_cat_world_care(
                    {
                        "siamese": {
                            "lastBathAt": "2026-07-27T00:00:00Z",
                            "bathCount": 1,
                        }
                    }
                ),
            )
            db.add(state)
            db.flush()

            first = create_cat_world_cat_profile(db, state, "siamese", "test")
            second = create_cat_world_cat_profile(db, state, "siamese", "test")
            first.profile_id = "siamese-profile-alpha"
            second.profile_id = "siamese-profile-beta"
            db.flush()

            first_cat = cat_world_cat_profile_payload(first)
            second_cat = cat_world_cat_profile_payload(second)
            self.assertNotEqual(first.profile_id, second.profile_id)
            self.assertNotEqual(first.personality_key, second.personality_key)
            self.assertEqual(first_cat["traits"]["personalityModel"], 2)
            self.assertEqual(second_cat["traits"]["personalityModel"], 2)
            self.assertNotEqual(first_cat["traits"], second_cat["traits"])
            self.assertEqual(first_cat["preferenceModel"], 1)
            self.assertEqual(second_cat["preferenceModel"], 1)
            self.assertEqual(first_cat["favoriteItemIds"], cat_world_profile_favorite_item_ids(first))
            self.assertEqual(second_cat["favoriteItemIds"], cat_world_profile_favorite_item_ids(second))
            self.assertNotEqual(first_cat["favoriteFoodIds"], second_cat["favoriteFoodIds"])
            self.assertNotEqual(first_cat["favoriteToyIds"], second_cat["favoriteToyIds"])
            self.assertNotEqual(first_cat["favoriteDecorIds"], second_cat["favoriteDecorIds"])
            self.assertNotEqual(
                first_cat["individualHabit"]["id"],
                second_cat["individualHabit"]["id"],
            )
            self.assertEqual(
                first_cat["individualHabit"],
                cat_world_cat_profile_payload(first)["individualHabit"],
            )
            self.assertIn(
                first_cat["individualHabit"]["thought"],
                first_cat["thoughts"],
            )
            self.assertTrue(first_cat["individualHabit"]["label"])
            self.assertIsInstance(first_cat["individualHabit"]["targetItemIds"], list)
            self.assertEqual(
                first_cat["learningStyle"],
                cat_world_profile_learning_style(first),
            )
            original_learning_style = first_cat["learningStyle"]
            first.breed_id = "ragdoll"
            self.assertEqual(
                original_learning_style,
                cat_world_profile_learning_style(first),
            )
            first.breed_id = "siamese"

            second.personality_key = first.personality_key
            second.personality_label = first.personality_label
            second.personality_traits = first.personality_traits
            db.add(second)
            db.flush()

            now = utc_now()
            db.add(
                CatWorldDailyLog(
                    phone=phone,
                    log_date=date.today(),
                    cat_id="siamese",
                    mood_score=77,
                    energy_score=66,
                    last_decay_at=now,
                )
            )
            db.flush()

            _, changed = ensure_cat_world_cat_profiles(db, state, ["siamese"])
            self.assertTrue(changed)
            self.assertNotEqual(first.personality_key, second.personality_key)
            first_cat = cat_world_cat_profile_payload(first)
            second_cat = cat_world_cat_profile_payload(second)
            self.assertEqual(first_cat["traits"]["personalityModel"], 2)
            self.assertEqual(second_cat["traits"]["personalityModel"], 2)
            self.assertNotEqual(first_cat["traits"], second_cat["traits"])
            migrated_bonds = parse_cat_world_bonds(state.cat_bonds)
            self.assertEqual(migrated_bonds[first.profile_id]["score"], 44)
            self.assertEqual(migrated_bonds[second.profile_id]["score"], 44)

            first_log = get_or_create_cat_world_daily_log(
                db, phone, first.profile_id, date.today(), now, first_cat
            )
            second_log = get_or_create_cat_world_daily_log(
                db, phone, second.profile_id, date.today(), now, second_cat
            )
            self.assertEqual(first_log.mood_score, 77)
            self.assertEqual(second_log.mood_score, 77)
            self.assertNotEqual(first_log.cat_id, second_log.cat_id)

            first_agent, _ = ensure_cat_world_agent_state(
                first_log, first_cat, first_cat["traits"]
            )
            second_agent, _ = ensure_cat_world_agent_state(
                second_log, second_cat, second_cat["traits"]
            )
            self.assertNotEqual(first_agent["seedKey"], second_agent["seedKey"])

            cat_world_apply_cat_bond(
                state, first.profile_id, 5, "test", "first cat", now
            )
            updated_bonds = parse_cat_world_bonds(state.cat_bonds)
            self.assertEqual(updated_bonds[first.profile_id]["score"], 49)
            self.assertEqual(updated_bonds[second.profile_id]["score"], 44)

            first_pet = cat_world_apply_pet_effect(
                db, state, first.profile_id, {}, {}
            )
            second_pet = cat_world_apply_pet_effect(
                db, state, second.profile_id, {}, {}
            )
            self.assertTrue(first_pet["rewarded"])
            self.assertTrue(second_pet["rewarded"])
            self.assertEqual(first_pet["catId"], first.profile_id)
            self.assertEqual(second_pet["catId"], second.profile_id)


if __name__ == "__main__":
    unittest.main()
