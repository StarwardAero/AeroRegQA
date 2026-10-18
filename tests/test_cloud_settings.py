import sys
import streamlit
from streamlit.errors import StreamlitSecretNotFoundError

from config.settings import Settings, _cloud_llm_overrides


def test_cloud_llm_section_overrides_legacy_model_but_not_embeddings(monkeypatch):
    monkeypatch.setenv("LLM_MODEL_NAME", "legacy-model")
    monkeypatch.setenv("EMBEDDING_MODEL_NAME", "existing-embedding")
    monkeypatch.setattr(streamlit, "secrets", {
        "aeroregqa_llm": {
            "LLM_MODEL_NAME": "deepseek-v4-pro",
            "LLM_BASE_URL": "https://api.deepseek.com/v1",
            "LLM_THINKING_MODE": "enabled",
            "EMBEDDING_MODEL_NAME": "must-not-override",
        }
    })
    settings = Settings(**_cloud_llm_overrides())
    assert settings.LLM_MODEL_NAME == "deepseek-v4-pro"
    assert settings.LLM_BASE_URL == "https://api.deepseek.com/v1"
    assert settings.LLM_THINKING_MODE == "enabled"
    assert settings.EMBEDDING_MODEL_NAME == "existing-embedding"


def test_cloud_llm_section_is_optional(monkeypatch):
    monkeypatch.setattr(streamlit, "secrets", {})
    assert _cloud_llm_overrides() == {}


def test_missing_local_secrets_is_supported(monkeypatch):
    class MissingSecrets:
        def get(self, *args):
            raise StreamlitSecretNotFoundError("No local secrets file")
    monkeypatch.setattr(streamlit, "secrets", MissingSecrets())
    assert _cloud_llm_overrides() == {}
    monkeypatch.delitem(sys.modules, "streamlit")
    assert _cloud_llm_overrides() == {}
