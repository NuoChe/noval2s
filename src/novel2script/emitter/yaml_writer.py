"""YAML serialization and report writing."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from ruamel.yaml import YAML

from novel2script.models.enums import ValidationStatus
from novel2script.models.schema import ConversionReport, ConversionStats, Screenplay
from novel2script.validator.validate import ValidationResult


def screenplay_to_dict(screenplay: Screenplay) -> dict:
    return screenplay.model_dump(exclude_none=True, mode="json")


def serialize_screenplay(screenplay: Screenplay) -> str:
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.allow_unicode = True
    yaml.width = 120

    data = screenplay_to_dict(screenplay)

    from io import StringIO

    stream = StringIO()
    yaml.dump(data, stream)
    return stream.getvalue()


def build_report(
    validation: ValidationResult,
    duration_sec: float,
) -> ConversionReport:
    sp = validation.screenplay
    stats = ConversionStats(
        chapters=sp.meta.source.chapter_count if sp else 0,
        scenes=len(sp.scenes) if sp else 0,
        characters=len(sp.characters) if sp else 0,
        locations=len(sp.locations) if sp else 0,
        warnings=len(validation.warnings),
    )

    counter = Counter(str(w.code) for w in validation.warnings)
    warnings_summary = [{"code": code, "count": count} for code, count in counter.items()]

    return ConversionReport(
        status=validation.status.value,
        stats=stats,
        duration_sec=round(duration_sec, 2),
        warnings_summary=warnings_summary,
        errors=validation.errors,
    )


def write_screenplay(
    screenplay: Screenplay,
    output_path: Path,
    validation: ValidationResult,
    duration_sec: float,
) -> tuple[str, ConversionReport]:
    yaml_content = serialize_screenplay(screenplay)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml_content, encoding="utf-8")

    report = build_report(validation, duration_sec)
    report_path = output_path.with_suffix(".report.json")
    report_path.write_text(
        json.dumps(report.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return yaml_content, report


def load_screenplay(path: Path) -> Screenplay:
    yaml = YAML(typ="safe")
    with path.open(encoding="utf-8") as f:
        data = yaml.load(f)
    return Screenplay.model_validate(data)
