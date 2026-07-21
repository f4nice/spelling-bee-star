import unittest
from unittest.mock import patch

from booklearner.config import get_mysql_config
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

    def test_config_can_reuse_main_database_url(self):
        env = {
            "BOOKLEARNER_MYSQL_ENABLED": "1",
            "BOOKLEARNER_MYSQL_USE_DATABASE_URL": "1",
            "DATABASE_URL": "mysql+pymysql://reader:p%40ss@aliyun.example.com:3307/speakeasy_spelling_bee?charset=utf8mb4",
        }
        with patch("booklearner.config.load_env_file", lambda path=None: None):
            with patch.dict("os.environ", env, clear=True):
                config = get_mysql_config()

        self.assertTrue(config.enabled)
        self.assertEqual(config.host, "aliyun.example.com")
        self.assertEqual(config.port, 3307)
        self.assertEqual(config.database, "speakeasy_spelling_bee")
        self.assertEqual(config.user, "reader")
        self.assertEqual(config.password, "p@ss")


if __name__ == "__main__":
    unittest.main()
