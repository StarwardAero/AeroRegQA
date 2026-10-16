"""FastAPI 接口集成测试"""
import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
project_root = str(Path(__file__).parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


# ── 辅助：用 mock 替换 get_services 以避免真实初始化 ──────────────


def _make_mock_services():
    """构造一组 mock 服务，用于 FastAPI 依赖注入"""
    mock_chroma = MagicMock()
    mock_chroma.get_collection_stats.return_value = {"total_chunks": 10}
    mock_chroma.list_sources.return_value = ["doc1.pdf", "doc2.pdf"]

    mock_agent = MagicMock()
    mock_retriever = MagicMock()
    mock_conv_manager = MagicMock()
    mock_chunker = MagicMock()
    mock_embedder = MagicMock()
    mock_router = MagicMock()
    mock_registry = MagicMock()
    mock_redis = MagicMock()
    mock_mysql = MagicMock()

    mock_router.route.return_value = MagicMock(
        skill_name="rag",
        confidence=0.95,
        method="mock",
        fallback_skills=[],
    )
    mock_registry.get.return_value = MagicMock()
    mock_redis.get_cached_answer.return_value = None
    mock_redis.cache_answer.return_value = None
    mock_mysql.log_skill_call.return_value = None

    return {
        "chroma_store": mock_chroma,
        "agent": mock_agent,
        "retriever": mock_retriever,
        "conversation_manager": mock_conv_manager,
        "chunker": mock_chunker,
        "parser_factory": MagicMock(),
        "embedder": mock_embedder,
        "intent_router": mock_router,
        "skill_registry": mock_registry,
        "redis_client": mock_redis,
        "mysql_client": mock_mysql,
    }


@pytest.fixture(autouse=True)
def mock_services():
    """自动 mock get_services，避免需要真实 API key"""
    services = _make_mock_services()
    with patch("api.dependencies.get_services", return_value=services), \
         patch("api.routes.chat.get_services", return_value=services), \
         patch("api.routes.knowledge.get_services", return_value=services), \
         patch("api.routes.conversation.get_services", return_value=services), \
         patch("api.routes.evaluate.get_agent", return_value=services["agent"]), \
         patch("api.routes.evaluate.get_retriever", return_value=services["retriever"]):
        yield services


@pytest.fixture
def client():
    from api.main import app
    return TestClient(app)


# ── 健康检查 ────────────────────────────────────────────────────


class TestHealthEndpoint:
    """健康检查接口测试"""

    def test_health_check(self, client, mock_services):
        """测试健康检查接口返回正常"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "knowledge_base_stats" in data


# ── 问答接口 ────────────────────────────────────────────────────


class TestChatEndpoints:
    """问答接口测试"""

    def test_chat_sync_requires_question(self, client):
        """测试同步问答接口需要 question 字段"""
        response = client.post("/api/chat/sync", json={})
        assert response.status_code == 422  # Validation error

    def test_chat_sync_accepts_valid_request(self, client, mock_services):
        """测试同步问答接口接受有效请求格式"""
        from core.skills.base_skill import SkillResult

        mock_skill = MagicMock()
        mock_skill.execute.return_value = SkillResult(
            answer="测试回答",
            sources=["doc1.pdf"],
            skill_name="rag",
            iterations=1,
        )
        mock_services["skill_registry"].get.return_value = mock_skill

        # Mock conversation_manager 方法
        mock_conv = MagicMock()
        mock_conv.conversation_id = "test-conv-id"
        mock_services["conversation_manager"].create_conversation.return_value = mock_conv
        mock_services["conversation_manager"].get_chat_history.return_value = []
        mock_services["conversation_manager"].add_message.return_value = None
        mock_services["conversation_manager"].auto_generate_title.return_value = None

        response = client.post("/api/chat/sync", json={"question": "什么是适航证？"})
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "测试回答"
        assert data["conversation_id"] == "test-conv-id"


# ── 知识库接口 ──────────────────────────────────────────────────


class TestKnowledgeEndpoints:
    """知识库接口测试"""

    def test_list_sources(self, client, mock_services):
        """测试知识库文件列表接口"""
        mock_services["chroma_store"].list_sources.return_value = ["a.pdf", "b.pdf"]
        response = client.get("/api/knowledge/sources")
        assert response.status_code == 200
        data = response.json()
        assert "sources" in data or isinstance(data, list)


# ── 对话管理接口 ────────────────────────────────────────────────


class TestConversationEndpoints:
    """对话管理接口测试"""

    def test_list_conversations(self, client, mock_services):
        """测试对话列表接口"""
        mock_services["conversation_manager"].list_conversations.return_value = []
        response = client.get("/api/conversations")
        assert response.status_code == 200


# ── 评估接口 ────────────────────────────────────────────────────


class TestEvaluateEndpoints:
    """评估接口测试"""

    def test_evaluate_requires_questions(self, client):
        """测试评估接口需要 questions 字段"""
        response = client.post("/api/evaluate", json={})
        assert response.status_code == 422

    def test_evaluate_valid_request(self, client, mock_services):
        """测试评估接口接受有效请求并返回报告"""
        from core.rag.agent import AgentResponse

        mock_agent = mock_services["agent"]
        mock_agent.run.return_value = AgentResponse(
            final_answer="回答 [1] 引用",
            steps=[],
            total_iterations=2,
            was_interrupted=False,
            sources=["doc1.pdf"],
        )

        response = client.post("/api/evaluate", json={"questions": ["适航证是什么？"]})
        assert response.status_code == 200
        data = response.json()
        assert data["total_questions"] == 1
        assert "avg_response_time" in data
        assert "results" in data
        assert len(data["results"]) == 1
