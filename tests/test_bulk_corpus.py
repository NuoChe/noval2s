"""Tests for bulk novel corpus (1000 full-book txt files)."""

from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from novel2script.parser.chapter import parse_book_metadata, parse_chapters

BULK_DIR = Path(__file__).parent / "fixtures" / "novels" / "bulk"
BULK_MANIFEST = BULK_DIR / "manifest.json"
SAMPLE_PARSE_COUNT = 30
SAMPLE_SEED = 20260605


@pytest.fixture(scope="module")
def bulk_manifest() -> dict:
    if not BULK_MANIFEST.exists():
        pytest.skip("Run scripts/build_novel_corpus.py to generate bulk corpus")
    return json.loads(BULK_MANIFEST.read_text(encoding="utf-8"))


def test_bulk_manifest_count(bulk_manifest):
    samples = bulk_manifest.get("samples", [])
    assert bulk_manifest.get("total") == 1000
    assert len(samples) == 1000


def test_bulk_all_full(bulk_manifest):
    samples = bulk_manifest["samples"]
    assert all(s.get("kind") == "full" for s in samples)
    assert bulk_manifest.get("excerpt_count") is None or bulk_manifest.get("excerpt_count", 0) == 0


def test_bulk_source_counts(bulk_manifest):
    samples = bulk_manifest["samples"]
    ws = sum(1 for s in samples if s.get("source") == "wikisource")
    syn = sum(1 for s in samples if s.get("source") == "synthetic")
    expected_ws = bulk_manifest.get("crawled_full_count", ws)
    expected_syn = bulk_manifest.get("synthetic_full_count", syn)
    assert ws == expected_ws
    assert ws <= bulk_manifest.get("crawled_full_target", 100)
    assert ws + syn == bulk_manifest.get("total", len(samples))
    assert syn == expected_syn


def test_bulk_all_files_exist(bulk_manifest):
    for sample in bulk_manifest["samples"]:
        path = BULK_DIR / sample["file"]
        assert path.exists(), f"Missing bulk file: {path}"


def test_bulk_parse_sample(bulk_manifest, settings):
    samples = bulk_manifest["samples"]
    rng = random.Random(SAMPLE_SEED)
    picked = rng.sample(samples, min(SAMPLE_PARSE_COUNT, len(samples)))
    bulk_settings = settings.model_copy(update={"max_chapters": 50, "max_words": 500_000})
    for sample in picked:
        path = BULK_DIR / sample["file"]
        text = path.read_text(encoding="utf-8")
        title, author = parse_book_metadata(text)
        assert title == sample["title"], sample["file"]
        assert author == sample["author"], sample["file"]

        chapters = parse_chapters(text, bulk_settings)
        assert len(chapters) >= 3, f"{sample['file']}: expected >=3 chapters"
        assert sample["chapters_included"] == len(chapters)
        if sample.get("source") == "synthetic":
            assert len(chapters) >= 20
        assert all(c.word_count > 0 for c in chapters)
