"""Screenplay validation per docs/YAML-SCHEMA.md section 6."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError as PydanticValidationError
from ruamel.yaml import YAML

from novel2script.models.enums import ValidationStatus, WarningCode, WarningSeverity
from novel2script.models.schema import SCHEMA_VERSION, Screenplay, Warning


class ValidationResult:
    def __init__(
        self,
        status: ValidationStatus,
        errors: list[str],
        warnings: list[Warning],
        chapter_coverage: dict[str, bool],
        screenplay: Screenplay | None = None,
    ) -> None:
        self.status = status
        self.errors = errors
        self.warnings = warnings
        self.chapter_coverage = chapter_coverage
        self.screenplay = screenplay


def _check_references(screenplay: Screenplay) -> list[str]:
    errors: list[str] = []
    char_ids = {c.id for c in screenplay.characters}
    loc_ids = {loc.id for loc in screenplay.locations}
    scene_ids = {s.id for s in screenplay.scenes}

    for scene in screenplay.scenes:
        for cid in scene.characters_present:
            if cid not in char_ids:
                errors.append(f"Scene {scene.id}: unknown character_id '{cid}' in characters_present")

        if scene.slugline.location_id and scene.slugline.location_id not in loc_ids:
            errors.append(
                f"Scene {scene.id}: unknown location_id '{scene.slugline.location_id}'"
            )

        for elem in scene.elements:
            if elem.type == "dialogue" and elem.character_id not in char_ids:
                errors.append(
                    f"Scene {scene.id}: dialogue references unknown character '{elem.character_id}'"
                )
            if elem.type == "voiceover" and elem.character_id and elem.character_id not in char_ids:
                errors.append(
                    f"Scene {scene.id}: voiceover references unknown character '{elem.character_id}'"
                )

    for act in screenplay.acts:
        for sid in act.scenes:
            if sid not in scene_ids:
                errors.append(f"Act {act.id}: unknown scene_id '{sid}'")

    for scene in screenplay.scenes:
        for ref in scene.source_refs:
            chapter_ids = {c.id for c in screenplay.meta.source.chapters}
            if ref.chapter_id not in chapter_ids:
                errors.append(
                    f"Scene {scene.id}: source_ref chapter_id '{ref.chapter_id}' not in meta"
                )

    return errors


def _check_chapter_coverage(screenplay: Screenplay) -> tuple[dict[str, bool], list[Warning]]:
    coverage: dict[str, bool] = {c.id: False for c in screenplay.meta.source.chapters}
    for scene in screenplay.scenes:
        for ref in scene.source_refs:
            if ref.chapter_id in coverage:
                coverage[ref.chapter_id] = True

    extra_warnings: list[Warning] = []
    for chapter_id, covered in coverage.items():
        if not covered:
            extra_warnings.append(
                Warning(
                    code=WarningCode.MISSING_SOURCE_REF,
                    message=f"Chapter '{chapter_id}' is not referenced in any scene source_refs",
                    severity=WarningSeverity.ERROR,
                )
            )
    return coverage, extra_warnings


def _check_content_quality(screenplay: Screenplay) -> list[Warning]:
    quality_warnings: list[Warning] = []
    for scene in screenplay.scenes:
        vo_count = sum(1 for e in scene.elements if e.type == "voiceover")
        if vo_count > 2:
            quality_warnings.append(
                Warning(
                    code="VOICEOVER_EXCESS",
                    scene_id=scene.id,
                    message=f"Scene has {vo_count} voiceover elements (recommended max 2)",
                    severity=WarningSeverity.WARNING,
                )
            )
        for elem in scene.elements:
            if elem.type == "action" and elem.text.count("\n") + 1 > 4:
                quality_warnings.append(
                    Warning(
                        code="ACTION_TOO_LONG",
                        scene_id=scene.id,
                        message="Action block exceeds 4 lines",
                        severity=WarningSeverity.WARNING,
                    )
                )
            if elem.type == "dialogue" and elem.lines.count("\n") + 1 > 5:
                quality_warnings.append(
                    Warning(
                        code="DIALOGUE_TOO_LONG",
                        scene_id=scene.id,
                        message="Dialogue block exceeds 5 lines",
                        severity=WarningSeverity.WARNING,
                    )
                )
    return quality_warnings


def validate_screenplay(screenplay: Screenplay) -> ValidationResult:
    errors: list[str] = []

    if screenplay.schema_version != SCHEMA_VERSION:
        errors.append(f"schema_version must be '{SCHEMA_VERSION}'")

    if screenplay.meta.source.chapter_count < 3:
        errors.append("meta.source.chapter_count must be >= 3")

    if len(screenplay.meta.source.chapters) != screenplay.meta.source.chapter_count:
        errors.append("meta.source.chapters length must equal chapter_count")

    if len(screenplay.scenes) < 1:
        errors.append("At least one scene is required")

    for scene in screenplay.scenes:
        if not scene.slugline.heading:
            errors.append(f"Scene {scene.id}: slugline.heading is required")
        if not scene.source_refs:
            errors.append(f"Scene {scene.id}: at least one source_ref is required")
        if not scene.elements:
            errors.append(f"Scene {scene.id}: at least one element is required")

    errors.extend(_check_references(screenplay))
    coverage, coverage_warnings = _check_chapter_coverage(screenplay)

    all_warnings = list(screenplay.warnings) + coverage_warnings + _check_content_quality(screenplay)

    has_error_warnings = any(w.severity == WarningSeverity.ERROR for w in all_warnings)

    if errors or has_error_warnings:
        status = ValidationStatus.FAIL
    elif any(w.severity == WarningSeverity.WARNING for w in all_warnings):
        status = ValidationStatus.PASS_WITH_WARNINGS
    else:
        status = ValidationStatus.PASS

    return ValidationResult(
        status=status,
        errors=errors,
        warnings=all_warnings,
        chapter_coverage=coverage,
        screenplay=screenplay,
    )


def load_and_validate_yaml(path: Path) -> ValidationResult:
    yaml = YAML(typ="safe")
    with path.open(encoding="utf-8") as f:
        data = yaml.load(f)

    try:
        screenplay = Screenplay.model_validate(data)
    except PydanticValidationError as exc:
        return ValidationResult(
            status=ValidationStatus.FAIL,
            errors=[str(exc)],
            warnings=[],
            chapter_coverage={},
        )

    return validate_screenplay(screenplay)
