import mimetypes
import os
import unittest

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"


class ImageDeliveryTest(unittest.TestCase):
    def test_webp_media_is_served_with_image_mime_type(self):
        # Importing the application registers the media type before its
        # StaticFiles mount is created. This mirrors the production process.
        import app.main  # noqa: F401

        self.assertEqual(mimetypes.guess_type("word.webp")[0], "image/webp")


if __name__ == "__main__":
    unittest.main()
