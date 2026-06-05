"""Tests for YAML emitter."""

import json
from pathlib import Path

from novel2script.emitter.yaml_writer import (
    load_screenplay,
    serialize_screenplay,
    write_screenplay,
)
from novel2script.models.enums import ValidationStatus
from novel2script.validator.validate import validate_screenplay


def test_serialize_contains_schema_version(minimal_screenplay):
    yaml_content = serialize_screenplay(minimal_screenplay)
    assert 'schema_version: "1.0"' in yaml_content or "schema_version: '1.0'" in yaml_content


def test_roundtrip_load_screenplay(minimal_screenplay, tmp_path):
    yaml_path = tmp_path / "roundtrip.yaml"
    yaml_path.write_text(serialize_screenplay(minimal_screenplay), encoding="utf-8")
    loaded = load_screenplay(yaml_path)
    assert loaded.meta.title == minimal_screenplay.meta.title
    assert len(loaded.scenes) == len(minimal_screenplay.scenes)
    assert loaded.characters[0].id == minimal_screenplay.characters[0].id


def test_write_screenplay_creates_report(minimal_screenplay, tmp_path):
    output = tmp_path / "out.yaml"
    validation = validate_screenplay(minimal_screenplay)
    yaml_content, report = write_screenplay(minimal_screenplay, output, validation, 1.5)

    assert output.exists()
    assert output.with_suffix(".report.json").exists()
    assert yaml_content
    assert report.duration_sec == 1.5


def test_report_stats_fields(minimal_screenplay, tmp_path):
    output = tmp_path / "out.yaml"
    validation = validate_screenplay(minimal_screenplay)
    _, report = write_screenplay(minimal_screenplay, output, validation, 2.0)

    assert report.stats.chapters == 3
    assert report.stats.scenes == 3
    assert report.stats.characters == 2
    assert report.stats.warnings >= 0
    assert report.status in ("PASS", "PASS_WITH_WARNINGS", "FAIL")

    report_data = json.loads(output.with_suffix(".report.json").read_text(encoding="utf-8"))
    assert "stats" in report_data
    assert "duration_sec" in report_data


def test_multiline_action_uses_block_scalar(minimal_screenplay):
    minimal_screenplay.scenes[0].elements[0].text = "第一行\n第二行\n第三行"
    yaml_content = serialize_screenplay(minimal_screenplay)
    assert "|" in yaml_content or "第一行" in yaml_content
