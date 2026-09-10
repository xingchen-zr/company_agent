import asyncio
import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile
from starlette.datastructures import Headers

from Attachment_Processing.storage import (
    AttachmentStorage,
    AttachmentValidationError,
)


class AttachmentStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = AttachmentStorage(Path(self.temp_dir.name))
        self.session_id = "a" * 32

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def upload(name: str, content_type: str, data: bytes) -> UploadFile:
        return UploadFile(
            file=BytesIO(data),
            filename=name,
            headers=Headers({"content-type": content_type}),
        )

    def test_saves_and_deletes_valid_png(self):
        upload = self.upload(
            "报销单.png",
            "image/png",
            b"\x89PNG\r\n\x1a\n" + b"content",
        )

        saved = asyncio.run(self.storage.save(self.session_id, upload))

        self.assertEqual(saved.name, "报销单.png")
        self.assertEqual(
            self.storage.require_owned(self.session_id, [saved.id]),
            [saved],
        )
        self.assertTrue(self.storage.delete(self.session_id, saved.id))
        self.assertFalse(self.storage.delete(self.session_id, saved.id))

    def test_rejects_fake_image(self):
        upload = self.upload("fake.png", "image/png", b"not a png")

        with self.assertRaisesRegex(AttachmentValidationError, "PNG 文件头无效"):
            asyncio.run(self.storage.save(self.session_id, upload))

    def test_accepts_valid_docx_container(self):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types />")
            archive.writestr("word/document.xml", "<document />")
        upload = self.upload(
            "制度.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            buffer.getvalue(),
        )

        saved = asyncio.run(self.storage.save(self.session_id, upload))

        self.assertEqual(saved.extension, ".docx")

    def test_rejects_attachment_from_another_session(self):
        upload = self.upload("note.txt", "text/plain", "内容".encode("utf-8"))
        saved = asyncio.run(self.storage.save(self.session_id, upload))

        with self.assertRaisesRegex(AttachmentValidationError, "附件不存在"):
            self.storage.require_owned("b" * 32, [saved.id])


if __name__ == "__main__":
    unittest.main()
