"""历史对话记忆管理"""

import env
import json
import logging
import time

from logging_config import safe_identifier
from redis import Redis
from uuid import uuid4


logger = logging.getLogger(__name__)


class ChatHistory:

    def __init__(self):
        self.r = Redis(decode_responses=True)

#加载获取历史对话
    def get_chat_history(self,session_id=None):
        started_at = time.perf_counter()

        if not session_id:
            session_id = uuid4().hex
        session_ref = safe_identifier(session_id)

        try:
            if self.r.exists(session_id):
                chat_history = self.r.lrange(session_id,-10,-1)
            else:
                chat_history = []
        except Exception:
            logger.exception("history_load_failed session=%s", session_ref)
            raise

        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "history_loaded session=%s count=%d duration_ms=%.2f",
            session_ref,
            len(chat_history),
            duration_ms,
        )

        return session_id, chat_history

#存入历史对话,设置过期时间

    def add_chat_history(self,session_id,answer:str,question,completed:bool):
        started_at = time.perf_counter()
        session_ref = safe_identifier(session_id)

        pipeline = self.r.pipeline(transaction=True)

        chat = {"user":question,
                "ai":answer,
                "completed":completed}

        chat_json = json.dumps(chat,ensure_ascii=False)

        pipeline.rpush(session_id, chat_json)
        pipeline.ltrim(session_id, -10, -1)
        pipeline.expire(session_id, env.Expired_Time)

        try:
            pipeline.execute()
        except Exception:
            logger.exception(
                "history_save_failed session=%s completed=%s",
                session_ref,
                completed,
            )
            raise

        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "history_saved session=%s completed=%s question_length=%d "
            "answer_length=%d duration_ms=%.2f",
            session_ref,
            completed,
            len(question),
            len(answer),
            duration_ms,
        )
