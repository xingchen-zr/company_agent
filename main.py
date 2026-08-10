# 接口层

import env
import logging
import time
import uuid

from pathlib import Path
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from logging_config import REQUEST_ID, safe_identifier, setup_logging

setup_logging()
logger = logging.getLogger(__name__)

from Rag.ai_answer import AiAnswer

app = FastAPI()
ai_service = AiAnswer()

COOKIE_NAME = env.COOKIE_NAME
COOKIE_MAX_AGE = env.COOKIE_MAX_AGE
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static",
)

@app.middleware("http")
async def log_request(request: Request, call_next):
    request_id = uuid.uuid4().hex[:12]
    request_id_token = REQUEST_ID.set(request_id)
    request.state.request_id = request_id
    started_at = time.perf_counter()

    try:
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started_at) * 1000
        response.headers["X-Request-ID"] = request_id

        log_method = logger.debug if request.url.path.startswith("/static/") else logger.info
        log_method(
            "http_response_started method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        return response
    except Exception:
        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.exception(
            "http_request_failed method=%s path=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            duration_ms,
        )
        raise
    finally:
        REQUEST_ID.reset(request_id_token)

class Question(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="传入问题",
    )


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/get_question")
def get_question(
    payload: Question,
    request: Request,
):
    # 浏览器有 Cookie 时读取原来的 session_id；
    # 第一次请求时得到 None。
    session_id = request.cookies.get(COOKIE_NAME)

    resolved_session_id, answer_stream = (
        ai_service.ai_answer(
            question=payload.question,
            session_id=session_id,
        )
    )

    response = StreamingResponse(
        answer_stream,
        media_type="text/plain; charset=utf-8",
    )

    # 将最终 session_id 保存到浏览器。
    # 每次响应都设置，可以同步刷新 Cookie 有效期。
    response.set_cookie(
        key=COOKIE_NAME,
        value=resolved_session_id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,  # 本地 HTTP 调试使用 False
        path="/",
    )

    return response


@app.post("/new_chat", status_code=204)
def new_chat(request: Request):
    session_ref = safe_identifier(request.cookies.get(COOKIE_NAME))
    logger.info("chat_session_reset session=%s", session_ref)

    response = Response(status_code=204)
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
    )
    return response
