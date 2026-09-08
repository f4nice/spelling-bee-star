import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.services import ai_image_generation


class PredictableTextDraw:
    def textbbox(self, _position, label, *, font, stroke_width):
        glyph_width = 1.05 if set(label) == {"W"} else 1.0
        width = round(len(label) * font.size * glyph_width) + stroke_width * 2
        return (0, 0, width, font.size + stroke_width * 2)


class WordImageLabelTests(unittest.TestCase):
    @staticmethod
    def scalable_font(size: int):
        return SimpleNamespace(size=size)

    def test_short_label_uses_large_card_font(self):
        draw = PredictableTextDraw()

        with patch.object(ai_image_generation, "chinese_label_font", side_effect=self.scalable_font):
            font, text_box = ai_image_generation.fit_chinese_label_font(draw, "含水的")

        self.assertEqual(font.size, ai_image_generation.WORD_LABEL_MAX_FONT_SIZE)
        self.assertLessEqual(text_box[2] - text_box[0], ai_image_generation.WORD_LABEL_MAX_WIDTH)

    def test_bundled_font_contains_distinct_chinese_glyphs(self):
        self.assertTrue(ai_image_generation.BUNDLED_CHINESE_FONT.is_file())

        font = ai_image_generation.chinese_label_font(96)

        self.assertEqual(font.size, 96)
        self.assertNotEqual(bytes(font.getmask("含")), bytes(font.getmask("水")))

    def test_wide_label_shrinks_without_becoming_tiny(self):
        draw = PredictableTextDraw()

        with patch.object(ai_image_generation, "chinese_label_font", side_effect=self.scalable_font):
            font, text_box = ai_image_generation.fit_chinese_label_font(draw, "WWWWWWWW")

        self.assertLess(font.size, ai_image_generation.WORD_LABEL_MAX_FONT_SIZE)
        self.assertGreaterEqual(font.size, ai_image_generation.WORD_LABEL_MIN_FONT_SIZE)
        self.assertLessEqual(text_box[2] - text_box[0], ai_image_generation.WORD_LABEL_MAX_WIDTH)


if __name__ == "__main__":
    unittest.main()
