import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from langchain_core.documents import Document

from Vector_Processing.bm25 import BM25Index, tokenize
from Vector_Processing.Vector_Processing import VectorProcessing
from all_tools.all_tools import Tools


class BM25Tests(unittest.TestCase):
    def test_tokenizer_keeps_chinese_bigrams_and_english_terms(self):
        tokens = tokenize("差旅报销 Travel 2026")
        self.assertIn("报销", tokens)
        self.assertIn("travel", tokens)
        self.assertIn("2026", tokens)

    def test_search_prefers_exact_lexical_match_and_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bm25.json"
            documents = [
                Document(page_content="差旅报销须在出差结束后提交", metadata={"source": "a"}),
                Document(page_content="采购申请需要预算审批", metadata={"source": "b"}),
            ]
            index = BM25Index(path)
            index.rebuild(documents)
            results = index.search("差旅报销", k=1)
            self.assertEqual(results[0][0].metadata["source"], "a")

            restored = BM25Index(path)
            self.assertEqual(restored.search("差旅报销", k=1)[0][0].metadata["source"], "a")

    def test_fusion_deduplicates_documents_and_combines_rankings(self):
        first = Document(page_content="报销时限为五个工作日", metadata={"source": "a"})
        second = Document(page_content="采购审批权限矩阵", metadata={"source": "b"})
        result = VectorProcessing._fuse_results(
            [(first, 0.9), (second, 0.7)],
            [(first, 2.0)],
            k=10,
            vector_weight=0.55,
            bm25_weight=0.45,
            rrf_k=60,
        )
        self.assertEqual(result, [first, second])
        self.assertEqual(len({document.page_content for document in result}), 2)

    def test_hybrid_search_includes_vector_and_bm25_only_matches(self):
        vector_document = Document(page_content="语义召回结果", metadata={"source": "vector"})
        bm25_document = Document(page_content="精确关键词结果", metadata={"source": "bm25"})
        processor = VectorProcessing.__new__(VectorProcessing)
        processor.vector_store = Mock()
        processor.vector_store.similarity_search_with_relevance_scores.return_value = [
            (vector_document, 0.9)
        ]
        processor.bm25_index = Mock()
        processor.bm25_index.search.return_value = [(bm25_document, 4.2)]

        with patch.multiple(
            "env",
            vector_k=10,
            bm25_k=10,
            hybrid_k=10,
            vector_weight=0.55,
            bm25_weight=0.45,
            rrf_k=60,
            relevance_threshold=0.3,
        ):
            results = processor.hybrid_search("精确关键词")

        self.assertEqual({document.metadata["source"] for document in results}, {"vector", "bm25"})

    def test_tool_formats_hybrid_results_for_the_answer_model(self):
        tool_manager = Tools.__new__(Tools)
        tool_manager.vector_searchs = Mock()
        tool_manager.vector_searchs.vector_search.return_value = [
            Document(
                page_content="报销须在五个工作日内提交",
                metadata={"source": "制度.txt", "page": 3},
            )
        ]

        context = tool_manager.vector_search("报销时限")

        self.assertIn("[混合召回资料1]", context)
        self.assertIn("来源：制度.txt", context)
        self.assertIn("报销须在五个工作日内提交", context)


if __name__ == "__main__":
    unittest.main()
