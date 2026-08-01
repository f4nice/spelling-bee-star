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
    cat_world_apply_pet_effect,
    cat_world_cat_profile_payload,
    cat_world_consume_rename_card,
    cat_world_normalize_nickname,
    create_cat_world_cat_profile,
    encode_cat_world_bonds,
    encode_cat_world_care,
    encode_cat_world_cats,
    ensure_cat_world_agent_state,
    ensure_cat_world_cat_profiles,
    get_or_create_cat_world_daily_log,
    parse_cat_world_bonds,
)
from app.models import CatWorldDailyLog, CatWorldState


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CatWorldIndividualProfileTest(unittest.TestCase):
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
            db.flush()

            first_cat = cat_world_cat_profile_payload(first)
            second_cat = cat_world_cat_profile_payload(second)
            self.assertNotEqual(first.profile_id, second.profile_id)
            self.assertNotEqual(first.personality_key, second.personality_key)
            self.assertEqual(first_cat["traits"]["personalityModel"], 2)
            self.assertEqual(second_cat["traits"]["personalityModel"], 2)
            self.assertNotEqual(first_cat["traits"], second_cat["traits"])

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
