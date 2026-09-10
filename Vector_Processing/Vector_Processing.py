"""向量、BM25 及其融合检索。"""

from __future__ import annotations

import logging
from pathlib import Path
import time

from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from Document_Processing.Document_Processing import DocumentProcessing
from Vector_Processing.bm25 import BM25Index
import env


logger = logging.getLogger(__name__)


class VectorProcessing:

    def __init__(self):
        self.vector_store = Chroma(
            collection_name="Commpany_Vector",
            embedding_function=OllamaEmbeddings(model="nomic-embed-text"),
            persist_directory=env.vector_path,
        )
        self.bm25_index = BM25Index(Path(env.vector_path) / "bm25_index.json")
        self._sync_bm25_from_vector_store()

    def _sync_bm25_from_vector_store(self) -> None:
        """Rebuild lexical data from Chroma so both indexes share one corpus."""

        try:
            payload = self.vector_store.get(include=["documents", "metadatas"])
            contents = payload.get("documents") or []
            metadatas = payload.get("metadatas") or []
            documents = [
                Document(
                    page_content=content,
                    metadata=(metadatas[index] or {}) if index < len(metadatas) else {},
                )
                for index, content in enumerate(contents)
                if content
            ]
        except Exception:
            # BM25 is an enhancement; a Chroma/API issue should not prevent startup.
            return

        self.bm25_index.rebuild(documents)

    def vector_storage(self):
        started_at = time.perf_counter()
        logger.info("vector_storage_started")
        try:
            processor = DocumentProcessing(
                path=env.text_Path,
                chunk_size=env.chunk_size,
                chunk_overlap=env.chunk_overlap,
            )
            chunks = processor.text_processing()
            self.vector_store.add_documents(
                documents=chunks,
                ids=[str(i) for i in range(len(chunks))],
            )
            self._sync_bm25_from_vector_store()
        except Exception:
            logger.exception("vector_storage_failed")
            raise

        logger.info(
            "vector_storage_finished chunk_count=%d duration_ms=%.2f",
            len(chunks),
            (time.perf_counter() - started_at) * 1000,
        )
        return "保存成功"

    @staticmethod
    def _document_key(document: Document) -> tuple[str, str, str]:
        metadata = document.metadata or {}
        return (
            document.page_content,
            str(metadata.get("source", "")),
            str(metadata.get("page", "")),
        )

    @staticmethod
    def _fuse_results(
        vector_results: list[tuple[Document, float]],
        bm25_results: list[tuple[Document, float]],
        *,
        k: int,
        vector_weight: float,
        bm25_weight: float,
        rrf_k: int,
    ) -> list[Document]:
        """Fuse two ranked lists with weighted reciprocal rank fusion."""

        fused: dict[tuple[str, str, str], tuple[Document, float]] = {}
        for rank, (document, _score) in enumerate(vector_results, start=1):
            key = VectorProcessing._document_key(document)
            contribution = vector_weight / (rrf_k + rank)
            current = fused.get(key)
            fused[key] = (document, contribution + (current[1] if current else 0.0))

        for rank, (document, _score) in enumerate(bm25_results, start=1):
            key = VectorProcessing._document_key(document)
            contribution = bm25_weight / (rrf_k + rank)
            current = fused.get(key)
            fused[key] = (document, contribution + (current[1] if current else 0.0))

        ranked = sorted(fused.values(), key=lambda item: item[1], reverse=True)
        return [document for document, _score in ranked[:k]]

    def hybrid_search(self, question: str, k: int | None = None) -> list[Document]:
        """Return a de-duplicated blend of semantic and lexical matches."""

        started_at = time.perf_counter()
        output_k = k or env.hybrid_k
        try:
            raw_vector_results = (
                self.vector_store.similarity_search_with_relevance_scores(
                    question,
                    k=env.vector_k,
                )
            )
            vector_results = [
                (document, score)
                for document, score in raw_vector_results
                if score >= env.relevance_threshold
            ]
            bm25_results = self.bm25_index.search(question, k=env.bm25_k)
            documents = self._fuse_results(
                vector_results,
                bm25_results,
                k=output_k,
                vector_weight=env.vector_weight,
                bm25_weight=env.bm25_weight,
                rrf_k=env.rrf_k,
            )
        except Exception:
            logger.exception(
                "hybrid_search_failed question_length=%d",
                len(question),
            )
            raise

        logger.info(
            "hybrid_search_finished question_length=%d vector_raw_count=%d "
            "vector_accepted_count=%d bm25_count=%d fused_count=%d duration_ms=%.2f",
            len(question),
            len(raw_vector_results),
            len(vector_results),
            len(bm25_results),
            len(documents),
            (time.perf_counter() - started_at) * 1000,
        )
        return documents

    def vector_search(self, question: str) -> list[Document]:
        """Backward-compatible tool entry point; now performs hybrid retrieval."""

        return self.hybrid_search(question)


if __name__ == "__main__":
    VectorProcessing().vector_storage()
