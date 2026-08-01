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
    cat_world_operating_energy_source,
    cat_world_today_energy_source_rows,
)
from app.models import CatWorldEnergyGrant


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


if __name__ == "__main__":
    unittest.main()
