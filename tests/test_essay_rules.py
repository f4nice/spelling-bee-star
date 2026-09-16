import json
import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app import main as m
from app.database import Base
from app.models import EssayEntry


def body(words):
    return " ".join(["word"] * words)


def assessment(essay, score=80):
    essay.writing_score = score
    essay.writing_score_breakdown = json.dumps({**dict.fromkeys(m.ESSAY_SCORE_KEYS, score), "_scale": 100})


class EssayRulesTest(unittest.TestCase):
    def test_minimum_is_100_english_words_and_type_cannot_be_downgraded(self):
        for kind in ["gaokao", "pet"]:
            essay = EssayEntry(title="", body="", phone="test")
            with self.assertRaisesRegex(HTTPException, "100"):
                m.apply_essay_payload(essay, {"body": body(99) + " 中文 123", "essayType": kind})
            m.apply_essay_payload(essay, {"body": body(100), "essayType": kind})
            self.assertEqual(essay.essay_type, kind)
            self.assertEqual(essay.energy_limit, 500)
            essay.id = 1
            with self.assertRaises(HTTPException):
                m.apply_essay_payload(essay, {"body": body(10), "essayType": "free"})
            with self.assertRaises(HTTPException):
                m.apply_essay_payload(essay, {"body": body(99)})

    def test_short_and_long_essay_energy_boundaries(self):
        for words, limit, points in [(1, 200, 160), (49, 200, 160), (50, 200, 160), (51, 200, 160), (99, 200, 160), (100, 500, 400), (101, 500, 400)]:
            with self.subTest(words=words):
                essay = EssayEntry(title="", body="", phone="test")
                m.apply_essay_payload(essay, {"body": body(words)})
                assessment(essay)
                serialized = m.serialize_essay(essay)
                self.assertEqual(serialized["energyLimit"], limit)
                self.assertEqual(serialized["writingPoints"], points)
                self.assertEqual(serialized["wordCount"], words)

    def test_only_improvement_is_rewarded_and_shortening_never_deducts(self):
        essay = EssayEntry(title="", body="", phone="test")
        m.apply_essay_payload(essay, {"body": body(50)})
        assessment(essay)
        reward = lambda: m.award_essay_writing_improvement(essay, writing_score=80, writing_points=m.current_essay_writing_points(essay), eligible=True)
        self.assertEqual(reward(), 160)
        self.assertEqual(reward(), 0)
        essay.id = 1
        m.apply_essay_payload(essay, {"body": body(100)}, clear_generated_on_change=True)
        assessment(essay)
        self.assertEqual(reward(), 240)
        m.apply_essay_payload(essay, {"body": body(30)}, clear_generated_on_change=True)
        assessment(essay)
        self.assertEqual(reward(), 0)
        self.assertEqual(essay.best_writing_points, 400)

    def test_legacy_earned_energy_is_preserved_when_new_rules_apply(self):
        essay = EssayEntry(id=1, title="Old", body=body(30), phone="test", energy_limit=500)
        assessment(essay)
        m.apply_essay_payload(essay, {"title": "Old", "body": body(30)})
        self.assertEqual(essay.energy_limit, 200)
        self.assertEqual(essay.best_writing_points, 400)

    def test_cat_wallet_uses_scaled_points_and_saved_best(self):
        engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            essay = EssayEntry(phone="test", title="Short", body=body(40), energy_limit=200)
            assessment(essay)
            db.add(essay)
            db.commit()
            self.assertEqual(m.cat_world_essay_energy_source(db, "test")["energy"], 160)
            essay.best_writing_points = 400
            db.commit()
            self.assertEqual(m.cat_world_essay_energy_source(db, "test")["energy"], 400)
        engine.dispose()

    def test_word_count_handles_apostrophes_accents_and_ignores_chinese_numbers(self):
        self.assertEqual(m.essay_word_count("I'm well-known. Don’t café cafe\u0301 中文 123"), 5)


if __name__ == "__main__":
    unittest.main()
