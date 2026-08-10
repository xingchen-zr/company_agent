"""ai问答模块"""

import json
import logging
import time

from langchain.agents import create_agent
from all_tools.all_tools import Tools
from env import MODEL,system_prompt
from langchain_core.messages import AIMessageChunk
from logging_config import safe_identifier
from Rag.chat_history import ChatHistory


logger = logging.getLogger(__name__)


class AiAnswer():

    def __init__(self):

        self.model = MODEL
        self.tool_manager = Tools()
        self.agent = create_agent(
            model=self.model,
            tools=self.tool_manager.tools,
            system_prompt=system_prompt,
        )
        self.history_manager = ChatHistory()

    def ai_answer(self,question:str,session_id:str):

        resolved_session_id, history_records = (self.history_manager.get_chat_history(session_id))
        session_ref = safe_identifier(resolved_session_id)

        def stream():
            answer_chunks = []
            history_messages = []
            completed = False
            started_at = time.perf_counter()

            logger.info(
                "agent_stream_started session=%s history_count=%d question_length=%d",
                session_ref,
                len(history_records),
                len(question),
            )
            try:
                for record in history_records:
                    chat = json.loads(record)

                    if not chat.get("completed", True):
                        continue

                    history_messages.extend([
                        {"role": "user", "content": chat["user"]},
                        {"role": "assistant", "content": chat["ai"]},
                        ])

                input_data = {
                        "messages":[
                            *history_messages,
                            {
                                "role":"user",
                                "content":f"用户问题：{question}"
                            }
                        ],
                    }

                for message_chunk,metadata in self.agent.stream(input_data,
                                                        stream_mode = "messages"):
                    if not isinstance(message_chunk,AIMessageChunk):
                        continue

                    content = message_chunk.content

                    #返回结果
                    if isinstance(content,str) and content:
                        answer_chunks.append(content)
                        yield content

                completed = True

            except GeneratorExit:
                logger.warning(
                    "agent_stream_closed session=%s answer_length=%d",
                    session_ref,
                    sum(len(chunk) for chunk in answer_chunks),
                )
                raise
            except Exception:
                logger.exception(
                    "agent_stream_failed session=%s answer_length=%d",
                    session_ref,
                    sum(len(chunk) for chunk in answer_chunks),
                )
                raise
            finally:
                #保存对话
                complete_answer = "".join(answer_chunks)

                if complete_answer:
                    try:
                        self.history_manager.add_chat_history(
                            session_id=resolved_session_id,
                            question=question,
                            answer=complete_answer,
                            completed=completed,
                        )
                    except Exception:
                        logger.exception(
                            "agent_history_save_failed session=%s completed=%s",
                            session_ref,
                            completed,
                        )
                        if completed:
                            raise

                duration_ms = (time.perf_counter() - started_at) * 1000
                logger.info(
                    "agent_stream_finished session=%s completed=%s "
                    "answer_length=%d duration_ms=%.2f",
                    session_ref,
                    completed,
                    len(complete_answer),
                    duration_ms,
                )

        return resolved_session_id, stream()
