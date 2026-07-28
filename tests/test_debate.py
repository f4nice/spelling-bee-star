import json
import unittest
from datetime import date, timedelta

from app.services.debate import (
    DEBATE_MAX_TURNS,
    DEBATE_TARGET_POINTS,
    debate_energy_reward,
    debate_result_status,
    debate_topic_for_day,
    debate_turn_messages,
    parse_debate_turn_result,
)


class DebateServiceTests(unittest.TestCase):
    def test_daily_topic_is_stable_for_each_level(self):
        debate_day = date(2026, 7, 28)

        primary = debate_topic_for_day(debate_day, "primary")
        primary_again = debate_topic_for_day(debate_day, "primary")
        middle = debate_topic_for_day(debate_day, "middle")

        self.assertEqual(primary, primary_again)
        self.assertNotEqual(primary["key"], middle["key"])
        self.assertTrue(primary["title"])
        self.assertEqual(len(primary["hints"]), 2)
        self.assertRegex(primary["title"], r"[A-Za-z]{3}")
        self.assertNotRegex(primary["title"], r"[\u4e00-\u9fff]")

    def test_topic_selection_accepts_future_dates(self):
        topic = debate_topic_for_day(date.today() + timedelta(days=30), "middle")

        self.assertIn("key", topic)
        self.assertIn("category", topic)

    def test_result_finishes_at_target_or_turn_limit(self):
        self.assertEqual(debate_result_status(99, 80, 5), "active")
        self.assertEqual(
            debate_result_status(DEBATE_TARGET_POINTS, 94, 4),
            "won",
        )
        self.assertEqual(
            debate_result_status(88, 91, DEBATE_MAX_TURNS),
            "lost",
        )
        self.assertEqual(
            debate_result_status(90, 90, DEBATE_MAX_TURNS),
            "draw",
        )

    def test_parser_normalizes_points_dimensions_and_review(self):
        source = {
            "aiReply": "I understand your reason, but we should also consider whether students have enough free time.",
            "userPoints": 30,
            "aiPoints": 22,
            "userDimensions": {
                "claim": 7,
                "reason": 6,
                "evidence": 5,
                "rebuttal": 4,
            },
            "coachNote": "例子很具体，再回应对方的担心会更有说服力。",
            "highlight": "具体例子",
            "finalReview": {
                "overallScore": 86,
                "summary": "观点明确，例子贴近生活。",
                "strengths": ["观点清楚", "例子具体"],
                "improvements": [
                    {
                        "title": "补上反驳",
                        "advice": "先承认对方合理的一点，再说明你的条件。",
                        "example": "虽然时间有限，但每天十分钟也能培养习惯。",
                    }
                ],
                "nextChallenge": "下一场重点练习回应对方。",
            },
        }

        result = parse_debate_turn_result(json.dumps(source, ensure_ascii=False))

        self.assertEqual(result["userPoints"], 22)
        self.assertEqual(result["aiPoints"], 22)
        self.assertEqual(result["finalReview"]["overallScore"], 86)
        self.assertEqual(result["finalReview"]["improvements"][0]["title"], "补上反驳")

    def test_prompt_requires_english_debate_and_chinese_coaching(self):
        messages = debate_turn_messages(
            level="primary",
            topic="Should children do chores every day?",
            user_stance="pro",
            ai_stance="con",
            user_points=0,
            ai_points=0,
            turn_count=0,
            argument="Chores teach children to be responsible.",
            transcript=[],
        )

        system_prompt = messages[0]["content"]
        self.assertIn("AI debate reply and highlight must be in English", system_prompt)
        self.assertIn("must be in Simplified Chinese", system_prompt)

    def test_reward_has_participation_floor_and_result_bonus(self):
        self.assertEqual(debate_energy_reward(0, "lost"), 20)
        self.assertEqual(debate_energy_reward(80, "draw"), 90)
        self.assertEqual(debate_energy_reward(100, "won"), 120)


if __name__ == "__main__":
    unittest.main()
