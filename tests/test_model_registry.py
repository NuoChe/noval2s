"""Model registry tests."""

import pytest

from novel2script.config import Settings, get_settings
from novel2script.llm.registry import (
    MODEL_CATALOG,
    ModelNotConfiguredError,
    UnknownModelError,
    get_default_model_id,
    is_model_available,
    list_models,
    resolve_model,
    settings_for_model_id,
)


def test_catalog_has_five_models():
    assert len(MODEL_CATALOG) == 5
    assert "deepseek-chat" in MODEL_CATALOG


def test_resolve_unknown_model():
    with pytest.raises(UnknownModelError):
        resolve_model("not-a-model", Settings())


def test_resolve_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    get_settings.cache_clear()
    empty = Settings(llm_api_key="", llm_provider="openai")
    with pytest.raises(ModelNotConfiguredError):
        resolve_model("openai-gpt-4o-mini", empty)


def test_available_via_settings_without_env(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    settings = Settings(llm_api_key="sk-from-settings", llm_provider="deepseek")
    assert is_model_available(MODEL_CATALOG["deepseek-chat"], settings)
    resolved = resolve_model("deepseek-chat", settings)
    assert resolved.id == "deepseek-chat"


def test_settings_for_model_id(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    get_settings.cache_clear()
    settings = Settings()
    resolved = settings_for_model_id(settings, "deepseek-chat")
    assert resolved.llm_provider == "deepseek"
    assert resolved.llm_model == "deepseek-chat"
    assert resolved.llm_api_key == "sk-test"
    assert resolved.llm_base_url == "https://api.deepseek.com"


def test_list_models_marks_availability(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    get_settings.cache_clear()
    settings = Settings(llm_provider="openai")
    models = list_models(settings)
    openai = next(m for m in models if m["id"] == "openai-gpt-4o-mini")
    deepseek = next(m for m in models if m["id"] == "deepseek-chat")
    assert openai["available"] is True
    assert deepseek["available"] is False


def test_list_models_deepseek_via_llm_api_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "sk-shared")
    get_settings.cache_clear()
    models = list_models(Settings(llm_provider="deepseek"))
    deepseek = next(m for m in models if m["id"] == "deepseek-chat")
    assert deepseek["available"] is True


def test_default_model_id_fallback():
    assert get_default_model_id(Settings(default_model_id="invalid")) == "openai-gpt-4o-mini"
