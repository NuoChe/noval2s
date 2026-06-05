"""Tests for public-domain novel sample fixtures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from novel2script.parser.chapter import parse_book_metadata, parse_chapters

PD_NOVELS_DIR = Path(__file__).parent / "fixtures" / "novels"
EXAMPLES_NOVELS_DIR = Path(__file__).parent.parent / "examples" / "novels"
MANIFEST_PATH = PD_NOVELS_DIR / "manifest.json"

REQUIRED_MANIFEST_FIELDS = {
    "id",
    "title",
    "author",
    "source_url",
    "license",
    "chapters_included",
    "file",
}


def _file_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def pd_manifest() -> dict:
    assert MANIFEST_PATH.exists(), "Run scripts/fetch_pd_novels.py to generate samples"
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_has_samples(pd_manifest):
    samples = pd_manifest.get("samples", [])
    assert len(samples) >= 3, "Expected at least 3 PD novel samples"


def test_manifest_fields_complete(pd_manifest):
    for sample in pd_manifest["samples"]:
        missing = REQUIRED_MANIFEST_FIELDS - set(sample.keys())
        assert not missing, f"Sample {sample.get('id')} missing fields: {missing}"


def test_fixture_example_checksums_match(pd_manifest):
    for sample in pd_manifest["samples"]:
        filename = sample["file"]
        fixture_path = PD_NOVELS_DIR / filename
        example_path = EXAMPLES_NOVELS_DIR / filename
        assert fixture_path.exists(), f"Missing fixture: {fixture_path}"
        assert example_path.exists(), f"Missing example: {example_path}"
        assert _file_checksum(fixture_path) == _file_checksum(example_path)


def test_pd_samples_parse_chapters(pd_manifest, settings):
    for sample in pd_manifest["samples"]:
        path = PD_NOVELS_DIR / sample["file"]
        text = path.read_text(encoding="utf-8")
        title, author = parse_book_metadata(text)
        assert title == sample["title"]
        assert author == sample["author"]

        chapters = parse_chapters(text, settings)
        assert len(chapters) >= 3, f"{sample['id']}: expected >=3 chapters"
        assert all(c.word_count > 0 for c in chapters), f"{sample['id']}: empty chapter body"
        assert sample["chapters_included"] == len(chapters)
