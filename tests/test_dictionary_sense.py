import unittest

from app.services.dictionary import _first_free_meaning_fields


class FreeDictionarySenseTest(unittest.TestCase):
    def test_example_does_not_leak_from_later_sense(self):
        entry = {"meanings": [{"partOfSpeech": "noun", "definitions": [
            {"definition": "A lifting machine."},
            {"definition": "A bird.", "example": "The crane flew away."},
        ]}]}
        self.assertEqual(_first_free_meaning_fields(entry), ("noun", "A lifting machine.", None))

    def test_first_defined_sense_owns_part_of_speech_and_example(self):
        entry = {"meanings": [
            {"partOfSpeech": "noun", "definitions": [{"example": "No definition here."}]},
            {"partOfSpeech": "verb", "definitions": [
                {"definition": "Stretch the neck.", "example": "She craned her neck."},
            ]},
        ]}
        self.assertEqual(_first_free_meaning_fields(entry), ("verb", "Stretch the neck.", "She craned her neck."))


if __name__ == "__main__":
    unittest.main()
