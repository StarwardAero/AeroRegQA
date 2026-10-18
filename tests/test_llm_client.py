from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from core.rag.llm_client import LLMClient


@pytest.mark.parametrize("method", ["chat", "chat_with_usage"])
@pytest.mark.parametrize("mode", ["enabled", "disabled"])
def test_official_v4_explicit_thinking_mode(method, mode):
    client = LLMClient("test-key", "https://api.deepseek.com/v1", "deepseek-v4-pro", 0.7, 512, mode)
    create = Mock(return_value=SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="OK"))], usage=None,
    ))
    client.client.chat.completions.create = create
    result = getattr(client, method)([{"role": "user", "content": "test"}])
    assert (result if method == "chat" else result["content"]) == "OK"
    assert create.call_args.kwargs["extra_body"] == {"thinking": {"type": mode}}


@pytest.mark.parametrize("url,model", [
    ("https://api.siliconflow.cn/v1", "deepseek-ai/DeepSeek-V3"),
    ("https://example.com/v1", "deepseek-v4-pro"),
    ("https://api.deepseek.com/v1", "deepseek-reasoner"),
])
def test_other_providers_keep_compatible_request(url, model):
    client = LLMClient("test-key", url, model, 0.7, 512)
    create = Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="OK"))]))
    client.client.chat.completions.create = create
    assert client.chat([]) == "OK"
    assert "extra_body" not in create.call_args.kwargs


def test_stream_ignores_empty_usage_chunk():
    client = LLMClient("test-key", "https://api.deepseek.com/v1", "deepseek-v4-pro", 0.7, 512)
    client.client.chat.completions.create = Mock(return_value=iter([
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="OK"))]),
        SimpleNamespace(choices=[]),
    ]))
    assert "".join(client.chat([], stream=True)) == "OK"
