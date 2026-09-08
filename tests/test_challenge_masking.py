import unittest

from app.services.challenge_masking import challenge_word_forms, mask_word_in_text


class ChallengeMaskingTests(unittest.TestCase):
    def test_masks_regular_s_ed_and_ing_forms(self):
        sentence = "The interruptions flustered her, but nothing flusters or is flustering him."

        self.assertEqual(
            mask_word_in_text(sentence, "fluster"),
            "The interruptions *** her, but nothing *** or is *** him.",
        )

    def test_masks_common_spelling_changes(self):
        self.assertEqual(
            mask_word_in_text("She studies, studied, and keeps studying.", "study"),
            "She ***, ***, and keeps ***.",
        )
        self.assertEqual(
            mask_word_in_text("He stopped, then started stopping again.", "stop"),
            "He ***, then started *** again.",
        )
        self.assertEqual(
            mask_word_in_text("She smiled while smiling for the photo.", "smile"),
            "She *** while *** for the photo.",
        )

    def test_masks_possessive_and_alternate_spelling_forms(self):
        self.assertEqual(
            mask_word_in_text("The student's notes were organized.", "student"),
            "The *** notes were organized.",
        )
        self.assertEqual(
            mask_word_in_text("They organized it.", "organise", "organize"),
            "They *** it.",
        )

    def test_inflected_headword_also_masks_its_base_form(self):
        self.assertEqual(
            mask_word_in_text("One body moved while other bodies rested.", "bodies"),
            "One *** moved while other *** rested.",
        )
        self.assertEqual(
            mask_word_in_text("They study what she studied.", "studied"),
            "They *** what she ***.",
        )

    def test_does_not_mask_unrelated_words_with_a_shared_substring(self):
        sentence = "A clustered pattern appeared near the flustered speaker."

        self.assertEqual(
            mask_word_in_text(sentence, "fluster"),
            "A clustered pattern appeared near the *** speaker.",
        )

    def test_returns_all_requested_regular_forms(self):
        forms = challenge_word_forms("fluster")

        self.assertTrue({"fluster", "flusters", "flustered", "flustering"}.issubset(forms))


if __name__ == "__main__":
    unittest.main()
