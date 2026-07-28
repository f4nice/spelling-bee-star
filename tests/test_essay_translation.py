import os
import unittest


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from app.main import apply_essay_payload, parse_essay_translation_result
from app.models import EssayEntry


class EssayTranslationTest(unittest.TestCase):
    def test_parses_draft_and_optimized_translation_from_json_fence(self):
        draft, optimized = parse_essay_translation_result(
            """```json
            {"draft":"这是原稿。","optimized":"这是优化稿。"}
            ```""",
            require_optimized=True,
        )

        self.assertEqual(draft, "这是原稿。")
        self.assertEqual(optimized, "这是优化稿。")

    def test_requires_optimized_translation_when_ai_version_exists(self):
        with self.assertRaisesRegex(RuntimeError, "优化稿"):
            parse_essay_translation_result(
                '{"draft":"这是原稿。","optimized":""}',
                require_optimized=True,
            )

    def test_content_change_clears_saved_translations(self):
        essay = EssayEntry(
            id=7,
            phone="13900000000",
            title="Old title",
            body="Old body.",
            optimized_body="Polished body.",
            translation_body="旧原稿译文。",
            optimized_translation_body="旧优化稿译文。",
            translation_model="dashscope:qwen-plus",
        )

        changed = apply_essay_payload(
            essay,
            {"title": "New title", "body": "New body."},
            clear_generated_on_change=True,
        )

        self.assertTrue(changed)
        self.assertIsNone(essay.translation_body)
        self.assertIsNone(essay.optimized_translation_body)
        self.assertIsNone(essay.translation_model)


if __name__ == "__main__":
    unittest.main()
