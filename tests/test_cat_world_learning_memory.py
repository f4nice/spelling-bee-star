import json
import os
import unittest
from datetime import date, datetime

from fastapi import HTTPException
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
    cat_world_learning_memory_review_error,
    cat_world_normalize_learning_memory_recall,
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


def review_log(
    cat_id: str,
    log_date: date,
    source_date: date,
    phone: str = "13900000000",
    recalled_word: str = "",
    recalled_sentence: str = "",
) -> CatWorldDailyLog:
    review = {
        "sourceDate": source_date.isoformat(),
        "reviewedAt": f"{log_date.isoformat()}T08:00:00Z",
    }
    if recalled_word:
        review["recalledWord"] = recalled_word
    if recalled_sentence:
        review["recalledSentence"] = recalled_sentence
    return CatWorldDailyLog(
        phone=phone,
        log_date=log_date,
        cat_id=cat_id,
        agent_state=json.dumps(
            {
                "learningMemoryReview": review
            },
            ensure_ascii=False,
        ),
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
                    review_log(
                        "cat-a",
                        date(2026, 9, 5),
                        date(2026, 9, 4),
                        recalled_word="steady",
                        recalled_sentence="I can make steady progress.",
                    ),
                    review_log(
                        "cat-b",
                        date(2026, 9, 6),
                        date(2026, 9, 5),
                        recalled_word="brave",
                        recalled_sentence="I can be brave today.",
                    ),
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
        self.assertEqual(payloads["cat-a"]["recallTreasures"][0]["word"], "steady")
        self.assertEqual(payloads["cat-b"]["recallTreasures"][0]["word"], "brave")
        self.assertNotEqual(
            payloads["cat-a"]["recallTreasures"],
            payloads["cat-b"]["recallTreasures"],
        )
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
                    "recalledWord": "steady",
                    "recalledSentence": "I can make steady progress.",
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
        self.assertEqual(payload["todayRecallWord"], "steady")
        self.assertEqual(payload["todayRecallSentence"], "I can make steady progress.")
        self.assertEqual(payload["todayReviewSourceDate"], "2026-09-06")
        self.assertEqual(payload["lastReviewDate"], "2026-09-07")
        self.assertEqual(payload["recentDays"][0]["latestRecallWord"], "steady")
        self.assertEqual(
            payload["recentDays"][0]["latestRecallSentence"],
            "I can make steady progress.",
        )

    def test_review_requires_one_english_word_and_a_real_short_sentence(self):
        self.assertEqual(
            cat_world_normalize_learning_memory_recall(
                "  resilient  ",
                "  I   can stay resilient.  ",
            ),
            ("resilient", "I can stay resilient."),
        )
        self.assertEqual(
            cat_world_normalize_learning_memory_recall(
                "don't",
                "I don't give up.",
            ),
            ("don't", "I don't give up."),
        )
        for word, sentence in (
            ("", "I keep learning."),
            ("两个词", "I keep learning."),
            ("two words", "I keep learning."),
            ("steady", "Too short"),
            ("steady", ""),
            ("steady", "word " * 61),
        ):
            with self.subTest(word=word, sentence=sentence):
                with self.assertRaises(HTTPException):
                    cat_world_normalize_learning_memory_recall(word, sentence)

    def test_recalled_words_become_deduplicated_cat_treasures(self):
        payload = cat_world_learning_memory_payload(
            [
                learning_log("cat-a", date(2026, 9, 1), ["started", "warmup"]),
                review_log(
                    "cat-a",
                    date(2026, 9, 2),
                    date(2026, 9, 1),
                    recalled_word="Steady",
                    recalled_sentence="I can make steady progress.",
                ),
                review_log(
                    "cat-a",
                    date(2026, 9, 5),
                    date(2026, 9, 1),
                    recalled_word="steady",
                    recalled_sentence="I study English at a steady pace.",
                ),
                review_log(
                    "cat-a",
                    date(2026, 9, 6),
                    date(2026, 9, 4),
                    recalled_word="resilient",
                    recalled_sentence="I can stay resilient every day.",
                ),
                review_log("cat-a", date(2026, 9, 7), date(2026, 9, 6)),
            ],
            today=date(2026, 9, 7),
        )

        self.assertEqual(payload["reviewCount"], 4)
        self.assertEqual(payload["recallTreasureCount"], 2)
        self.assertEqual(
            [treasure["word"] for treasure in payload["recallTreasures"]],
            ["resilient", "steady"],
        )
        steady = payload["recallTreasures"][1]
        self.assertEqual(steady["key"], "steady")
        self.assertEqual(steady["reviewCount"], 2)
        self.assertEqual(steady["reviewDate"], "2026-09-05")
        self.assertEqual(steady["sentence"], "I study English at a steady pace.")

    def test_learning_pages_offer_one_humane_review_when_the_next_day_arrives(self):
        payload = cat_world_learning_memory_payload(
            [
                learning_log("cat-a", date(2026, 9, 6), ["started", "warmup"]),
                learning_log("cat-a", date(2026, 9, 7), ["output"]),
            ],
            today=date(2026, 9, 7),
        )
        days = {day["date"]: day for day in payload["recentDays"]}

        self.assertTrue(payload["reviewDueToday"])
        self.assertEqual(payload["suggestedReviewDate"], "2026-09-06")
        self.assertEqual(payload["suggestedReviewStageLabel"], "隔日回想")
        self.assertTrue(days["2026-09-06"]["reviewDue"])
        self.assertEqual(days["2026-09-06"]["reviewStageKey"], "first")
        self.assertEqual(days["2026-09-06"]["reviewProgressLabel"], "0/2")
        self.assertEqual(days["2026-09-06"]["nextReviewDate"], "2026-09-07")
        self.assertFalse(days["2026-09-07"]["reviewDue"])

    def test_second_review_waits_three_days_then_settles_the_page(self):
        source = learning_log("cat-a", date(2026, 9, 5), ["started", "warmup", "output", "loop"])
        first_review = review_log("cat-a", date(2026, 9, 6), date(2026, 9, 5))

        waiting = cat_world_learning_memory_payload(
            [source, first_review],
            today=date(2026, 9, 8),
        )
        waiting_day = waiting["recentDays"][0]
        self.assertFalse(waiting["reviewDueToday"])
        self.assertEqual(waiting["nextReviewDate"], "2026-09-09")
        self.assertEqual(waiting_day["reviewStageKey"], "strengthen")
        self.assertEqual(waiting_day["reviewProgressLabel"], "1/2")

        due = cat_world_learning_memory_payload(
            [source, first_review],
            today=date(2026, 9, 9),
        )
        self.assertTrue(due["reviewDueToday"])
        self.assertEqual(due["suggestedReviewDate"], "2026-09-05")
        self.assertEqual(due["suggestedReviewStageLabel"], "三日巩固")

        settled = cat_world_learning_memory_payload(
            [source, first_review, review_log("cat-a", date(2026, 9, 9), date(2026, 9, 5))],
            today=date(2026, 9, 9),
        )
        settled_day = settled["recentDays"][0]
        self.assertTrue(settled["reviewedToday"])
        self.assertFalse(settled["reviewDueToday"])
        self.assertEqual(settled_day["reviewStageKey"], "settled")
        self.assertEqual(settled_day["reviewProgressLabel"], "2/2")
        self.assertEqual(settled_day["nextReviewDate"], "")
        self.assertEqual(
            cat_world_learning_memory_review_error(settled, date(2026, 9, 5)),
            "",
        )

        next_day = cat_world_learning_memory_payload(
            [source, first_review, review_log("cat-a", date(2026, 9, 9), date(2026, 9, 5))],
            today=date(2026, 9, 10),
        )
        self.assertIn(
            "已经完成隔日回想和三日巩固",
            cat_world_learning_memory_review_error(next_day, date(2026, 9, 5)),
        )
        self.assertIn(
            "还不存在",
            cat_world_learning_memory_review_error(next_day, date(2026, 9, 4)),
        )

    def test_due_page_stays_visible_when_it_is_older_than_the_recent_six(self):
        learning_days = [
            learning_log("cat-a", date(2026, 8, day), ["started", "warmup"])
            for day in range(1, 9)
        ]
        review_days = []
        review_date = 9
        for source_day in range(3, 9):
            review_days.append(review_log("cat-a", date(2026, 8, review_date), date(2026, 8, source_day)))
            review_days.append(review_log("cat-a", date(2026, 8, review_date + 1), date(2026, 8, source_day)))
            review_date += 2

        payload = cat_world_learning_memory_payload(
            [*learning_days, *review_days],
            today=date(2026, 8, 21),
        )
        visible_dates = [day["date"] for day in payload["recentDays"]]

        self.assertEqual(len(visible_dates), 6)
        self.assertEqual(payload["suggestedReviewDate"], "2026-08-02")
        self.assertIn("2026-08-02", visible_dates)
        self.assertNotIn("2026-08-03", visible_dates)

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
            "resilient",
            "I can stay resilient.",
            now=now,
        )
        repeated = cat_world_apply_learning_memory_review(
            log,
            cat,
            traits,
            date(2026, 9, 5),
            "patient",
            "I can remain patient.",
            now=now,
        )
        agent_state = parse_cat_world_agent_state(log.agent_state)

        self.assertTrue(first["recorded"])
        self.assertFalse(repeated["recorded"])
        self.assertEqual(repeated["sourceDate"], "2026-09-06")
        self.assertEqual(first["recalledWord"], "resilient")
        self.assertEqual(agent_state["learningMemoryReview"]["recalledWord"], "resilient")
        self.assertEqual(
            agent_state["learningMemoryReview"]["recalledSentence"],
            "I can stay resilient.",
        )
        self.assertIn("resilient", first["message"])
        self.assertEqual(log.mood_score, 63)
        self.assertEqual(log.energy_score, 57)
        self.assertEqual(
            len([event for event in agent_state["events"] if event["kind"] == "learning-review"]),
            1,
        )


if __name__ == "__main__":
    unittest.main()
