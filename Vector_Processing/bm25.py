"""Small persistent BM25 index used alongside the Chroma vector store."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document


_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]+|[a-z0-9_]+", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    """Tokenize mixed Chinese/English text for lexical matching."""

    tokens: list[str] = []
    for segment in _TOKEN_RE.findall((text or "").lower()):
        if re.fullmatch(r"[\u4e00-\u9fff]+", segment):
            tokens.extend(segment)
            tokens.extend(segment[i : i + 2] for i in range(len(segment) - 1))
        else:
            tokens.append(segment)
    return tokens


class BM25Index:
    """A minimal Okapi BM25 implementation with JSON persistence."""

    def __init__(
        self,
        storage_path: str | Path,
        *,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.storage_path = Path(storage_path)
        self.k1 = k1
        self.b = b
        self.documents: list[Document] = []
        self._term_frequencies: list[dict[str, int]] = []
        self._doc_lengths: list[int] = []
        self._idf: dict[str, float] = {}
        self._average_doc_length = 0.0
        self.load()

    def _set_documents(self, documents: Iterable[Document]) -> None:
        self.documents = list(documents)
        self._term_frequencies = []
        self._doc_lengths = []
        document_frequency: dict[str, int] = {}

        for document in self.documents:
            frequencies: dict[str, int] = {}
            for token in tokenize(document.page_content):
                frequencies[token] = frequencies.get(token, 0) + 1
            self._term_frequencies.append(frequencies)
            self._doc_lengths.append(sum(frequencies.values()))
            for token in frequencies:
                document_frequency[token] = document_frequency.get(token, 0) + 1

        document_count = len(self.documents)
        self._average_doc_length = (
            sum(self._doc_lengths) / document_count if document_count else 0.0
        )
        self._idf = {
            token: math.log(1 + (document_count - frequency + 0.5) / (frequency + 0.5))
            for token, frequency in document_frequency.items()
        }

    @staticmethod
    def _serialize(document: Document) -> dict:
        return {"page_content": document.page_content, "metadata": document.metadata}

    def rebuild(self, documents: Iterable[Document]) -> None:
        """Replace the index and persist the current Chroma corpus."""

        self._set_documents(documents)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(
            json.dumps(
                [self._serialize(document) for document in self.documents],
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

    def load(self) -> None:
        if not self.storage_path.exists():
            return
        try:
            raw_documents = json.loads(self.storage_path.read_text(encoding="utf-8"))
            documents = [
                Document(
                    page_content=str(item.get("page_content", "")),
                    metadata=item.get("metadata") or {},
                )
                for item in raw_documents
                if isinstance(item, dict) and item.get("page_content")
            ]
            self._set_documents(documents)
        except (OSError, ValueError, TypeError):
            self._set_documents([])

    def search(self, query: str, k: int = 10) -> list[tuple[Document, float]]:
        if not self.documents or k <= 0:
            return []

        query_terms = set(tokenize(query))
        if not query_terms:
            return []

        scored: list[tuple[int, float]] = []
        for index, frequencies in enumerate(self._term_frequencies):
            length = self._doc_lengths[index]
            score = 0.0
            for token in query_terms:
                frequency = frequencies.get(token, 0)
                if not frequency:
                    continue
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * length / (self._average_doc_length or 1.0)
                )
                score += self._idf.get(token, 0.0) * frequency * (self.k1 + 1) / denominator
            if score > 0:
                scored.append((index, score))

        scored.sort(key=lambda item: (-item[1], item[0]))
        return [(self.documents[index], score) for index, score in scored[:k]]
