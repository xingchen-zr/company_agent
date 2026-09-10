"""ai问答模块"""

import json

from langchain.agents import create_agent
from all_tools.all_tools import Tools
from env import MODEL,system_prompt
from langchain_core.messages import AIMessageChunk
from Rag.chat_history import ChatHistory


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

    def ai_answer(
        self,
        question: str,
        session_id: str | None,
        attachment_context: str = "",
    ):

        resolved_session_id, history_records = (self.history_manager.get_chat_history(session_id))

        def stream():
            answer_chunks = []
            history_messages = []
            completed = False
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
                                "role": "user",
                                "content": (
                                    f"用户问题：{question}"
                                    f"{attachment_context}"
                                ),
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

            finally:
                #保存对话
                complete_answer = "".join(answer_chunks)

                if complete_answer:
                    if completed:
                        self.history_manager.add_chat_history(
                            session_id=resolved_session_id,
                            question=question,
                            answer=complete_answer,
                            completed=True,
                        )
                    else:
                        try:
                            self.history_manager.add_chat_history(
                                session_id=resolved_session_id,
                                question=question,
                                answer=complete_answer,
                                completed=False,
                            )
                        except Exception:
                            pass

        return resolved_session_id, stream()
