from __future__ import annotations

import json
import re
import zipfile
from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_FILES_PER_REQUEST = 5
SESSION_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")
ATTACHMENT_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")

ALLOWED_TYPES = {
    ".png": {"image/png", "application/octet-stream"},
    ".jpg": {"image/jpeg", "application/octet-stream"},
    ".jpeg": {"image/jpeg", "application/octet-stream"},
    ".webp": {"image/webp", "application/octet-stream"},
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/octet-stream",
    },
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
        "application/octet-stream",
    },
    ".txt": {"text/plain", "application/octet-stream"},
    ".md": {"text/markdown", "text/plain", "application/octet-stream"},
    ".csv": {
        "text/csv",
        "application/csv",
        "application/vnd.ms-excel",
        "text/plain",
        "application/octet-stream",
    },
}


class AttachmentValidationError(ValueError):
    pass


@dataclass(frozen=True)
class StoredAttachment:
    id: str
    name: str
    content_type: str
    size: int
    extension: str

    def to_dict(self) -> dict:
        return asdict(self)


class AttachmentStorage:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def resolve_session_id(session_id: str | None) -> str:
        if session_id and SESSION_ID_PATTERN.fullmatch(session_id):
            return session_id
        return uuid4().hex

    async def save(self, session_id: str, upload: UploadFile) -> StoredAttachment:
        original_name = Path(upload.filename or "").name
        extension = Path(original_name).suffix.lower()
        if not original_name or extension not in ALLOWED_TYPES:
            raise AttachmentValidationError(
                "不支持该文件类型，可上传 PNG、JPEG、WebP、PDF、DOCX、XLSX、TXT、MD 或 CSV。"
            )

        declared_type = (upload.content_type or "application/octet-stream").lower()
        if declared_type not in ALLOWED_TYPES[extension]:
            raise AttachmentValidationError("文件扩展名与浏览器报告的内容类型不一致。")

        data = await self._read_limited(upload)
        self._validate_content(extension, data)

        attachment_id = uuid4().hex
        session_dir = self._session_dir(session_id)
        stored_path = session_dir / f"{attachment_id}{extension}"
        metadata_path = session_dir / f"{attachment_id}.json"
        stored_path.write_bytes(data)

        metadata = StoredAttachment(
            id=attachment_id,
            name=original_name,
            content_type=declared_type,
            size=len(data),
            extension=extension,
        )
        metadata_path.write_text(
            json.dumps(metadata.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return metadata

    def delete(self, session_id: str | None, attachment_id: str) -> bool:
        if not session_id or not ATTACHMENT_ID_PATTERN.fullmatch(attachment_id):
            return False

        session_dir = self._session_dir(session_id, create=False)
        metadata_path = session_dir / f"{attachment_id}.json"
        if not metadata_path.is_file():
            return False

        metadata = self._load_metadata(metadata_path)
        stored_path = session_dir / f"{attachment_id}{metadata.extension}"
        if stored_path.is_file():
            stored_path.unlink()
        metadata_path.unlink()
        return True

    def require_owned(
        self,
        session_id: str | None,
        attachment_ids: list[str],
    ) -> list[StoredAttachment]:
        if len(attachment_ids) > MAX_FILES_PER_REQUEST:
            raise AttachmentValidationError(
                f"一次最多提交 {MAX_FILES_PER_REQUEST} 个附件。"
            )

        if not session_id:
            raise AttachmentValidationError("当前会话无效，请重新上传附件。")
        session_dir = self._session_dir(session_id, create=False)
        attachments = []
        for attachment_id in attachment_ids:
            if not ATTACHMENT_ID_PATTERN.fullmatch(attachment_id):
                raise AttachmentValidationError("附件 ID 格式无效。")
            metadata_path = session_dir / f"{attachment_id}.json"
            if not metadata_path.is_file():
                raise AttachmentValidationError("附件不存在或不属于当前会话。")
            attachments.append(self._load_metadata(metadata_path))
        return attachments

    def read_bytes(self, session_id: str, attachment: StoredAttachment) -> bytes:
        """Read an already-authorized attachment from the session directory."""
        session_dir = self._session_dir(session_id, create=False)
        stored_path = session_dir / f"{attachment.id}{attachment.extension}"
        try:
            return stored_path.read_bytes()
        except OSError as exc:
            raise AttachmentValidationError("附件文件读取失败。") from exc

    async def _read_limited(self, upload: UploadFile) -> bytes:
        chunks = []
        total = 0
        while chunk := await upload.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_FILE_SIZE:
                raise AttachmentValidationError("单个附件不能超过 10 MB。")
            chunks.append(chunk)
        if total == 0:
            raise AttachmentValidationError("不能上传空文件。")
        return b"".join(chunks)

    def _session_dir(self, session_id: str, create: bool = True) -> Path:
        if not SESSION_ID_PATTERN.fullmatch(session_id):
            raise AttachmentValidationError("会话 ID 格式无效。")
        path = (self.root / session_id).resolve()
        if path.parent != self.root:
            raise AttachmentValidationError("附件存储路径无效。")
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _load_metadata(path: Path) -> StoredAttachment:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return StoredAttachment(**payload)
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            raise AttachmentValidationError("附件元数据损坏。") from exc

    @staticmethod
    def _validate_content(extension: str, data: bytes) -> None:
        if extension == ".png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise AttachmentValidationError("PNG 文件头无效。")
        if extension in {".jpg", ".jpeg"} and not data.startswith(b"\xff\xd8\xff"):
            raise AttachmentValidationError("JPEG 文件头无效。")
        if extension == ".webp" and not (
            data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP"
        ):
            raise AttachmentValidationError("WebP 文件头无效。")
        if extension == ".pdf" and not data.startswith(b"%PDF-"):
            raise AttachmentValidationError("PDF 文件头无效。")
        if extension in {".docx", ".xlsx"}:
            AttachmentStorage._validate_office_archive(extension, data)
        if extension in {".txt", ".md", ".csv"}:
            if b"\x00" in data:
                raise AttachmentValidationError("文本文件包含二进制内容。")
            try:
                data.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise AttachmentValidationError("文本文件必须使用 UTF-8 编码。") from exc

    @staticmethod
    def _validate_office_archive(extension: str, data: bytes) -> None:
        try:
            with zipfile.ZipFile(BytesIO(data)) as archive:
                names = set(archive.namelist())
        except zipfile.BadZipFile as exc:
            raise AttachmentValidationError("Office 文件容器无效。") from exc

        required = "word/document.xml" if extension == ".docx" else "xl/workbook.xml"
        if required not in names:
            raise AttachmentValidationError("Office 文件内容与扩展名不一致。")
