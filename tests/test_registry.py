"""Tests for entity registry."""

from novel2script.extractor.registry import EntityRegistry
from novel2script.models.schema import CharacterDraft, LocationDraft


def test_merge_characters_deduplicates_aliases():
    registry = EntityRegistry()
    registry.merge_characters(
        [CharacterDraft(name="周默", aliases=["小周"], description="主角")]
    )
    registry.merge_characters(
        [CharacterDraft(name="小周", aliases=[], description="同一人")]
    )
    assert len(registry.characters) == 1
    char = registry.characters_list()[0]
    assert char.name == "周默"
    assert "小周" in char.aliases


def test_merge_locations():
    registry = EntityRegistry()
    registry.merge_locations(
        [LocationDraft(name="晚风书店", int_ext="interior")]
    )
    registry.merge_locations(
        [LocationDraft(name="晚风书店", int_ext="interior")]
    )
    assert len(registry.locations) == 1
