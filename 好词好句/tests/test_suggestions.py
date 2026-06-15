import unittest
from unittest.mock import patch

from booklearner.analyzer import suggest_books


class SuggestionTest(unittest.TestCase):
    def test_suggests_public_domain_book_from_partial_title(self):
        with (
            patch("booklearner.analyzer._internet_archive_suggestions", return_value=[]),
            patch("booklearner.analyzer._google_books_suggestions", return_value=[]),
            patch("booklearner.analyzer._open_library_suggestions", return_value=[]),
        ):
            titles = [item["title"] for item in suggest_books("gatsb")]

        self.assertIn("The Great Gatsby", titles)

    def test_suggests_public_domain_book_from_typo(self):
        with (
            patch("booklearner.analyzer._internet_archive_suggestions", return_value=[]),
            patch("booklearner.analyzer._google_books_suggestions", return_value=[]),
            patch("booklearner.analyzer._open_library_suggestions", return_value=[]),
        ):
            titles = [item["title"] for item in suggest_books("sherlok")]

        self.assertIn("The Adventures of Sherlock Holmes", titles)

    def test_suggests_popular_book_without_public_text(self):
        with (
            patch("booklearner.analyzer._internet_archive_suggestions", return_value=[]),
            patch("booklearner.analyzer._google_books_suggestions", return_value=[]),
            patch("booklearner.analyzer._open_library_suggestions", return_value=[]),
        ):
            items = suggest_books("graveyard")

        self.assertEqual(items[0]["title"], "The Graveyard Book")
        self.assertFalse(items[0]["availableText"])


if __name__ == "__main__":
    unittest.main()
