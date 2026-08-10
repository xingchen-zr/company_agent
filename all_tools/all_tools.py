"""这里为tool构建管理模块"""

import logging
import time

from Vector_Processing.Vector_Processing import VectorProcessing
from langchain_core.tools import tool,StructuredTool


logger = logging.getLogger(__name__)


class Tools:
    def __init__(self):

        self.vector_searchs = VectorProcessing()
        self.tools = [
            StructuredTool.from_function(
                func=self.vector_search,
                name="vector_search",
                description="搜索公司制度文档"
                )
                ]

    """整理封装其他模块的方法,方便取出调用"""

    def vector_search(self,question):
        """搜索相似文本内容并返回"""
        started_at = time.perf_counter()
        logger.info(
            "tool_started tool=vector_search question_length=%d",
            len(question),
        )

        try:
            documents = self.vector_searchs.vector_search(question)
        except Exception:
            logger.exception("tool_failed tool=vector_search")
            raise

        parts = []

        for index, document in enumerate(documents, start=1):
            source = document.metadata.get("source", "未知来源")
            page = document.metadata.get("page", "未知页码")

            parts.append(
                f"[资料{index}]\n"
                f"来源：{source}\n"
                f"页码：{page}\n"
                f"内容：{document.page_content}"
            )

        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "tool_finished tool=vector_search result_count=%d duration_ms=%.2f",
            len(documents),
            duration_ms,
        )

        if not documents:
            return("没有搜索到相关信息")

        else:
            return "\n\n".join(parts)
