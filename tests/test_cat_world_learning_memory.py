import json
import os
import unittest
from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.database import Base
from app.main import (
    cat_world_learning_memory_milestones,
    cat_world_learning_memory_payload,
    cat_world_learning_memory_payloads,
)
from app.models import CatWorldDailyLog


def learning_log(
    cat_id: str,
    log_date: date,
    milestones: list[str] | None = None,
    status_key: str = "",
    phone: str = "13900000000",
) -> CatWorldDailyLog:
    agent_state = {"learningCompanionAssigned": True}
    if milestones is not None:
        agent_state["learningCompanionMilestones"] = milestones
    if status_key:
        agent_state["learningCompanionStatusKey"] = status_key
    return CatWorldDailyLog(
        phone=phone,
        log_date=log_date,
        cat_id=cat_id,
        agent_state=json.dumps(agent_state, ensure_ascii=False),
    )


class CatWorldLearningMemoryTest(unittest.TestCase):
    def test_learning_memory_only_counts_days_with_real_learning_milestones(self):
        payload = cat_world_learning_memory_payload(
            [
                learning_log("cat-a", date(2026, 9, 4), []),
                learning_log("cat-a", date(2026, 9, 5), ["started"]),
                learning_log(
                    "cat-a",
                    date(2026, 9, 6),
                    ["started", "warmup", "output", "loop"],
                ),
                learning_log("cat-a", date(2026, 9, 7), ["output"]),
            ]
        )

        self.assertTrue(payload["hasMemory"])
        self.assertEqual(payload["companionDays"], 3)
        self.assertEqual(payload["startedDays"], 2)
        self.assertEqual(payload["warmupDays"], 1)
        self.assertEqual(payload["outputDays"], 2)
        self.assertEqual(payload["loopDays"], 1)
        self.assertEqual(payload["memoryPoints"], 4)
        self.assertEqual(payload["levelKey"], "familiar")
        self.assertEqual(payload["levelLabel"], "熟悉节奏")
        self.assertEqual(payload["nextRemaining"], 6)
        self.assertEqual(payload["firstDate"], "2026-09-05")
        self.assertEqual(payload["latestDate"], "2026-09-07")

    def test_legacy_companion_status_restores_equivalent_milestones(self):
        self.assertEqual(
            cat_world_learning_memory_milestones(
                {"learningCompanionStatusKey": "warmup"}
            ),
            {"started", "warmup"},
        )
        payload = cat_world_learning_memory_payload(
            [learning_log("cat-a", date(2026, 9, 6), None, "loop")]
        )

        self.assertEqual(payload["companionDays"], 1)
        self.assertEqual(payload["loopDays"], 1)
        self.assertEqual(payload["memoryPoints"], 2)

    def test_learning_memories_are_grouped_by_cat_and_account(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            db.add_all(
                [
                    learning_log("cat-a", date(2026, 9, 6), ["started"]),
                    learning_log("cat-a", date(2026, 9, 7), ["output"]),
                    learning_log("cat-b", date(2026, 9, 7), ["started", "warmup"]),
                    learning_log(
                        "cat-a",
                        date(2026, 9, 7),
                        ["started", "warmup", "output", "loop"],
                        phone="13800000000",
                    ),
                ]
            )
            db.commit()

            payloads = cat_world_learning_memory_payloads(
                db,
                "13900000000",
                {"cat-a", "cat-b", "cat-empty"},
            )

        self.assertEqual(payloads["cat-a"]["companionDays"], 2)
        self.assertEqual(payloads["cat-a"]["loopDays"], 0)
        self.assertEqual(payloads["cat-b"]["warmupDays"], 1)
        self.assertFalse(payloads["cat-empty"]["hasMemory"])


if __name__ == "__main__":
    unittest.main()
