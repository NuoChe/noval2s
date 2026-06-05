"""Tests for scene adapter post-processing."""

from novel2script.adapter.scene_adapter import SceneAdapter, _enrich_source_refs, _truncate_excerpt
from novel2script.extractor.registry import EntityRegistry
from novel2script.llm.client import MockLLMClient
from novel2script.models.enums import IntExt, TimeOfDay, WarningCode
from novel2script.models.schema import CharacterDraft, SceneDraft, Slugline
from novel2script.parser.chapter import Chapter


def test_truncate_excerpt():
    long_text = "字" * 250
    result = _truncate_excerpt(long_text, max_len=200)
    assert len(result) <= 200
    assert result.endswith("…")


def test_empty_source_refs_filled_from_chapter():
    chapter = Chapter(
        id="chapter_01",
        title="测试",
        content="第一段内容。\n\n第二段内容。",
        word_count=20,
        paragraphs=["第一段内容。", "第二段内容。"],
        index=0,
    )
    draft = SceneDraft(
        slugline=Slugline(
            int_ext=IntExt.INTERIOR,
            time_of_day=TimeOfDay.DAY,
            heading="内景 测试 - 日",
        ),
        source_refs=[],
        characters_present=["char_a"],
        elements=[],
    )
    enriched = _enrich_source_refs(draft, chapter)
    assert len(enriched.source_refs) >= 1
    assert enriched.source_refs[0].excerpt
    assert enriched.source_refs[0].chapter_id == "chapter_01"


def test_scene_ids_increment(mock_llm, mock_llm_responses):
    registry = EntityRegistry()
    registry.merge_characters([CharacterDraft(id="char_a", name="A")])
    adapter = SceneAdapter(mock_llm)
    chapter = Chapter(
        id="chapter_01",
        title="章1",
        content="内容",
        word_count=2,
        paragraphs=["内容"],
        index=0,
    )
    scenes1 = adapter.adapt_chapter(chapter, registry)
    chapter2 = Chapter(
        id="chapter_02",
        title="章2",
        content="内容2",
        word_count=2,
        paragraphs=["内容2"],
        index=1,
    )
    scenes2 = adapter.adapt_chapter(chapter2, registry)
    all_ids = [s.id for s in scenes1 + scenes2]
    assert all_ids == ["scene_001", "scene_002"]


def test_scene_split_warning(mock_llm, mock_llm_responses):
    mock_llm_responses["chapter_01"]["adaptation"]["scenes"].append(
        mock_llm_responses["chapter_01"]["adaptation"]["scenes"][0].copy()
    )
    mock_llm_responses["chapter_01"]["adaptation"]["scenes"][1]["slugline"] = {
        **mock_llm_responses["chapter_01"]["adaptation"]["scenes"][0]["slugline"],
        "heading": "内景 另一场景 - 日",
    }

    registry = EntityRegistry()
    adapter = SceneAdapter(mock_llm)
    chapter = Chapter(
        id="chapter_01",
        title="章1",
        content="内容",
        word_count=2,
        paragraphs=["内容"],
        index=0,
    )
    adapter.adapt_chapter(chapter, registry)
    codes = [str(w.code) for w in adapter.all_warnings]
    assert WarningCode.SCENE_SPLIT.value in codes
