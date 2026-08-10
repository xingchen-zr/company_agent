"""对文本进行向量存储和查询"""
import logging
import time

from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_chroma import Chroma
from Document_Processing.Document_Processing import DocumentProcessing

import env


logger = logging.getLogger(__name__)


class VectorProcessing:

    def __init__(self):
        self.vector_store = Chroma(
            collection_name = "Commpany_Vector",
            embedding_function = OllamaEmbeddings(model="nomic-embed-text"),
            persist_directory = env.vector_path
        )

#向量存储
    def vector_storage(self):
        started_at = time.perf_counter()
        logger.info("vector_storage_started")

        try:
            processor = DocumentProcessing(
                path=env.text_Path,
                chunk_size=env.chunk_size,
                chunk_overlap=env.chunk_overlap
            )

            chunks = processor.text_processing()

            self.vector_store.add_documents(
                documents=chunks,
                ids = [str(i) for i in range(len(chunks))]
                )
        except Exception:
            logger.exception("vector_storage_failed")
            raise

        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "vector_storage_finished chunk_count=%d duration_ms=%.2f",
            len(chunks),
            duration_ms,
        )

        return ("保存成功")

#相似向量搜索
    def vector_search(self,question:str):
        started_at = time.perf_counter()

        try:
            results = self.vector_store.similarity_search_with_relevance_scores(
                question,
                k=env.k_top,)

            documents = [
                document
                for document, score in results
                if score >= env.relevance_threshold
            ]
        except Exception:
            logger.exception(
                "vector_search_failed question_length=%d",
                len(question),
            )
            raise

        max_score = max((score for _, score in results), default=-1.0)
        duration_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "vector_search_finished question_length=%d raw_count=%d "
            "accepted_count=%d max_score=%.4f threshold=%.4f duration_ms=%.2f",
            len(question),
            len(results),
            len(documents),
            max_score,
            env.relevance_threshold,
            duration_ms,
        )

        return documents

if __name__ == "__main":
    result = VectorProcessing

    result.vector_storage
