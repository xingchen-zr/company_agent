# 接口层

import env
import json

from pathlib import Path
from fastapi import FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from Attachment_Processing.storage import (
    MAX_FILES_PER_REQUEST,
    AttachmentStorage,
    AttachmentValidationError,
)
from Attachment_Processing.content import build_attachment_context
from Attachment_Processing.vision import ImageAnalyzer

from Rag.ai_answer import AiAnswer

app = FastAPI()
ai_service = AiAnswer()
attachment_storage = AttachmentStorage(Path(__file__).resolve().parent / "uploads")
image_analyzer = ImageAnalyzer()

COOKIE_NAME = env.COOKIE_NAME
COOKIE_MAX_AGE = env.COOKIE_MAX_AGE
FRONTEND_DIR = Path(__file__).resolve().parent / "frontend"

app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static",
)

class Question(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="传入问题",
    )
    attachment_ids: list[str] = Field(
        default_factory=list,
        max_length=MAX_FILES_PER_REQUEST,
        description="当前会话已上传的附件 ID",
    )


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.post("/attachments")
async def upload_attachments(
    request: Request,
    files: list[UploadFile] = File(...),
):
    if not files or len(files) > MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=400,
            detail=f"一次需要上传 1 至 {MAX_FILES_PER_REQUEST} 个附件。",
        )

    session_id = attachment_storage.resolve_session_id(
        request.cookies.get(COOKIE_NAME)
    )
    saved = []
    try:
        for upload in files:
            saved.append(await attachment_storage.save(session_id, upload))
    except AttachmentValidationError as exc:
        for attachment in saved:
            attachment_storage.delete(session_id, attachment.id)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        for upload in files:
            await upload.close()

    response = Response(
        content=json.dumps(
            {"attachments": [item.to_dict() for item in saved]},
            ensure_ascii=False,
        ),
        media_type="application/json",
    )
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_id,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    return response


@app.delete("/attachments/{attachment_id}", status_code=204)
def delete_attachment(attachment_id: str, request: Request):
    session_id = request.cookies.get(COOKIE_NAME)
    try:
        deleted = bool(session_id) and attachment_storage.delete(
            session_id,
            attachment_id,
        )
    except AttachmentValidationError:
        deleted = False
    if not deleted:
        raise HTTPException(status_code=404, detail="附件不存在。")
    return Response(status_code=204)


@app.post("/get_question")
def get_question(
    payload: Question,
    request: Request,
):
    # 浏览器有 Cookie 时读取原来的 session_id；
    # 第一次请求时得到 None。
    session_id = request.cookies.get(COOKIE_NAME)

    try:
        attachments = (
            attachment_storage.require_owned(session_id, payload.attachment_ids)
            if payload.attachment_ids
            else []
        )
    except AttachmentValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    attachment_context = ""
    if attachments:
        try:
            attachment_context = build_attachment_context(
                attachment_storage,
                session_id,
                attachments,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail="附件内容读取失败。") from exc

        try:
            attachment_context += image_analyzer.analyze(
                payload.question,
                attachment_storage,
                session_id,
                attachments,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail="图片识别失败，请稍后重试。") from exc

    resolved_session_id, answer_stream = (
        ai_service.ai_answer(
            question=payload.question,
            session_id=session_id,
            attachment_context=attachment_context,
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
    response = Response(status_code=204)
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
    )
    return response
