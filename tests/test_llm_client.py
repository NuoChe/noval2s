"""Tests for LLM client."""

import pytest

from novel2script.llm.client import MockLLMClient, _extract_json, resolve_model_name
from novel2script.models.schema import AdaptationChapterResult, EntityExtractionResult


def test_resolve_model_name_deepseek():
    assert resolve_model_name("deepseek", "deepseek-v4-pro") == "deepseek/deepseek-v4-pro"
    assert resolve_model_name("deepseek", "deepseek-chat") == "deepseek/deepseek-chat"
    assert resolve_model_name("deepseek", "deepseek/deepseek-v4-pro") == "deepseek/deepseek-v4-pro"


def test_extract_json_from_markdown_fence():
    raw = '```json\n{"characters": [], "locations": []}\n```'
    data = _extract_json(raw)
    assert data == {"characters": [], "locations": []}


def test_extract_json_plain():
    data = _extract_json('{"scenes": [], "warnings": []}')
    assert "scenes" in data


def test_mock_llm_entity_extraction(mock_llm):
    result = mock_llm.complete_json(
        "system",
        "从以下小说章节中抽取 existing_characters\n章节 ID：chapter_01\n章节文本：测试",
        EntityExtractionResult,
    )
    assert len(result.characters) >= 1


def test_mock_llm_adaptation(mock_llm):
    result = mock_llm.complete_json(
        "system",
        "将以下小说章节改编为剧本场次\n章节 ID：chapter_01\nscenes",
        AdaptationChapterResult,
    )
    assert len(result.scenes) >= 1


def test_mock_llm_tracks_calls(mock_llm):
    assert len(mock_llm.calls) == 0
    mock_llm.complete_json("s", "抽取 existing_characters", EntityExtractionResult)
    mock_llm.complete_json("s", "改编 scenes", AdaptationChapterResult)
    assert len(mock_llm.calls) == 2
