"""历史对话记忆管理"""

import env
import json

from redis import Redis
from uuid import uuid4


class ChatHistory:

    def __init__(self):
        self.r = Redis(decode_responses=True)

#加载获取历史对话
    def get_chat_history(self,session_id=None):
        if not session_id:
            session_id = uuid4().hex

        if self.r.exists(session_id):
            chat_history = self.r.lrange(session_id,-10,-1)
        else:
            chat_history = []

        return session_id, chat_history

#存入历史对话,设置过期时间

    def add_chat_history(self,session_id,answer:str,question,completed:bool):
        pipeline = self.r.pipeline(transaction=True)

        chat = {"user":question,
                "ai":answer,
                "completed":completed}

        chat_json = json.dumps(chat,ensure_ascii=False)

        pipeline.rpush(session_id, chat_json)
        pipeline.ltrim(session_id, -10, -1)
        pipeline.expire(session_id, env.Expired_Time)

        pipeline.execute()
