import os
import unittest
from datetime import date, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.database import Base
from app.main import (
    DIARY_MIN_WORDS,
    DIARY_REWARD_MINUTES,
    award_diary_play_time,
    cat_world_play_time_reward_source,
    diary_english_word_count,
    parse_diary_guidance_result,
    save_daily_diary,
)
from app.models import CatWorldPlayTimeGrant, DiaryEntry


class DiaryTest(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        self.engine.dispose()

    def test_diary_counts_only_english_words(self):
        self.assertEqual(diary_english_word_count("Today I'm happy. 今天很好。 2026"), 3)
        self.assertEqual(diary_english_word_count("well-written can't stop"), 3)

    def test_guidance_parser_accepts_structured_json_fence(self):
        guidance = parse_diary_guidance_result(
            """```json
            {
              "score": 88,
              "overall": "内容真诚，时间顺序清楚。",
              "strengths": ["具体写出了放学后的感受。"],
              "suggestions": [
                {"title": "补充连接词", "guidance": "用 because 说明原因。", "example": "I smiled because I felt proud."}
              ],
              "corrections": [
                {"original": "I am go home.", "better": "I went home.", "reason": "日记讲过去的事情时使用过去时。"}
              ],
              "nextFocus": "下一篇可以多写一个声音或动作细节。"
            }
            ```"""
        )

        self.assertEqual(guidance["score"], 88)
        self.assertEqual(guidance["suggestions"][0]["example"], "I smiled because I felt proud.")
        self.assertEqual(guidance["corrections"][0]["better"], "I went home.")

    def test_daily_diary_reward_is_granted_only_once(self):
        diary_date = date(2026, 8, 16)
        phone = "13900000000"
        body = " ".join(f"word{index}" for index in range(DIARY_MIN_WORDS))
        with Session(self.engine) as db:
            entry = save_daily_diary(
                db,
                phone,
                {"title": "A Busy Sunday", "body": body},
                diary_date,
            )
            entry.completed_at = datetime(2026, 8, 16, 20, 0)
            self.assertEqual(entry.word_count, DIARY_MIN_WORDS)
            self.assertTrue(award_diary_play_time(db, entry, datetime(2026, 8, 16, 20, 1)))
            self.assertFalse(award_diary_play_time(db, entry, datetime(2026, 8, 16, 20, 2)))
            db.commit()

            reward = cat_world_play_time_reward_source(db, phone, diary_date)
            grants = db.scalars(select(CatWorldPlayTimeGrant)).all()
            saved = db.scalar(select(DiaryEntry))

            self.assertEqual(reward["minutes"], DIARY_REWARD_MINUTES)
            self.assertEqual(reward["grantCount"], 1)
            self.assertEqual(len(grants), 1)
            self.assertIsNotNone(saved.rewarded_at)

    def test_editing_completed_diary_clears_feedback_but_keeps_reward(self):
        diary_date = date(2026, 8, 16)
        with Session(self.engine) as db:
            entry = save_daily_diary(
                db,
                "13700000000",
                {"title": "Today", "body": "One short draft."},
                diary_date,
            )
            entry.ai_guidance = '{"overall":"旧意见"}'
            entry.ai_model = "test:model"
            entry.completed_at = datetime(2026, 8, 16, 18, 0)
            entry.rewarded_at = datetime(2026, 8, 16, 18, 1)
            db.commit()

            updated = save_daily_diary(
                db,
                "13700000000",
                {"title": "Today", "body": "A revised diary entry."},
                diary_date,
            )

            self.assertIsNone(updated.ai_guidance)
            self.assertIsNone(updated.ai_model)
            self.assertIsNone(updated.completed_at)
            self.assertIsNotNone(updated.rewarded_at)


if __name__ == "__main__":
    unittest.main()
