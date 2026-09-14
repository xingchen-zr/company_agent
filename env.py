# 存放各种可能随时可修改的变量
import os
from pathlib import Path

from langchain_deepseek.chat_models import ChatDeepSeek


BASE_DIR = Path(__file__).resolve().parent


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


text_Path = os.getenv(
    "TEXT_PATH",
    str(BASE_DIR / "Document_Processing" / "金融公司制度与操作手册.txt"),
)
encoding = "utf-8"
chunk_size = 300
chunk_overlap = 100
vector_path = os.getenv("VECTOR_PATH", str(BASE_DIR / "Chroma_db"))
UPLOAD_PATH = os.getenv("UPLOAD_PATH", str(BASE_DIR / "uploads"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
k_top: int = 20
vector_k: int = k_top
bm25_k: int = k_top
hybrid_k: int = 8
vector_weight: float = 0.5
bm25_weight: float = 0.5
rrf_k: int = 60
MODEL = ChatDeepSeek(model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"))
IMAGE_MODEL = ChatDeepSeek(
    model=os.getenv("DEEPSEEK_IMAGE_MODEL", "deepseek-v4-flash-vision-exp")
)
Expired_Time = 60*60*48
system_prompt = ("你是一位充分了解公司制度的助手,"
                "专门解答公司内员工的各种对公司相关事务的疑惑,"
                "当你回答与公司制度,福利,规则相关的问题时,必须调用工具查询,"
                "你的回答必须有理有据,回答时要附带你回答问题的依据,"
                "没有依据的问题你要回答不知道")
relevance_threshold = 0.3
COOKIE_NAME = "chat_session_id"
COOKIE_MAX_AGE = 60 * 60 * 48
COOKIE_SECURE = _env_bool("COOKIE_SECURE", default=False)
