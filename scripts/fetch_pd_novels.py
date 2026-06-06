#!/usr/bin/env python3
"""Fetch public-domain novel samples from Wikisource (zh)."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from wikisource_lib import (  # noqa: E402
    CHAPTER_ZHANG_RE,
    FetchOptions,
    apply_text_options,
    count_chinese_chars,
    fetch_novel_content,
    sanitize_chinese_filename,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = ROOT / "tests" / "fixtures" / "novels"
EXAMPLES_DIR = ROOT / "examples" / "novels"
REQUEST_DELAY_SEC = 1.0


@dataclass
class SampleCatalogEntry:
    id: str
    title: str
    author: str
    wiki_page: str
    source_url: str
    license: str = "Public Domain"


SAMPLE_CATALOG: list[SampleCatalogEntry] = [
    SampleCatalogEntry(
        id="niehaihua",
        title="孽海花",
        author="曾朴",
        wiki_page="孽海花",
        source_url="https://zh.wikisource.org/wiki/孽海花",
    ),
    SampleCatalogEntry(
        id="guanchang_xianxingji",
        title="官场现形记",
        author="李宝嘉",
        wiki_page="官場現形記",
        source_url="https://zh.wikisource.org/wiki/官場現形記",
    ),
    SampleCatalogEntry(
        id="ershi_nian",
        title="二十年目睹之怪现状",
        author="吴研人",
        wiki_page="二十年目睹之怪現狀",
        source_url="https://zh.wikisource.org/wiki/二十年目睹之怪現狀",
    ),
    SampleCatalogEntry(
        id="laocan_youji",
        title="老残游记",
        author="刘鹗",
        wiki_page="老殘遊記",
        source_url="https://zh.wikisource.org/wiki/老殘遊記",
    ),
]


def fetch_sample(
    entry: SampleCatalogEntry,
    options: FetchOptions,
    session: requests.Session,
) -> str:
    return fetch_novel_content(
        entry.wiki_page,
        title=entry.title,
        author=entry.author,
        options=options,
        session=session,
    )


def write_sample_files(entry: SampleCatalogEntry, content: str, filename: str) -> int:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    fixture_path = FIXTURES_DIR / filename
    example_path = EXAMPLES_DIR / filename
    fixture_path.write_text(content, encoding="utf-8")
    shutil.copy2(fixture_path, example_path)
    return len(CHAPTER_ZHANG_RE.findall(content))


def build_manifest(records: list[dict], options: FetchOptions) -> None:
    manifest = {
        "locale": "zh-hans" if (options.variant or options.simplify) else "zh-hant",
        "wikisource_variant": options.variant,
        "opencc_simplified": options.simplify,
        "samples": records,
    }
    manifest_path = FIXTURES_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(manifest_path, EXAMPLES_DIR / "manifest.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch PD novel samples from Wikisource")
    parser.add_argument("--chapters", type=int, default=3, help="Chapters per book (default: 3)")
    parser.add_argument(
        "--variant",
        choices=["zh-hans"],
        default=None,
        help="MediaWiki language variant (zh-hans for simplified from Wikisource API)",
    )
    parser.add_argument(
        "--simplify",
        action="store_true",
        help="Post-process with OpenCC traditional-to-simplified (t2s)",
    )
    parser.add_argument(
        "--simplified",
        action="store_true",
        help="Shorthand for --variant zh-hans --simplify",
    )
    parser.add_argument("--dry-run", action="store_true", help="Fetch but do not write files")
    args = parser.parse_args()

    variant = "zh-hans" if args.simplified else args.variant
    simplify = args.simplify or args.simplified
    fetch_options = FetchOptions(
        max_chapters=args.chapters,
        variant=variant,
        simplify=simplify,
    )

    session = requests.Session()
    session.headers.update({"User-Agent": "Novel2Script/0.1.0 (PD sample fetcher; educational use)"})

    used_filenames: set[str] = set()
    records: list[dict] = []
    for entry in SAMPLE_CATALOG:
        print(f"Fetching {entry.title} ...", flush=True)
        try:
            content = fetch_sample(entry, fetch_options, session)
            chapter_count = len(CHAPTER_ZHANG_RE.findall(content))
            word_count = count_chinese_chars(content)
            if chapter_count < 3:
                print(f"  SKIP: only {chapter_count} chapters detected", flush=True)
                continue
            if word_count < 500:
                print(f"  SKIP: only {word_count} Chinese chars (likely empty body)", flush=True)
                continue
            print(f"  OK: {chapter_count} chapters, ~{word_count} Chinese chars", flush=True)
            filename = sanitize_chinese_filename(entry.title, used_filenames)
            if not args.dry_run:
                write_sample_files(entry, content, filename)
            records.append(
                {
                    "id": entry.id,
                    "title": entry.title,
                    "author": entry.author,
                    "source_url": entry.source_url,
                    "license": entry.license,
                    "chapters_included": chapter_count,
                    "word_count": word_count,
                    "file": filename,
                }
            )
        except Exception as exc:
            print(f"  FAILED: {exc}", flush=True)
        time.sleep(REQUEST_DELAY_SEC)

    if records and not args.dry_run:
        build_manifest(records, fetch_options)
        mode = []
        if fetch_options.variant:
            mode.append(f"variant={fetch_options.variant}")
        if fetch_options.simplify:
            mode.append("opencc=t2s")
        print(
            f"\nWrote {len(records)} samples ({', '.join(mode) or 'original'}) "
            f"to {FIXTURES_DIR} and {EXAMPLES_DIR}",
            flush=True,
        )
    elif args.dry_run:
        print(f"\nDry run complete: {len(records)} samples would be written", flush=True)


if __name__ == "__main__":
    main()
