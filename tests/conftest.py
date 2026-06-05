"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from novel2script.config import Settings
from novel2script.llm.client import MockLLMClient
from novel2script.models.enums import IntExt, TimeOfDay
from novel2script.models.schema import (
    ActionElement,
    AdaptationInfo,
    ChapterInfo,
    Character,
    DialogueElement,
    Location,
    Meta,
    Scene,
    Slugline,
    SourceInfo,
    SourceRef,
    Screenplay,
    TransitionElement,
    VoiceoverElement,
    build_meta,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
PD_NOVELS_DIR = FIXTURES_DIR / "novels"


def screenplay_factory(**overrides) -> Screenplay:
    """Build a minimal valid Screenplay for validator unit tests."""
    chapters = [
        ChapterInfo(id="chapter_01", title="第一章", word_count=100),
        ChapterInfo(id="chapter_02", title="第二章", word_count=100),
        ChapterInfo(id="chapter_03", title="第三章", word_count=100),
    ]
    meta = build_meta(
        title="测试作品",
        author="测试作者",
        chapters=chapters,
        model="test-model",
        prompt_version="v1.0-test",
    )
    characters = [
        Character(id="char_a", name="角色A"),
        Character(id="char_b", name="角色B"),
    ]
    locations = [
        Location(id="loc_main", name="主场景", int_ext=IntExt.INTERIOR),
    ]
    slugline = Slugline(
        int_ext=IntExt.INTERIOR,
        location_id="loc_main",
        time_of_day=TimeOfDay.DAY,
        heading="内景 主场景 - 日",
    )
    scenes = [
        Scene(
            id="scene_001",
            slugline=slugline,
            summary="第一场",
            source_refs=[
                SourceRef(chapter_id="chapter_01", excerpt="第一章摘要"),
            ],
            characters_present=["char_a", "char_b"],
            elements=[
                ActionElement(text="角色A走进房间。"),
                DialogueElement(character_id="char_a", lines="你好。"),
            ],
        ),
        Scene(
            id="scene_002",
            slugline=slugline.model_copy(update={"heading": "内景 主场景 - 夜"}),
            summary="第二场",
            source_refs=[
                SourceRef(chapter_id="chapter_02", excerpt="第二章摘要"),
            ],
            characters_present=["char_a"],
            elements=[ActionElement(text="夜戏。")],
        ),
        Scene(
            id="scene_003",
            slugline=slugline,
            summary="第三场",
            source_refs=[
                SourceRef(chapter_id="chapter_03", excerpt="第三章摘要"),
            ],
            characters_present=["char_b"],
            elements=[
                DialogueElement(character_id="char_b", lines="再见。"),
                TransitionElement(text="淡出。"),
            ],
        ),
    ]
    screenplay = Screenplay(
        meta=meta,
        characters=characters,
        locations=locations,
        scenes=scenes,
    )
    if overrides:
        data = screenplay.model_dump()
        data.update(overrides)
        return Screenplay.model_validate(data)
    return screenplay


@pytest.fixture
def settings() -> Settings:
    return Settings(
        llm_api_key="test-key",
        llm_model="mock-model",
        llm_provider="openai",
        min_chapters=3,
        max_chapters=20,
        max_words=100_000,
        prompt_version="v1.0-test",
    )


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def sample_novel_text() -> str:
    path = EXAMPLES_DIR / "sample-novel-chapters.txt"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def two_chapter_novel_text() -> str:
    return (FIXTURES_DIR / "novel_two_chapters.txt").read_text(encoding="utf-8")


@pytest.fixture
def empty_novel_text() -> str:
    return (FIXTURES_DIR / "novel_empty.txt").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def pd_novel_samples() -> list[dict]:
    """Load PD novel samples from manifest with file contents."""
    manifest_path = PD_NOVELS_DIR / "manifest.json"
    if not manifest_path.exists():
        return []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    samples = []
    for entry in manifest.get("samples", []):
        file_path = PD_NOVELS_DIR / entry["file"]
        samples.append(
            {
                **entry,
                "text": file_path.read_text(encoding="utf-8") if file_path.exists() else "",
                "path": file_path,
            }
        )
    return samples


@pytest.fixture
def minimal_screenplay() -> Screenplay:
    return screenplay_factory()


@pytest.fixture
def mock_llm_responses() -> dict:
    return {
        "entity": {
            "characters": [
                {
                    "id": "char_zhou_mo",
                    "name": "周默",
                    "aliases": [],
                    "description": "青年访客",
                },
                {
                    "id": "char_su_wan",
                    "name": "苏晚",
                    "aliases": ["晚晚"],
                    "description": "书店店主",
                },
            ],
            "locations": [
                {
                    "id": "loc_bookstore",
                    "name": "晚风书店",
                    "int_ext": "interior",
                    "description": "小书店",
                },
            ],
        },
        "chapter_01": {
            "entity": {
                "characters": [
                    {"id": "char_zhou_mo", "name": "周默", "aliases": [], "description": "青年"},
                    {"id": "char_su_wan", "name": "苏晚", "aliases": [], "description": "店主"},
                ],
                "locations": [
                    {"id": "loc_bookstore", "name": "晚风书店", "int_ext": "interior"},
                ],
            },
            "adaptation": {
                "scenes": [
                    {
                        "slugline": {
                            "int_ext": "interior",
                            "location_id": "loc_bookstore",
                            "time_of_day": "day",
                            "heading": "内景 晚风书店 - 日",
                        },
                        "summary": "周默与苏晚初遇",
                        "source_refs": [
                            {
                                "chapter_id": "chapter_01",
                                "excerpt": "周默推开了晚风书店的门",
                                "paragraph_range": [0, 2],
                            }
                        ],
                        "characters_present": ["char_zhou_mo", "char_su_wan"],
                        "elements": [
                            {"type": "action", "text": "周默推门进入书店。"},
                            {
                                "type": "dialogue",
                                "character_id": "char_su_wan",
                                "lines": "随便看。",
                            },
                            {
                                "type": "voiceover",
                                "character_id": "char_zhou_mo",
                                "text": "这家店真安静。",
                            },
                            {"type": "transition", "text": "切至"},
                        ],
                    }
                ],
                "warnings": [
                    {
                        "code": "TIME_INFERRED",
                        "message": "时间推断为日",
                        "severity": "warning",
                    }
                ],
            },
        },
        "chapter_02": {
            "entity": {"characters": [], "locations": []},
            "adaptation": {
                "scenes": [
                    {
                        "slugline": {
                            "int_ext": "interior",
                            "location_id": "loc_bookstore",
                            "time_of_day": "day",
                            "heading": "内景 晚风书店 - 日（次日）",
                        },
                        "summary": "误会",
                        "source_refs": [
                            {
                                "chapter_id": "chapter_02",
                                "excerpt": "周默再次来到晚风书店",
                                "paragraph_range": [0, 1],
                            }
                        ],
                        "characters_present": ["char_zhou_mo", "char_su_wan"],
                        "elements": [
                            {"type": "action", "text": "苏晚态度冷淡。"},
                            {
                                "type": "dialogue",
                                "character_id": "char_su_wan",
                                "lines": "有人预定了。",
                            },
                        ],
                    }
                ],
                "warnings": [],
            },
        },
        "chapter_03": {
            "entity": {"characters": [], "locations": []},
            "adaptation": {
                "scenes": [
                    {
                        "slugline": {
                            "int_ext": "interior",
                            "location_id": "loc_bookstore",
                            "time_of_day": "night",
                            "heading": "内景 晚风书店 - 夜",
                        },
                        "summary": "和解",
                        "source_refs": [
                            {
                                "chapter_id": "chapter_03",
                                "excerpt": "暴雨倾盆",
                                "paragraph_range": [0, 2],
                            }
                        ],
                        "characters_present": ["char_zhou_mo", "char_su_wan"],
                        "elements": [
                            {"type": "action", "text": "暴雨夜，周默避雨进入书店。"},
                            {
                                "type": "dialogue",
                                "character_id": "char_su_wan",
                                "lines": "昨天……我撒谎了。",
                            },
                            {
                                "type": "dialogue",
                                "character_id": "char_zhou_mo",
                                "lines": "成交。",
                            },
                        ],
                    }
                ],
                "warnings": [],
            },
        },
    }


@pytest.fixture
def mock_llm(mock_llm_responses: dict) -> MockLLMClient:
    return MockLLMClient(mock_llm_responses)
