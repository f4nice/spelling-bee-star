import json
import os
import unittest
from datetime import date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.database import Base
from app.main import (
    CAT_WORLD_CAT_BY_ID,
    CAT_WORLD_DEFAULT_CAT_ID,
    cat_world_apply_learning_memory_review,
    cat_world_cat_payload,
    cat_world_cat_traits,
    cat_world_learning_memory_milestones,
    cat_world_learning_memory_payload,
    cat_world_learning_memory_payloads,
    parse_cat_world_agent_state,
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
        self.assertEqual(
            [stage["key"] for stage in payload["stages"] if stage["unlocked"]],
            ["starter", "familiar"],
        )
        self.assertEqual(payload["recentDays"][0]["date"], "2026-09-07")
        self.assertEqual(payload["recentDays"][0]["statusKey"], "output")
        self.assertEqual(payload["recentDays"][1]["statusKey"], "loop")
        self.assertEqual(payload["recentDays"][2]["statusLabel"], "点亮 5 词起步")

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
        self.assertEqual(payload["recentDays"][0]["statusKey"], "loop")

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
        self.assertEqual(payloads["cat-empty"]["recentDays"], [])
        self.assertFalse(any(stage["unlocked"] for stage in payloads["cat-empty"]["stages"]))

    def test_review_is_tracked_without_inflating_memory_points(self):
        first_day = learning_log("cat-a", date(2026, 9, 6), ["started", "warmup"])
        review_day = learning_log("cat-a", date(2026, 9, 7), [])
        review_day.agent_state = json.dumps(
            {
                "learningMemoryReview": {
                    "sourceDate": "2026-09-06",
                    "reviewedAt": "2026-09-07T08:00:00Z",
                }
            },
            ensure_ascii=False,
        )

        payload = cat_world_learning_memory_payload(
            [first_day, review_day],
            today=date(2026, 9, 7),
        )

        self.assertEqual(payload["companionDays"], 1)
        self.assertEqual(payload["memoryPoints"], 1)
        self.assertEqual(payload["reviewCount"], 1)
        self.assertTrue(payload["reviewedToday"])
        self.assertEqual(payload["todayReviewSourceDate"], "2026-09-06")
        self.assertEqual(payload["lastReviewDate"], "2026-09-07")

    def test_daily_review_is_idempotent_and_does_not_change_cat_scores(self):
        cat = cat_world_cat_payload(CAT_WORLD_CAT_BY_ID[CAT_WORLD_DEFAULT_CAT_ID])
        traits = cat_world_cat_traits(cat)
        log = CatWorldDailyLog(
            phone="13900000000",
            log_date=date(2026, 9, 7),
            cat_id=cat["id"],
            mood_score=63,
            energy_score=57,
        )
        now = datetime(2026, 9, 7, 8, 30)

        first = cat_world_apply_learning_memory_review(
            log,
            cat,
            traits,
            date(2026, 9, 6),
            now,
        )
        repeated = cat_world_apply_learning_memory_review(
            log,
            cat,
            traits,
            date(2026, 9, 5),
            now,
        )
        agent_state = parse_cat_world_agent_state(log.agent_state)

        self.assertTrue(first["recorded"])
        self.assertFalse(repeated["recorded"])
        self.assertEqual(repeated["sourceDate"], "2026-09-06")
        self.assertEqual(log.mood_score, 63)
        self.assertEqual(log.energy_score, 57)
        self.assertEqual(
            len([event for event in agent_state["events"] if event["kind"] == "learning-review"]),
            1,
        )


if __name__ == "__main__":
    unittest.main()
