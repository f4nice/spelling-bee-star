import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import main as m
from app.database import Base
from app.models import ChallengeProgress, Word, WordList, WordListItem


class ChallengeSubmissionPerformanceTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine, expire_on_commit=False)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.db.close)

        self.word_list = WordList(name="large challenge")
        words = [Word(word=f"word-{index}") for index in range(400)]
        self.db.add(self.word_list)
        self.db.add_all(words)
        self.db.flush()
        self.db.add_all(
            [WordListItem(word_list_id=self.word_list.id, word_id=word.id) for word in words]
        )
        self.db.add(ChallengeProgress(word_list_id=self.word_list.id, current_index=200))
        self.db.commit()
        self.current_word = words[200]
        self.next_word = words[201]

    def test_indexed_word_queries_preserve_challenge_order(self):
        self.assertEqual(
            m.challenge_word_count(self.db, self.word_list.id),
            400,
        )
        self.assertEqual(
            m.challenge_word_at_index(self.db, self.word_list.id, 200).id,
            self.current_word.id,
        )
        word, position = m.challenge_word_and_position(
            self.db,
            self.word_list.id,
            self.current_word.id,
        )
        self.assertEqual(word.id, self.current_word.id)
        self.assertEqual(position, 200)

    def test_submission_uses_one_word_instead_of_loading_the_whole_list(self):
        with patch.object(m, "get_words_for_list", side_effect=AssertionError("full list loaded")):
            result = m.apply_challenge_answer(
                self.db,
                word_list_id=self.word_list.id,
                action="spell",
                daily_count=20,
                start_count=0,
                session_correct=0,
                session_wrong=0,
                spelling=self.current_word.word,
                answer_word_id=self.current_word.id,
                wrong_date="",
            )

            payload = m.challenge_payload(
                self.db,
                word_list_id=self.word_list.id,
                daily_count=result["daily_count"],
                start_count=result["start_count"],
                session_correct=result["session_correct"],
                session_wrong=result["session_wrong"],
                wrong_date=None,
                preloaded_current_word=result["next_word"],
            )

        self.assertEqual(result["answer"]["is_correct"], True)
        self.assertEqual(result["next_word"].id, self.next_word.id)
        self.assertEqual(payload["current_word"]["id"], self.next_word.id)
        self.assertEqual(payload["progress"]["current_index"], 201)

    def test_daily_completion_still_hides_the_next_word(self):
        result = m.apply_challenge_answer(
            self.db,
            word_list_id=self.word_list.id,
            action="spell",
            daily_count=1,
            start_count=0,
            session_correct=0,
            session_wrong=0,
            spelling=self.current_word.word,
            answer_word_id=self.current_word.id,
            wrong_date="",
        )

        payload = m.challenge_payload(
            self.db,
            word_list_id=self.word_list.id,
            daily_count=result["daily_count"],
            start_count=result["start_count"],
            session_correct=result["session_correct"],
            session_wrong=result["session_wrong"],
            wrong_date=None,
            preloaded_current_word=result["next_word"],
        )

        self.assertTrue(payload["today_challenge"]["is_complete"])
        self.assertIsNone(payload["current_word"])


if __name__ == "__main__":
    unittest.main()
