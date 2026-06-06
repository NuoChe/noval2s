"""Application configuration via environment variables."""

import os
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )

    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str = ""
    llm_base_url: str | None = None

    default_model_id: str = "openai-gpt-4o-mini"
    auth_secret: str = "dev-insecure-change-me"
    auth_demo_users: str = ""

    max_chapters: int = 20
    max_words: int = 100_000
    prompt_version: str = "v1.0"

    min_chapters: int = 3

    @model_validator(mode="after")
    def fill_provider_defaults(self) -> "Settings":
        if not self.llm_api_key:
            openai_key = os.getenv("OPENAI_API_KEY", "") or os.getenv("LLM_API_KEY", "")
            if openai_key:
                self.llm_api_key = openai_key
        if not self.llm_api_key and self.llm_provider == "deepseek":
            self.llm_api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if self.llm_provider == "deepseek" and not self.llm_base_url:
            self.llm_base_url = "https://api.deepseek.com"
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
