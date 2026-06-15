import unittest
from unittest.mock import patch

from booklearner.storage import get_storage_status, save_analysis


class StorageTest(unittest.TestCase):
    def test_storage_status_is_disabled_without_env_flag(self):
        with patch.dict("os.environ", {"BOOKLEARNER_MYSQL_ENABLED": "0"}, clear=True):
            status = get_storage_status()

        self.assertFalse(status["enabled"])
        self.assertFalse(status["connected"])

    def test_save_analysis_skips_when_mysql_disabled(self):
        with patch.dict("os.environ", {"BOOKLEARNER_MYSQL_ENABLED": "0"}, clear=True):
            result = save_analysis("Pride", {"status": "ok", "book": {"title": "Pride"}})

        self.assertFalse(result["saved"])
        self.assertEqual(result["reason"], "mysql_disabled")


if __name__ == "__main__":
    unittest.main()
