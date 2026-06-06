"""V2 model registry: catalog, availability, and request-scoped settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from novel2script.config import Settings
from novel2script.exceptions import Novel2ScriptError
from novel2script.llm.client import resolve_model_name


class ModelNotConfiguredError(Novel2ScriptError):
    """API key for the requested model is not configured."""


class UnknownModelError(Novel2ScriptError):
    """model_id is not in the catalog."""


@dataclass(frozen=True)
class ModelEntry:
    id: str
    display_name: str
    provider: str
    model: str
    base_url: str | None
    env_keys: tuple[str, ...]
    description: str = ""


MODEL_CATALOG: dict[str, ModelEntry] = {
    "openai-gpt-4o-mini": ModelEntry(
        id="openai-gpt-4o-mini",
        display_name="GPT-4o Mini",
        provider="openai",
        model="gpt-4o-mini",
        base_url=None,
        env_keys=("OPENAI_API_KEY", "LLM_API_KEY"),
        description="质量稳定、演示",
    ),
    "qwen-plus": ModelEntry(
        id="qwen-plus",
        display_name="通义千问 Plus",
        provider="dashscope",
        model="qwen-plus",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        env_keys=("DASHSCOPE_API_KEY",),
        description="国内部署、中文理解",
    ),
    "zhipu-glm-5.1": ModelEntry(
        id="zhipu-glm-5.1",
        display_name="智谱 GLM-5.1",
        provider="zai",
        model="glm-5.1",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        env_keys=("ZAI_API_KEY",),
        description="长文本、推理",
    ),
    "kimi-moonshot-32k": ModelEntry(
        id="kimi-moonshot-32k",
        display_name="Kimi 32K",
        provider="moonshot",
        model="moonshot-v1-32k",
        base_url="https://api.moonshot.cn/v1",
        env_keys=("MOONSHOT_API_KEY",),
        description="长上下文改编",
    ),
    "deepseek-chat": ModelEntry(
        id="deepseek-chat",
        display_name="DeepSeek Chat",
        provider="deepseek",
        model="deepseek-chat",
        base_url="https://api.deepseek.com",
        env_keys=("DEEPSEEK_API_KEY", "LLM_API_KEY"),
        description="性价比、中文推理",
    ),
}


def _read_env_key(env_keys: tuple[str, ...]) -> str:
    for key in env_keys:
        value = os.getenv(key, "").strip()
        if value:
            return value
    return ""


def _settings_fallback_key(entry: ModelEntry, settings: Settings) -> str:
    api_key = settings.llm_api_key.strip()
    if not api_key:
        return ""
    if entry.id == "openai-gpt-4o-mini" and settings.llm_provider == "openai":
        return api_key
    if entry.id == "deepseek-chat" and settings.llm_provider == "deepseek":
        return api_key
    return ""


def get_api_key(entry: ModelEntry, settings: Settings | None = None) -> str:
    key = _read_env_key(entry.env_keys)
    if key:
        return key
    if settings is None:
        from novel2script.config import get_settings

        settings = get_settings()
    return _settings_fallback_key(entry, settings)


def is_model_available(entry: ModelEntry, settings: Settings | None = None) -> bool:
    return bool(get_api_key(entry, settings))


def get_default_model_id(settings: Settings | None = None) -> str:
    from novel2script.config import get_settings

    settings = settings or get_settings()
    model_id = settings.default_model_id.strip()
    if model_id in MODEL_CATALOG:
        return model_id
    return "openai-gpt-4o-mini"


def list_models(settings: Settings | None = None) -> list[dict[str, Any]]:
    from novel2script.config import get_settings

    settings = settings or get_settings()
    default_id = get_default_model_id(settings)
    return [
        {
            "id": entry.id,
            "name": entry.display_name,
            "provider": entry.provider,
            "available": is_model_available(entry, settings),
            "description": entry.description,
        }
        for entry in MODEL_CATALOG.values()
    ]


def resolve_model(model_id: str, settings: Settings | None = None) -> ModelEntry:
    from novel2script.config import get_settings

    settings = settings or get_settings()
    entry = MODEL_CATALOG.get(model_id)
    if entry is None:
        raise UnknownModelError(f"Unknown model_id: {model_id}")
    if not is_model_available(entry, settings):
        raise ModelNotConfiguredError(
            f"API key not configured for model '{model_id}'. "
            f"Set one of: {', '.join(entry.env_keys)}"
        )
    return entry


def litellm_model_name(entry: ModelEntry) -> str:
    return resolve_model_name(entry.provider, entry.model)


def settings_for_model_id(base: Settings, model_id: str) -> Settings:
    entry = resolve_model(model_id, base)
    updates: dict[str, Any] = {
        "llm_provider": entry.provider,
        "llm_model": entry.model,
        "llm_api_key": get_api_key(entry, base),
        "llm_base_url": entry.base_url,
    }
    return base.model_copy(update=updates)


def build_llm_client(model_id: str | None, base_settings: Settings | None = None):
    from novel2script.config import get_settings
    from novel2script.llm.client import LiteLLMClient

    base = base_settings or get_settings()
    mid = model_id or get_default_model_id(base)
    request_settings = settings_for_model_id(base, mid)
    entry = resolve_model(mid, base)
    return LiteLLMClient(request_settings), request_settings, litellm_model_name(entry)
