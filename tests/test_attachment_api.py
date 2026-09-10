import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from Attachment_Processing.storage import AttachmentStorage


class FakeAiService:
    def ai_answer(
        self,
        question: str,
        session_id: str | None,
        attachment_context: str = "",
    ):
        self.last_attachment_context = attachment_context
        return session_id or "f" * 32, iter(["测试回答"])


class FakeImageAnalyzer:
    def analyze(self, question, storage, session_id, attachments):
        if any(item.extension == ".png" for item in attachments):
            return "\n\n视觉识别结果：图片中是一张办公桌。"
        return ""


class FailingImageAnalyzer:
    def analyze(self, question, storage, session_id, attachments):
        raise RuntimeError("vision unavailable")


class AttachmentApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage_patch = patch.object(
            main,
            "attachment_storage",
            AttachmentStorage(Path(self.temp_dir.name)),
        )
        self.fake_ai = FakeAiService()
        self.ai_patch = patch.object(main, "ai_service", self.fake_ai)
        self.image_patch = patch.object(main, "image_analyzer", FakeImageAnalyzer())
        self.storage_patch.start()
        self.ai_patch.start()
        self.image_patch.start()
        self.client = TestClient(main.app)

    def tearDown(self):
        self.client.close()
        self.image_patch.stop()
        self.ai_patch.stop()
        self.storage_patch.stop()
        self.temp_dir.cleanup()

    def upload_png(self):
        return self.client.post(
            "/attachments",
            files={
                "files": (
                    "报销单.png",
                    b"\x89PNG\r\n\x1a\n" + b"content",
                    "image/png",
                )
            },
        )

    def test_upload_sets_cookie_and_returns_metadata(self):
        response = self.upload_png()

        self.assertEqual(response.status_code, 200)
        attachment = response.json()["attachments"][0]
        self.assertEqual(attachment["name"], "报销单.png")
        self.assertEqual(attachment["content_type"], "image/png")
        self.assertIn(main.COOKIE_NAME, response.cookies)

    def test_rejects_invalid_image(self):
        response = self.client.post(
            "/attachments",
            files={"files": ("fake.png", b"not a png", "image/png")},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("PNG 文件头无效", response.json()["detail"])

    def test_rejects_attachment_id_from_another_session(self):
        attachment_id = self.upload_png().json()["attachments"][0]["id"]
        self.client.cookies.set(main.COOKIE_NAME, "b" * 32)

        response = self.client.post(
            "/get_question",
            json={"question": "读取附件", "attachment_ids": [attachment_id]},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("附件不存在", response.json()["detail"])

    def test_delete_attachment(self):
        attachment_id = self.upload_png().json()["attachments"][0]["id"]

        response = self.client.delete(f"/attachments/{attachment_id}")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            self.client.delete(f"/attachments/{attachment_id}").status_code,
            404,
        )

    def test_question_rejects_unknown_attachment(self):
        self.client.cookies.set(main.COOKIE_NAME, "a" * 32)

        response = self.client.post(
            "/get_question",
            json={"question": "读取附件", "attachment_ids": ["c" * 32]},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("附件不存在", response.json()["detail"])

    def test_question_passes_text_attachment_to_ai(self):
        response = self.client.post(
            "/attachments",
            files={"files": ("说明.txt", "报销金额为 100 元".encode("utf-8"), "text/plain")},
        )
        attachment_id = response.json()["attachments"][0]["id"]

        response = self.client.post(
            "/get_question",
            json={"question": "请阅读附件", "attachment_ids": [attachment_id]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("报销金额为 100 元", self.fake_ai.last_attachment_context)

    def test_question_passes_image_analysis_to_ai(self):
        attachment_id = self.upload_png().json()["attachments"][0]["id"]

        response = self.client.post(
            "/get_question",
            json={"question": "图片里有什么", "attachment_ids": [attachment_id]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("图片中是一张办公桌", self.fake_ai.last_attachment_context)

    def test_question_returns_502_when_image_analysis_fails(self):
        attachment_id = self.upload_png().json()["attachments"][0]["id"]

        with patch.object(main, "image_analyzer", FailingImageAnalyzer()):
            response = self.client.post(
                "/get_question",
                json={"question": "图片里有什么", "attachment_ids": [attachment_id]},
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "图片识别失败，请稍后重试。")


if __name__ == "__main__":
    unittest.main()
