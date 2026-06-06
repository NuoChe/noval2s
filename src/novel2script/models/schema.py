"""Pydantic models aligned with docs/YAML-SCHEMA.md."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from novel2script.models.enums import (
    IntExt,
    TimeOfDay,
    WarningCode,
    WarningSeverity,
)

SCHEMA_VERSION = "1.0"


class ChapterInfo(BaseModel):
    id: str
    title: str
    word_count: int


class SourceInfo(BaseModel):
    format: Literal["novel"] = "novel"
    chapter_count: int
    chapters: list[ChapterInfo]


class AdaptationInfo(BaseModel):
    created_at: str
    model: str
    prompt_version: str


class Meta(BaseModel):
    title: str
    author: str
    adapted_by: str | None = None
    source: SourceInfo
    adaptation: AdaptationInfo


class FirstAppearance(BaseModel):
    scene_id: str
    chapter_id: str


class Character(BaseModel):
    id: str
    name: str
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None
    first_appearance: FirstAppearance | None = None


class Location(BaseModel):
    id: str
    name: str
    int_ext: IntExt
    description: str | None = None


class Slugline(BaseModel):
    int_ext: IntExt
    location_id: str | None = None
    location_name: str | None = None
    time_of_day: TimeOfDay
    heading: str


class SourceRef(BaseModel):
    chapter_id: str
    excerpt: str
    paragraph_range: list[int] | None = None


class ActionElement(BaseModel):
    type: Literal["action"] = "action"
    text: str


class DialogueElement(BaseModel):
    type: Literal["dialogue"] = "dialogue"
    character_id: str
    lines: str
    parenthetical: str | None = None


class VoiceoverElement(BaseModel):
    type: Literal["voiceover"] = "voiceover"
    character_id: str | None = None
    text: str


class TransitionElement(BaseModel):
    type: Literal["transition"] = "transition"
    text: str


Element = Annotated[
    ActionElement | DialogueElement | VoiceoverElement | TransitionElement,
    Field(discriminator="type"),
]


class Scene(BaseModel):
    id: str
    slugline: Slugline
    summary: str | None = None
    source_refs: list[SourceRef]
    characters_present: list[str]
    elements: list[Element]
    estimated_duration_min: float | None = None


class Act(BaseModel):
    id: str
    title: str | None = None
    scenes: list[str]


class Warning(BaseModel):
    code: WarningCode | str
    scene_id: str | None = None
    message: str
    severity: WarningSeverity


class Screenplay(BaseModel):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    meta: Meta
    characters: list[Character]
    locations: list[Location] = Field(default_factory=list)
    acts: list[Act] = Field(default_factory=list)
    scenes: list[Scene]
    warnings: list[Warning] = Field(default_factory=list)


# --- LLM intermediate DTOs ---


class CharacterDraft(BaseModel):
    id: str | None = None
    name: str
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None


class LocationDraft(BaseModel):
    id: str | None = None
    name: str
    int_ext: IntExt = IntExt.INTERIOR
    description: str | None = None


class EntityExtractionResult(BaseModel):
    characters: list[CharacterDraft] = Field(default_factory=list)
    locations: list[LocationDraft] = Field(default_factory=list)


class SceneDraft(BaseModel):
    slugline: Slugline
    summary: str | None = None
    source_refs: list[SourceRef]
    characters_present: list[str]
    elements: list[Element]
    estimated_duration_min: float | None = None


class AdaptationChapterResult(BaseModel):
    scenes: list[SceneDraft] = Field(default_factory=list)
    warnings: list[Warning] = Field(default_factory=list)


class ConversionStats(BaseModel):
    chapters: int
    scenes: int
    characters: int
    locations: int
    warnings: int


class ConversionReport(BaseModel):
    status: str
    stats: ConversionStats
    duration_sec: float
    warnings_summary: list[dict[str, int | str]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ConversionResult(BaseModel):
    screenplay: Screenplay
    report: ConversionReport
    yaml_content: str


class ConversionOptions(BaseModel):
    title: str | None = None
    author: str | None = None
    model: str | None = None
    provider: str | None = None
    model_id: str | None = None


def build_meta(
    *,
    title: str,
    author: str,
    chapters: list[ChapterInfo],
    model: str,
    prompt_version: str,
) -> Meta:
    return Meta(
        title=title,
        author=author,
        adapted_by="novel2script/0.1.0",
        source=SourceInfo(format="novel", chapter_count=len(chapters), chapters=chapters),
        adaptation=AdaptationInfo(
            created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            model=model,
            prompt_version=prompt_version,
        ),
    )
