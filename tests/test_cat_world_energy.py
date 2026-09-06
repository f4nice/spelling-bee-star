import os
import unittest
from datetime import date, datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.database import Base
from app.main import (
    CAT_WORLD_DEBATE_ENERGY_GRANT_SOURCE,
    cat_world_debate_energy_source,
    cat_world_learning_habit_source,
    cat_world_operating_energy_source,
    cat_world_spelling_habit_energy,
    cat_world_today_energy_source_rows,
)
from app.models import CatWorldEnergyGrant, ChallengeDailyStat, EssayEntry


class CatWorldEnergyTest(unittest.TestCase):
    def test_debate_rewards_are_separate_from_operating_activity(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        today = date(2026, 8, 1)
        with Session(engine) as db:
            db.add_all(
                [
                    CatWorldEnergyGrant(
                        phone="13900000000",
                        amount=88,
                        reason="AI Debate 今日完成",
                        granted_by_phone=CAT_WORLD_DEBATE_ENERGY_GRANT_SOURCE,
                        created_at=datetime(2026, 8, 1, 10, 0),
                    ),
                    CatWorldEnergyGrant(
                        phone="13900000000",
                        amount=25,
                        reason="周末活动",
                        granted_by_phone="13911111111",
                        created_at=datetime(2026, 8, 1, 11, 0),
                    ),
                    CatWorldEnergyGrant(
                        phone="13900000000",
                        amount=60,
                        reason="昨日 Debate",
                        granted_by_phone=CAT_WORLD_DEBATE_ENERGY_GRANT_SOURCE,
                        created_at=datetime(2026, 8, 1, 0, 0) - timedelta(seconds=1),
                    ),
                ]
            )
            db.commit()

            debate = cat_world_debate_energy_source(db, "13900000000", today=today)
            operating = cat_world_operating_energy_source(db, "13900000000", today=today)

        self.assertEqual(debate["energy"], 148)
        self.assertEqual(debate["todayEnergy"], 88)
        self.assertEqual(operating["energy"], 25)
        self.assertEqual(operating["todayEnergy"], 25)

    def test_today_rows_only_keep_nonzero_daily_sources(self):
        rows = cat_world_today_energy_source_rows(
            {
                "scoreRules": [{"key": "spelling_words", "points": 2}],
                "dailyMissions": [{"key": "today_spelling", "value": 12}],
            },
            {"key": "essay_scores", "label": "作文五项积分", "todayEnergy": 0},
            {
                "key": "ai_debate",
                "label": "AI Debate",
                "unit": "能量",
                "energyPerUnit": 1,
                "todayValue": 88,
                "todayEnergy": 88,
                "todayDetail": "AI Debate 今日完成",
            },
            {"key": "operating_activity", "label": "运营活动", "todayEnergy": 0},
        )

        self.assertEqual([row["key"] for row in rows], ["spelling_words", "ai_debate"])
        self.assertEqual([row["energy"] for row in rows], [24, 88])

    def test_spelling_habit_energy_uses_gentle_milestones(self):
        self.assertEqual(cat_world_spelling_habit_energy(19), 0)
        self.assertEqual(cat_world_spelling_habit_energy(20), 10)
        self.assertEqual(cat_world_spelling_habit_energy(50), 25)
        self.assertEqual(cat_world_spelling_habit_energy(100), 45)
        self.assertEqual(cat_world_spelling_habit_energy(200), 65)

    def test_habit_reward_values_consistency_and_mixed_learning(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all(
                [
                    ChallengeDailyStat(stat_date=date(2026, 9, 6), correct_count=20, wrong_count=0),
                    ChallengeDailyStat(stat_date=date(2026, 9, 7), correct_count=45, wrong_count=5),
                    EssayEntry(
                        phone="13900000000",
                        title="A useful habit",
                        body="word " * 80,
                        word_count=80,
                        created_at=datetime(2026, 9, 7, 10, 0),
                    ),
                    CatWorldEnergyGrant(
                        phone="13900000000",
                        amount=88,
                        reason="AI Debate 今日完成",
                        granted_by_phone=CAT_WORLD_DEBATE_ENERGY_GRANT_SOURCE,
                        created_at=datetime(2026, 9, 7, 11, 0),
                    ),
                ]
            )
            db.commit()

            source = cat_world_learning_habit_source(db, "13900000000", today=date(2026, 9, 7))

        self.assertEqual(source["todayEnergy"], 80)
        self.assertEqual(source["energy"], 90)
        self.assertEqual(source["currentStreak"], 2)
        self.assertEqual(source["totalActiveDays"], 2)
        self.assertEqual(source["totalLoopDays"], 1)
        self.assertEqual(source["bestStreak"], 2)
        self.assertTrue(source["todayHasEssay"])
        self.assertTrue(source["todayHasDebate"])
        self.assertTrue(source["todayBalanceComplete"])
        self.assertEqual(source["nextAction"], "再完成 50 词，习惯奖励再 +20")
        self.assertIn("输入输出组合 +20", source["todayDetail"])
        self.assertEqual(len(source["recentDays"]), 7)
        self.assertEqual(source["recentDays"][-2]["statusKey"], "input")
        self.assertEqual(source["recentDays"][-1]["statusKey"], "loop")
        self.assertTrue(source["recentDays"][-1]["today"])

    def test_habit_rhythm_bonus_survives_one_intentional_rest_day(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all(
                [
                    ChallengeDailyStat(stat_date=date(2026, 9, 6), correct_count=20, wrong_count=0),
                    ChallengeDailyStat(stat_date=date(2026, 9, 8), correct_count=20, wrong_count=0),
                    EssayEntry(
                        phone="13900000000",
                        title="A calm return",
                        body="word " * 80,
                        word_count=80,
                        created_at=datetime(2026, 9, 8, 10, 0),
                    ),
                ]
            )
            db.commit()

            source = cat_world_learning_habit_source(db, "13900000000", today=date(2026, 9, 8))

        self.assertEqual(source["currentStreak"], 1)
        self.assertEqual(source["todayEnergy"], 50)
        self.assertEqual(source["energy"], 60)
        self.assertIn("近 7 日节奏 2 天 +5", source["todayDetail"])
        self.assertEqual(source["recentDays"][-3]["statusKey"], "input")
        self.assertEqual(source["recentDays"][-2]["statusKey"], "rest")
        self.assertEqual(source["recentDays"][-1]["statusKey"], "loop")

    def test_five_word_touchpoint_supports_rhythm_without_granting_base_energy(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all(
                [
                    ChallengeDailyStat(stat_date=date(2026, 9, 6), correct_count=20, wrong_count=0),
                    ChallengeDailyStat(stat_date=date(2026, 9, 7), correct_count=5, wrong_count=0),
                    ChallengeDailyStat(stat_date=date(2026, 9, 8), correct_count=20, wrong_count=0),
                ]
            )
            db.commit()

            source = cat_world_learning_habit_source(db, "13900000000", today=date(2026, 9, 8))

        self.assertEqual(source["todayEnergy"], 20)
        self.assertEqual(source["energy"], 30)
        self.assertEqual(source["totalActiveDays"], 3)
        self.assertIn("近 7 日节奏 3 天 +10", source["todayDetail"])
        self.assertEqual(source["recentDays"][-2]["statusKey"], "started")
        self.assertTrue(source["recentDays"][-2]["active"])


if __name__ == "__main__":
    unittest.main()
