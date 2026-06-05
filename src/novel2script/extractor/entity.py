"""Entity extraction via LLM."""

from __future__ import annotations

from novel2script.adapter.prompts import ENTITY_EXTRACTION_USER, SYSTEM_PROMPT
from novel2script.extractor.registry import EntityRegistry
from novel2script.llm.client import LLMClient
from novel2script.models.schema import EntityExtractionResult
from novel2script.parser.chapter import Chapter


def extract_entities(
    chapter: Chapter,
    registry: EntityRegistry,
    llm: LLMClient,
) -> EntityRegistry:
    user = ENTITY_EXTRACTION_USER.format(
        existing_characters=registry.characters_json(),
        existing_locations=registry.locations_json(),
        chapter_id=chapter.id,
        chapter_text=chapter.content[:8000],
    )
    result = llm.complete_json(SYSTEM_PROMPT, user, EntityExtractionResult)
    registry.merge_characters(result.characters)
    registry.merge_locations(result.locations)
    return registry
