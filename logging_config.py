# 日志记录
import hashlib
import logging
from contextvars import ContextVar
from logging.config import dictConfig
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
REQUEST_ID: ContextVar[str] = ContextVar("request_id", default="-")


class RequestContextFilter(logging.Filter):
    def filter(self, record):
        record.request_id = REQUEST_ID.get()
        return True


def safe_identifier(value):
    """Return a stable, non-reversible identifier suitable for logs."""
    if not value:
        return "-"

    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:12]


def setup_logging():
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_context": {
                "()": RequestContextFilter,
            },
        },
        "formatters": {
            "default": {
                "format": (
                    "%(asctime)s | %(levelname)s | request_id=%(request_id)s | "
                    "%(name)s | "
                    "%(filename)s:%(lineno)d | %(message)s"
                ),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "default",
                "filters": ["request_context"],
            },
            "app_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "INFO",
                "formatter": "default",
                "filters": ["request_context"],
                "filename": str(LOG_DIR / "app.log"),
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 5,
                "encoding": "utf-8",
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "default",
                "filters": ["request_context"],
                "filename": str(LOG_DIR / "error.log"),
                "maxBytes": 10 * 1024 * 1024,
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["console", "app_file", "error_file"],
        },
    })
