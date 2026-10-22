import asyncio
from io import BytesIO
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from fastapi import HTTPException, UploadFile
from starlette.datastructures import Headers
from PIL import Image

from app.main import cleanup_replaced_word_image as remove_local_image


class ImageReplacementTests(unittest.TestCase):
    def test_cleanup_permission_failure_keeps_old_file(self):
        with TemporaryDirectory() as directory:
            image_dir = Path(directory)
            old_image = image_dir / "old.webp"
            old_image.write_bytes(b"old")
            with patch.object(Path, "unlink", side_effect=PermissionError("NAS ACL")):
                with self.assertLogs("speakeasy.images", level="WARNING"):
                    remove_local_image("/media/images/old.webp", image_dir)
            self.assertEqual(old_image.read_bytes(), b"old")

    def test_cleanup_still_removes_unprotected_old_file(self):
        with TemporaryDirectory() as directory:
            image_dir = Path(directory)
            old_image = image_dir / "old.webp"
            old_image.write_bytes(b"old")
            remove_local_image("/media/images/old.webp", image_dir)
            self.assertFalse(old_image.exists())
            remove_local_image("/media/images/old.webp", image_dir)

    def test_successful_upload_survives_old_image_permission_failure(self):
        import app.main as main

        with TemporaryDirectory() as directory:
            image_dir = Path(directory)
            old_image = image_dir / "old.webp"
            old_image.write_bytes(b"old")
            content = BytesIO()
            Image.new("RGB", (8, 8), "green").save(content, "PNG")
            upload = UploadFile(
                filename="replacement.png", file=BytesIO(content.getvalue()),
                headers=Headers({"content-type": "image/png"}),
            )
            word = SimpleNamespace(id=1, word="example", image_url="/media/images/old.webp")
            db = Mock()
            db.get.return_value = word
            with patch.object(main, "IMAGE_DIR", image_dir), \
                 patch.object(main, "require_word_write_access"), \
                 patch.object(main, "remember_word_resource") as remember, \
                 patch.object(main, "word_media_sources", return_value={"image": {"source": "upload"}}), \
                 patch.object(Path, "unlink", side_effect=PermissionError("NAS ACL")), \
                 self.assertLogs("speakeasy.images", level="WARNING"):
                result = asyncio.run(main.replace_word_image(1, upload, "", db))
            self.assertTrue(result["ok"])
            self.assertEqual(result["image_url"], word.image_url)
            self.assertNotEqual(word.image_url, "/media/images/old.webp")
            self.assertTrue((image_dir / Path(word.image_url).name).is_file())
            self.assertTrue(old_image.is_file())
            self.assertTrue(word.image_locked)
            db.commit.assert_called_once()
            remember.assert_called_once()

    def test_new_image_storage_failure_preserves_existing_image(self):
        import app.main as main

        word = SimpleNamespace(id=1, word="example", image_url="/media/images/old.webp")
        db = Mock()
        db.get.return_value = word
        upload = UploadFile(
            filename="invalid.png", file=BytesIO(b"not an image"),
            headers=Headers({"content-type": "image/png"}),
        )
        with TemporaryDirectory() as directory, \
             patch.object(main, "IMAGE_DIR", Path(directory)), \
             patch.object(main, "require_word_write_access"), \
             patch.object(main, "remove_local_image") as cleanup:
            with self.assertRaises(HTTPException) as error:
                asyncio.run(main.replace_word_image(1, upload, "", db))
        self.assertEqual(error.exception.status_code, 400)
        self.assertEqual(word.image_url, "/media/images/old.webp")
        db.commit.assert_not_called()
        cleanup.assert_not_called()


if __name__ == "__main__":
    unittest.main()
