"""Hybrid Search 和 Rerank 单元测试"""
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
project_root = str(Path(__file__).parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from unittest.mock import MagicMock, patch
from core.chunker.chunk_models import DocumentChunk


# ── RRF 融合算法测试 ────────────────────────────────────────────


class TestRRFFusion:
    """RRF 融合算法测试"""

    def test_rrf_fusion_basic(self):
        """测试 RRF 融合基本功能"""
        from core.vectorstore.retriever import HybridRetriever

        chunk_a = DocumentChunk(content="文档A", chunk_id="a")
        chunk_b = DocumentChunk(content="文档B", chunk_id="b")
        chunk_c = DocumentChunk(content="文档C", chunk_id="c")

        vector_results = [chunk_a, chunk_b]  # A 排第 1，B 排第 2
        bm25_results = [chunk_b, chunk_c]    # B 排第 1，C 排第 2

        fused = HybridRetriever._rrf_fusion(vector_results, bm25_results)

        # B 在两个列表中都出现，RRF 分数应该最高
        assert fused[0].chunk_id == "b"
        assert len(fused) == 3  # A, B, C 都应该在结果中

    def test_rrf_fusion_empty_inputs(self):
        """测试 RRF 融合空输入"""
        from core.vectorstore.retriever import HybridRetriever

        result = HybridRetriever._rrf_fusion([], [])
        assert result == []

    def test_rrf_fusion_one_empty(self):
        """测试一路为空"""
        from core.vectorstore.retriever import HybridRetriever

        chunk = DocumentChunk(content="test", chunk_id="x")
        result = HybridRetriever._rrf_fusion([chunk], [])
        assert len(result) == 1
        assert result[0].chunk_id == "x"

    def test_rrf_fusion_preserves_all_chunks(self):
        """测试 RRF 不丢失任何文档"""
        from core.vectorstore.retriever import HybridRetriever

        chunks_v = [DocumentChunk(content=f"v{i}", chunk_id=f"v{i}") for i in range(5)]
        chunks_b = [DocumentChunk(content=f"b{i}", chunk_id=f"b{i}") for i in range(5)]

        fused = HybridRetriever._rrf_fusion(chunks_v, chunks_b)
        assert len(fused) == 10


# ── Reranker 单元测试 ──────────────────────────────────────────


class TestReranker:
    """Reranker 单元测试"""

    def test_reranker_empty_chunks(self):
        """测试空输入"""
        from core.vectorstore.reranker import Reranker

        reranker = Reranker(api_key="test", base_url="http://test", model_name="test")
        result = reranker.rerank("query", [], top_n=5)
        assert result == []

    @patch("core.vectorstore.reranker.requests.post")
    def test_reranker_api_failure_fallback(self, mock_post):
        """测试 API 失败时的降级策略"""
        from core.vectorstore.reranker import Reranker

        mock_post.side_effect = Exception("API Error")

        chunks = [
            DocumentChunk(content="doc1", chunk_id="1"),
            DocumentChunk(content="doc2", chunk_id="2"),
        ]

        reranker = Reranker(api_key="test", base_url="http://test", model_name="test")
        result = reranker.rerank("query", chunks, top_n=2)

        # 应该降级返回原始顺序的前 top_n 个
        assert len(result) == 2
        assert result[0].chunk_id == "1"

    @patch("core.vectorstore.reranker.requests.post")
    def test_reranker_success(self, mock_post):
        """测试 Rerank 成功场景"""
        from core.vectorstore.reranker import Reranker

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"index": 1, "relevance_score": 0.95},
                {"index": 0, "relevance_score": 0.80},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        chunks = [
            DocumentChunk(content="doc1", chunk_id="1"),
            DocumentChunk(content="doc2", chunk_id="2"),
        ]

        reranker = Reranker(api_key="test", base_url="http://test", model_name="test")
        result = reranker.rerank("query", chunks, top_n=2)

        # doc2 (index=1) 应该排在前面（分数更高）
        assert result[0].chunk_id == "2"
        assert result[1].chunk_id == "1"

    @patch("core.vectorstore.reranker.requests.post")
    def test_reranker_top_n_limits(self, mock_post):
        """测试 top_n 截断"""
        from core.vectorstore.reranker import Reranker

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"index": 0, "relevance_score": 0.9},
                {"index": 1, "relevance_score": 0.8},
                {"index": 2, "relevance_score": 0.7},
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        chunks = [
            DocumentChunk(content=f"doc{i}", chunk_id=str(i)) for i in range(3)
        ]

        reranker = Reranker(api_key="test", base_url="http://test", model_name="test")
        result = reranker.rerank("query", chunks, top_n=2)

        assert len(result) == 2


# ── 引用校验测试 ────────────────────────────────────────────────


class TestCitationChecker:
    """CitationChecker 单元测试"""

    def test_missing_citation_is_invalid_when_chunks_exist(self):
        """有检索结果时，无引用回答不能视为通过"""
        from core.rag.citation_checker import CitationChecker

        checker = CitationChecker()
        result = checker.check("这是一个没有来源编号的回答", num_chunks=3)

        assert result.is_valid is False
        assert result.total_citations == 0

    def test_invalid_citation_is_stripped(self):
        """非法引用编号应被移除"""
        from core.rag.citation_checker import CitationChecker

        checker = CitationChecker()
        cleaned = checker.strip_invalid_citations("有效 [1]，无效 [9]", num_chunks=3)

        assert "[1]" in cleaned
        assert "[9]" not in cleaned


# ── 上传文件名安全测试 ──────────────────────────────────────────


class TestFileUtils:
    """上传文件工具测试"""

    def test_sanitize_filename_removes_path_segments(self):
        """文件名清洗应移除路径片段和非法字符"""
        from utils.file_utils import sanitize_filename

        safe_name = sanitize_filename("../bad\\name?.pdf")

        assert safe_name == "name_.pdf"
        assert "/" not in safe_name
        assert "\\" not in safe_name


# ── HybridRetriever 集成测试 ───────────────────────────────────


class TestHybridRetriever:
    """HybridRetriever 集成测试"""

    def test_retrieve_vector_only(self):
        """测试纯向量检索模式"""
        from core.vectorstore.retriever import HybridRetriever

        mock_store = MagicMock()
        chunks = [DocumentChunk(content=f"doc{i}", chunk_id=str(i)) for i in range(5)]
        mock_store.similarity_search.return_value = chunks

        retriever = HybridRetriever(chroma_store=mock_store)
        results = retriever.retrieve("test query", top_k=5, use_hybrid=False)

        assert len(results) == 5
        mock_store.similarity_search.assert_called_once()

    def test_format_context(self):
        """测试上下文格式化"""
        from core.vectorstore.retriever import HybridRetriever

        mock_store = MagicMock()
        retriever = HybridRetriever(chroma_store=mock_store)

        chunks = [
            DocumentChunk(
                content="测试内容",
                chunk_id="1",
                metadata={"source_file": "test.pdf", "header_path": "第一章"},
            )
        ]

        context = retriever.format_context(chunks)
        assert "[1]" in context
        assert "test.pdf" in context
        assert "第一章" in context
        assert "测试内容" in context

    def test_format_context_empty(self):
        """测试空结果格式化"""
        from core.vectorstore.retriever import HybridRetriever

        mock_store = MagicMock()
        retriever = HybridRetriever(chroma_store=mock_store)

        context = retriever.format_context([])
        assert "无相关上下文" in context

    def test_format_context_multiple_chunks(self):
        """测试多文档格式化"""
        from core.vectorstore.retriever import HybridRetriever

        mock_store = MagicMock()
        retriever = HybridRetriever(chroma_store=mock_store)

        chunks = [
            DocumentChunk(content=f"内容{i}", chunk_id=str(i), metadata={"source_file": f"f{i}.pdf", "header_path": f"章节{i}"})
            for i in range(3)
        ]

        context = retriever.format_context(chunks)
        assert "[1]" in context
        assert "[2]" in context
        assert "[3]" in context

    def test_retrieve_with_reranker(self):
        """测试带 Reranker 的检索"""
        from core.vectorstore.retriever import HybridRetriever

        mock_store = MagicMock()
        chunks = [DocumentChunk(content=f"doc{i}", chunk_id=str(i)) for i in range(10)]
        mock_store.similarity_search.return_value = chunks

        mock_reranker = MagicMock()
        mock_reranker.rerank.return_value = chunks[:3]

        retriever = HybridRetriever(chroma_store=mock_store, reranker=mock_reranker)
        results = retriever.retrieve("test query", top_k=3, use_hybrid=False)

        assert len(results) == 3
        mock_reranker.rerank.assert_called_once()


# ── 评估器单元测试 ──────────────────────────────────────────────


class TestRAGEvaluator:
    """RAGEvaluator 单元测试"""

    def test_evaluate_single(self):
        """测试单次评估"""
        from core.rag.evaluator import RAGEvaluator
        from core.rag.agent import AgentResponse, AgentStep

        mock_agent = MagicMock()
        mock_agent.run.return_value = AgentResponse(
            final_answer="回答 [1] 引用 [2] 引用",
            steps=[],
            total_iterations=2,
            was_interrupted=False,
            sources=["doc1.pdf", "doc2.pdf"],
        )
        mock_retriever = MagicMock()

        evaluator = RAGEvaluator(mock_agent, mock_retriever)
        result = evaluator.evaluate_single("测试问题")

        assert result.question == "测试问题"
        assert result.iterations == 2
        assert result.retrieval_count == 2
        assert result.citation_rate == 1.0  # 2 citations / 2 sources
        assert result.response_time >= 0

    def test_evaluate_batch(self):
        """测试批量评估"""
        from core.rag.evaluator import RAGEvaluator
        from core.rag.agent import AgentResponse

        mock_agent = MagicMock()
        mock_agent.run.return_value = AgentResponse(
            final_answer="答案 [1]",
            steps=[],
            total_iterations=1,
            was_interrupted=False,
            sources=["s.pdf"],
        )
        mock_retriever = MagicMock()

        evaluator = RAGEvaluator(mock_agent, mock_retriever)
        report = evaluator.evaluate_batch(["问题1", "问题2"])

        assert report.total_questions == 2
        assert len(report.results) == 2
        assert report.avg_iterations == 1.0

    def test_evaluate_batch_empty(self):
        """测试空批量评估"""
        from core.rag.evaluator import RAGEvaluator

        mock_agent = MagicMock()
        mock_agent.run.side_effect = Exception("fail")
        mock_retriever = MagicMock()

        evaluator = RAGEvaluator(mock_agent, mock_retriever)
        report = evaluator.evaluate_batch(["q1"])

        assert report.total_questions == 1
        assert len(report.results) == 0
        assert report.avg_response_time == 0

    def test_batch_report_to_dict(self):
        """测试报告转字典"""
        from core.rag.evaluator import BatchEvaluationReport, EvaluationResult

        result = EvaluationResult(
            question="q",
            answer="a" * 300,
            sources=["s"],
            response_time=1.5,
            citation_rate=0.8,
            retrieval_count=5,
            iterations=2,
            judge_score=0.9,
        )
        report = BatchEvaluationReport(
            total_questions=1,
            avg_response_time=1.5,
            avg_citation_rate=0.8,
            avg_iterations=2.0,
            avg_judge_score=0.9,
            results=[result],
        )

        d = report.to_dict()
        assert d["total_questions"] == 1
        assert d["avg_response_time"] == 1.5
        assert len(d["results"]) == 1
        # 答案超过200字应被截断
        assert d["results"][0]["answer_preview"].endswith("...")
