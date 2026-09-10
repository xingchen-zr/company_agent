import asyncio
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from fastapi import UploadFile
from starlette.datastructures import Headers

from Attachment_Processing.storage import AttachmentStorage
from Attachment_Processing.vision import ImageAnalyzer


class FakeVisionModel:
    def __init__(self, content="图片中有一台电脑"):
        self.content = content
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return SimpleNamespace(content=self.content)


class ImageAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.storage = AttachmentStorage(Path(self.temp_dir.name))
        self.session_id = "a" * 32

    def tearDown(self):
        self.temp_dir.cleanup()

    def save_png(self):
        upload = UploadFile(
            file=BytesIO(b"\x89PNG\r\n\x1a\ncontent"),
            filename="现场.png",
            headers=Headers({"content-type": "image/png"}),
        )
        return asyncio.run(self.storage.save(self.session_id, upload))

    def test_sends_image_as_multimodal_data_url(self):
        model = FakeVisionModel()
        analyzer = ImageAnalyzer(model=model)

        result = analyzer.analyze(
            "请说明图片内容",
            self.storage,
            self.session_id,
            [self.save_png()],
        )

        blocks = model.messages[0].content
        image_block = next(block for block in blocks if block["type"] == "image_url")
        self.assertTrue(image_block["image_url"]["url"].startswith("data:image/png;base64,"))
        self.assertIn("请说明图片内容", blocks[0]["text"])
        self.assertIn("现场.png", blocks[1]["text"])
        self.assertIn("图片中有一台电脑", result)

    def test_rejects_empty_vision_response(self):
        analyzer = ImageAnalyzer(model=FakeVisionModel(content=""))

        with self.assertRaisesRegex(ValueError, "未返回有效识别结果"):
            analyzer.analyze(
                "识别图片",
                self.storage,
                self.session_id,
                [self.save_png()],
            )


if __name__ == "__main__":
    unittest.main()
