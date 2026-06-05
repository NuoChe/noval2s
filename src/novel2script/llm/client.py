"""LiteLLM client with JSON parsing and retries."""

from __future__ import annotations

import json
import re
import time
from typing import Protocol, TypeVar

import litellm
from pydantic import BaseModel

from novel2script.config import Settings, get_settings
from novel2script.exceptions import LLMError

T = TypeVar("T", bound=BaseModel)


class LLMClient(Protocol):
    def complete_json(
        self,
        system: str,
        user: str,
        response_model: type[T],
    ) -> T: ...


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise LLMError(f"Failed to parse LLM JSON response: {exc}") from exc


def resolve_model_name(provider: str, model: str) -> str:
    """Normalize model string for LiteLLM."""
    model = model.strip()
    if provider == "ollama":
        return f"ollama/{model.removeprefix('ollama/')}"
    if provider == "deepseek" or model.startswith("deepseek"):
        if model.startswith("deepseek/"):
            return model
        return f"deepseek/{model}"
    if "/" not in model and provider not in ("openai", "ollama"):
        return f"{provider}/{model}"
    return model


class LiteLLMClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if self.settings.llm_api_key:
            litellm.api_key = self.settings.llm_api_key

    @property
    def model_name(self) -> str:
        return resolve_model_name(self.settings.llm_provider, self.settings.llm_model)

    def _completion_kwargs(self, system: str, user: str) -> dict:
        kwargs: dict = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.3,
        }
        if self.settings.llm_base_url:
            kwargs["api_base"] = self.settings.llm_base_url
        if self.settings.llm_api_key:
            kwargs["api_key"] = self.settings.llm_api_key
        return kwargs

    def complete_json(
        self,
        system: str,
        user: str,
        response_model: type[T],
        *,
        retries: int = 3,
    ) -> T:
        last_error: Exception | None = None
        extra_user = user

        for attempt in range(retries):
            try:
                kwargs = self._completion_kwargs(system, extra_user)

                try:
                    kwargs["response_format"] = {"type": "json_object"}
                    response = litellm.completion(**kwargs)
                except Exception:
                    kwargs.pop("response_format", None)
                    response = litellm.completion(**kwargs)

                content = response.choices[0].message.content or ""
                data = _extract_json(content)
                return response_model.model_validate(data)

            except Exception as exc:
                last_error = exc
                if attempt < retries - 1:
                    time.sleep(2**attempt)
                    extra_user = user + "\n\n请仅输出合法 JSON，不要包含 markdown 代码块或其他文字。"
                    continue

        raise LLMError(f"LLM request failed after {retries} attempts: {last_error}") from last_error


class MockLLMClient:
    """Test double that returns pre-configured responses by prompt keyword."""

    def __init__(self, responses: dict[str, dict | list[dict]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str]] = []

    def complete_json(
        self,
        system: str,
        user: str,
        response_model: type[T],
    ) -> T:
        self.calls.append((system, user))

        if "抽取" in user or "existing_characters" in user:
            key = "entity"
            chapter_key = None
            for line in user.split("\n"):
                if line.startswith("章节 ID："):
                    chapter_key = line.replace("章节 ID：", "").strip()
                    break
            if chapter_key and chapter_key in self.responses:
                data = self.responses[chapter_key]["entity"]
            else:
                data = self.responses.get("entity", {"characters": [], "locations": []})
            return response_model.model_validate(data)

        if "改编" in user or "scenes" in user:
            chapter_key = None
            for line in user.split("\n"):
                if line.startswith("章节 ID："):
                    chapter_key = line.replace("章节 ID：", "").strip()
                    break
            if chapter_key and chapter_key in self.responses:
                data = self.responses[chapter_key]["adaptation"]
            else:
                data = self.responses.get("adaptation", {"scenes": [], "warnings": []})
            return response_model.model_validate(data)

        return response_model.model_validate({})
