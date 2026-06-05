"""Tests for schema validation."""

from pathlib import Path

from novel2script.emitter.yaml_writer import load_screenplay
from novel2script.models.enums import ValidationStatus
from novel2script.models.schema import (
    ActionElement,
    Act,
    DialogueElement,
    VoiceoverElement,
)
from novel2script.validator.validate import load_and_validate_yaml, validate_screenplay

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_sample_screenplay_passes():
    result = load_and_validate_yaml(EXAMPLES_DIR / "sample-screenplay.yaml")
    assert result.status in (ValidationStatus.PASS, ValidationStatus.PASS_WITH_WARNINGS)
    assert not result.errors
    assert all(result.chapter_coverage.values())


def test_invalid_character_reference_fails():
    screenplay = load_screenplay(EXAMPLES_DIR / "sample-screenplay.yaml")
    scene = screenplay.scenes[0]
    scene.characters_present = ["char_nonexistent"]
    result = validate_screenplay(screenplay)
    assert result.status == ValidationStatus.FAIL
    assert any("unknown character" in e for e in result.errors)


def test_missing_chapter_coverage_fails():
    screenplay = load_screenplay(EXAMPLES_DIR / "sample-screenplay.yaml")
    for scene in screenplay.scenes:
        scene.source_refs = [
            ref for ref in scene.source_refs if ref.chapter_id != "chapter_03"
        ]
    result = validate_screenplay(screenplay)
    assert result.status == ValidationStatus.FAIL
    assert result.chapter_coverage.get("chapter_03") is False


def test_invalid_schema_version(minimal_screenplay):
    minimal_screenplay.schema_version = "0.9"  # type: ignore[assignment]
    result = validate_screenplay(minimal_screenplay)
    assert result.status == ValidationStatus.FAIL
    assert any("schema_version" in e for e in result.errors)


def test_chapter_count_below_three(minimal_screenplay):
    minimal_screenplay.meta.source.chapter_count = 2
    result = validate_screenplay(minimal_screenplay)
    assert result.status == ValidationStatus.FAIL


def test_chapter_count_mismatch(minimal_screenplay):
    minimal_screenplay.meta.source.chapter_count = 5
    result = validate_screenplay(minimal_screenplay)
    assert result.status == ValidationStatus.FAIL
    assert any("chapter_count" in e for e in result.errors)


def test_empty_scenes(minimal_screenplay):
    minimal_screenplay.scenes = []
    result = validate_screenplay(minimal_screenplay)
    assert result.status == ValidationStatus.FAIL
    assert any("scene" in e.lower() for e in result.errors)


def test_invalid_location_ref(minimal_screenplay):
    minimal_screenplay.scenes[0].slugline.location_id = "loc_nonexistent"
    result = validate_screenplay(minimal_screenplay)
    assert result.status == ValidationStatus.FAIL
    assert any("location_id" in e for e in result.errors)


def test_invalid_act_scene_ref(minimal_screenplay):
    minimal_screenplay.acts = [Act(id="act_1", scenes=["scene_999"])]
    result = validate_screenplay(minimal_screenplay)
    assert result.status == ValidationStatus.FAIL
    assert any("scene_999" in e for e in result.errors)


def test_dialogue_unknown_character(minimal_screenplay):
    minimal_screenplay.scenes[0].elements = [
        DialogueElement(character_id="char_unknown", lines="测试")
    ]
    result = validate_screenplay(minimal_screenplay)
    assert result.status == ValidationStatus.FAIL
    assert any("dialogue" in e for e in result.errors)


def test_voiceover_unknown_character(minimal_screenplay):
    minimal_screenplay.scenes[0].elements = [
        VoiceoverElement(character_id="char_unknown", text="内心独白")
    ]
    result = validate_screenplay(minimal_screenplay)
    assert result.status == ValidationStatus.FAIL


def test_action_too_long_warning(minimal_screenplay):
    long_action = ActionElement(text="\n".join(f"动作行{i}" for i in range(6)))
    minimal_screenplay.scenes[0].elements = [long_action]
    result = validate_screenplay(minimal_screenplay)
    assert result.status == ValidationStatus.PASS_WITH_WARNINGS
    assert any("ACTION_TOO_LONG" in str(w.code) for w in result.warnings)


def test_voiceover_excess_warning(minimal_screenplay):
    minimal_screenplay.scenes[0].elements = [
        VoiceoverElement(character_id="char_a", text="旁白1"),
        VoiceoverElement(character_id="char_a", text="旁白2"),
        VoiceoverElement(character_id="char_a", text="旁白3"),
    ]
    result = validate_screenplay(minimal_screenplay)
    assert result.status == ValidationStatus.PASS_WITH_WARNINGS
    assert any("VOICEOVER_EXCESS" in str(w.code) for w in result.warnings)


def test_load_invalid_yaml_file():
    result = load_and_validate_yaml(FIXTURES_DIR / "invalid_missing_meta.yaml")
    assert result.status == ValidationStatus.FAIL
    assert result.errors


def test_load_bad_character_ref_fixture():
    result = load_and_validate_yaml(FIXTURES_DIR / "invalid_bad_character_ref.yaml")
    assert result.status == ValidationStatus.FAIL


def test_load_two_chapters_meta_fixture():
    result = load_and_validate_yaml(FIXTURES_DIR / "invalid_two_chapters_meta.yaml")
    assert result.status == ValidationStatus.FAIL


def test_sample_has_all_element_types():
    screenplay = load_screenplay(EXAMPLES_DIR / "sample-screenplay.yaml")
    types = {elem.type for scene in screenplay.scenes for elem in scene.elements}
    assert "action" in types
    assert "dialogue" in types
    assert "transition" in types
