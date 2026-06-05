"""Scene adaptation from novel chapters."""

from __future__ import annotations

from novel2script.adapter.prompts import SCENE_ADAPTATION_USER, SYSTEM_PROMPT
from novel2script.extractor.registry import EntityRegistry
from novel2script.llm.client import LLMClient
from novel2script.models.enums import WarningCode, WarningSeverity
from novel2script.models.schema import (
    AdaptationChapterResult,
    Scene,
    SceneDraft,
    SourceRef,
    Warning,
)
from novel2script.parser.chapter import Chapter


def _truncate_excerpt(text: str, max_len: int = 200) -> str:
    text = text.strip().replace("\n", " ")
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _enrich_source_refs(draft: SceneDraft, chapter: Chapter) -> SceneDraft:
    refs: list[SourceRef] = []
    for ref in draft.source_refs:
        excerpt = ref.excerpt
        if not excerpt and chapter.paragraphs:
            start = ref.paragraph_range[0] if ref.paragraph_range else 0
            end = (ref.paragraph_range[1] + 1) if ref.paragraph_range else 1
            end = min(end, len(chapter.paragraphs))
            excerpt = " ".join(chapter.paragraphs[start:end])
        refs.append(
            SourceRef(
                chapter_id=ref.chapter_id or chapter.id,
                excerpt=_truncate_excerpt(excerpt or chapter.content[:200]),
                paragraph_range=ref.paragraph_range,
            )
        )
    if not refs:
        refs.append(
            SourceRef(
                chapter_id=chapter.id,
                excerpt=_truncate_excerpt(chapter.content[:300]),
                paragraph_range=[0, min(2, len(chapter.paragraphs) - 1)] if chapter.paragraphs else None,
            )
        )
    return draft.model_copy(update={"source_refs": refs})


class SceneAdapter:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm
        self._scene_counter = 0
        self.all_warnings: list[Warning] = []
        self.all_scenes: list[Scene] = []

    def _next_scene_id(self) -> str:
        self._scene_counter += 1
        return f"scene_{self._scene_counter:03d}"

    def adapt_chapter(
        self,
        chapter: Chapter,
        registry: EntityRegistry,
    ) -> list[Scene]:
        user = SCENE_ADAPTATION_USER.format(
            characters=registry.characters_json(),
            locations=registry.locations_json(),
            chapter_id=chapter.id,
            chapter_text=chapter.content[:12000],
        )
        result = self.llm.complete_json(SYSTEM_PROMPT, user, AdaptationChapterResult)

        scenes: list[Scene] = []
        for draft in result.scenes:
            enriched = _enrich_source_refs(draft, chapter)
            scene_id = self._next_scene_id()
            scenes.append(
                Scene(
                    id=scene_id,
                    slugline=enriched.slugline,
                    summary=enriched.summary,
                    source_refs=enriched.source_refs,
                    characters_present=enriched.characters_present,
                    elements=enriched.elements,
                    estimated_duration_min=enriched.estimated_duration_min,
                )
            )

        for warning in result.warnings:
            if not warning.scene_id and scenes:
                warning = warning.model_copy(update={"scene_id": scenes[0].id})
            self.all_warnings.append(warning)

        if len(result.scenes) > 1:
            self.all_warnings.append(
                Warning(
                    code=WarningCode.SCENE_SPLIT,
                    scene_id=scenes[0].id if scenes else None,
                    message=f"Chapter {chapter.id} split into {len(result.scenes)} scenes",
                    severity=WarningSeverity.INFO,
                )
            )

        self._detect_merged_scenes(scenes)
        self.all_scenes.extend(scenes)
        return scenes

    def _detect_merged_scenes(self, new_scenes: list[Scene]) -> None:
        if not self.all_scenes or not new_scenes:
            return
        prev = self.all_scenes[-1]
        first = new_scenes[0]
        if prev.slugline.heading == first.slugline.heading:
            self.all_warnings.append(
                Warning(
                    code=WarningCode.SCENE_MERGED,
                    scene_id=first.id,
                    message=f"Adjacent scenes share slugline: {first.slugline.heading}",
                    severity=WarningSeverity.INFO,
                )
            )

    def set_first_appearances(self, registry: EntityRegistry, chapter_id: str) -> None:
        for scene in self.all_scenes:
            for char_id in scene.characters_present:
                if char_id in registry.characters:
                    char = registry.characters[char_id]
                    if char.first_appearance is None:
                        from novel2script.models.schema import FirstAppearance

                        registry.characters[char_id] = char.model_copy(
                            update={
                                "first_appearance": FirstAppearance(
                                    scene_id=scene.id,
                                    chapter_id=chapter_id,
                                )
                            }
                        )
