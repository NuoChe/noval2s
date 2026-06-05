#!/usr/bin/env python3
"""Fetch public-domain novel samples from Wikisource (zh)."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import time
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = ROOT / "tests" / "fixtures" / "novels"
EXAMPLES_DIR = ROOT / "examples" / "novels"

WIKISOURCE_API = "https://zh.wikisource.org/w/api.php"
USER_AGENT = "Novel2Script/0.1.0 (PD sample fetcher; educational use)"
REQUEST_DELAY_SEC = 1.0
MAX_RETRIES = 2

CHAPTER_HUI_RE = re.compile(
    r"^第([零一二三四五六七八九十百千\d]+)回\s*(.*)$",
    re.MULTILINE,
)
CHAPTER_ZHANG_RE = re.compile(
    r"^第([零一二三四五六七八九十百千\d]+)章\s*(.*)$",
    re.MULTILINE,
)
HUI_HEADING_RE = re.compile(r"第([零一二三四五六七八九十百千\d]+)回\s*(.*)")
NUMERIC_SUBPAGE_RE = re.compile(r"^\d{2}$")

CN_NUM_MAP = {
    "零": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
    "百": 100,
    "千": 1000,
}


@dataclass
class SampleCatalogEntry:
    id: str
    title: str
    author: str
    wiki_page: str
    source_url: str
    license: str = "Public Domain"


@dataclass
class FetchOptions:
    max_chapters: int = 3
    variant: str | None = None
    simplify: bool = False


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

_opencc_converter = None


def get_opencc_converter():
    global _opencc_converter
    if _opencc_converter is None:
        from opencc import OpenCC

        _opencc_converter = OpenCC("t2s")
    return _opencc_converter


def to_simplified(text: str) -> str:
    return get_opencc_converter().convert(text)


def cn_numeral_to_int(s: str) -> int | None:
    if s.isdigit():
        return int(s)
    if not s:
        return None
    total = 0
    current = 0
    for ch in s:
        if ch not in CN_NUM_MAP:
            return None
        val = CN_NUM_MAP[ch]
        if val >= 10:
            if current == 0:
                current = 1
            total += current * val
            current = 0
        else:
            current = val
    return total + current


def normalize_hui_to_zhang(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        num_raw = match.group(1)
        subtitle = match.group(2).strip()
        num = cn_numeral_to_int(num_raw)
        if num is None:
            return match.group(0)
        heading = f"第{num}章"
        if subtitle:
            heading += f" {subtitle}"
        return heading

    return CHAPTER_HUI_RE.sub(repl, text)


def apply_text_options(text: str, options: FetchOptions) -> str:
    if options.simplify:
        text = to_simplified(text)
    return text


def api_get(
    session: requests.Session,
    params: dict,
    *,
    retries: int = MAX_RETRIES,
) -> dict:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            resp = session.get(WIKISOURCE_API, params=params, timeout=60)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(REQUEST_DELAY_SEC * (attempt + 1))
    raise RuntimeError(str(last_error))


def fetch_wiki_parse(
    page_title: str,
    session: requests.Session,
    options: FetchOptions,
    *,
    include_links: bool = False,
) -> tuple[str, list[dict]]:
    props = "text|links" if include_links else "text"
    params: dict = {
        "action": "parse",
        "page": page_title,
        "prop": props,
        "format": "json",
        "disableeditsection": "true",
    }
    if options.variant:
        params["variant"] = options.variant
    data = api_get(session, params)
    if "error" in data:
        raise RuntimeError(data["error"].get("info", str(data["error"])))
    html = data["parse"]["text"]["*"]
    links = data["parse"].get("links", []) if include_links else []
    return html, links


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.select(
        "script, style, .mw-editsection, .reference, sup.reference, "
        "table, .noprint, .navbox, .toc, .mw-jump-link"
    ):
        tag.decompose()
    root = soup.select_one(".mw-parser-output") or soup
    text = root.get_text("\n", strip=True)
    text = unescape(text)
    lines = [line.strip() for line in text.splitlines()]
    cleaned: list[str] = []
    skip_prefixes = ("跳转至", "检索自", "分类：", "▶", "←", "→")
    for line in lines:
        if not line:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        if any(line.startswith(p) for p in skip_prefixes):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def extract_hui_heading(text: str) -> str | None:
    for line in text.splitlines():
        line = line.strip()
        match = HUI_HEADING_RE.search(line)
        if match:
            subtitle = match.group(2).strip()
            return f"第{match.group(1)}回 {subtitle}".strip()
    return None


def find_chapter_subpages(
    html: str,
    wiki_page: str,
    api_links: list[dict],
) -> list[tuple[str, str]]:
    """Return ordered list of (subpage_slug, chapter_heading)."""
    heading_by_slug: dict[str, str] = {}

    soup = BeautifulSoup(html, "html.parser")
    wiki_prefix = f"/wiki/{wiki_page}/"
    for anchor in soup.find_all("a", href=True):
        href = unquote(anchor["href"])
        if not href.startswith(wiki_prefix):
            continue
        slug = href[len(wiki_prefix) :].split("#")[0]
        link_text = anchor.get_text(" ", strip=True)
        if NUMERIC_SUBPAGE_RE.fullmatch(slug):
            heading = extract_hui_heading(link_text) or f"第{int(slug)}回"
            heading_by_slug[slug] = heading
        elif re.match(r"第[零一二三四五六七八九十百千\d]+回", slug):
            heading = extract_hui_heading(link_text) or slug
            heading_by_slug[slug] = heading

    numeric_slugs = sorted(
        [slug for slug in heading_by_slug if NUMERIC_SUBPAGE_RE.fullmatch(slug)],
        key=int,
    )
    if numeric_slugs:
        return [(slug, heading_by_slug[slug]) for slug in numeric_slugs]

    hui_slugs = sorted(
        heading_by_slug.keys(),
        key=lambda s: cn_numeral_to_int(re.search(r"第([零一二三四五六七八九十百千\d]+)回", s).group(1))
        if re.search(r"第([零一二三四五六七八九十百千\d]+)回", s)
        else 9999,
    )
    if hui_slugs:
        return [(slug, heading_by_slug[slug]) for slug in hui_slugs]

    api_numeric = sorted(
        {
            link.get("*") or link.get("title", "")
            for link in api_links
            if NUMERIC_SUBPAGE_RE.fullmatch(link.get("*") or link.get("title", ""))
        },
        key=int,
    )
    return [(slug, f"第{int(slug)}回") for slug in api_numeric]


def split_by_chapter_headings(text: str) -> list[tuple[str, str]]:
    pattern = re.compile(
        r"^(第[零一二三四五六七八九十百千\d]+[回章]\s*.*)$",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(text))
    if not matches:
        return []
    sections: list[tuple[str, str]] = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        heading = match.group(1).strip()
        body = text[match.end() : end].strip()
        if body:
            sections.append((heading, body))
    return sections


def fetch_sample(
    entry: SampleCatalogEntry,
    options: FetchOptions,
    session: requests.Session,
) -> str:
    index_html, api_links = fetch_wiki_parse(
        entry.wiki_page, session, options, include_links=True
    )
    subpages = find_chapter_subpages(index_html, entry.wiki_page, api_links)

    header_title = apply_text_options(f"《{entry.title}》", options)
    header_author = apply_text_options(f"作者：{entry.author}", options)
    parts: list[str] = [header_title, header_author, ""]

    if subpages:
        for slug, heading in subpages[: options.max_chapters]:
            time.sleep(REQUEST_DELAY_SEC)
            page_title = f"{entry.wiki_page}/{slug}"
            chapter_html, _ = fetch_wiki_parse(page_title, session, options)
            body = html_to_text(chapter_html)
            page_heading = extract_hui_heading(body) or heading
            page_heading = apply_text_options(page_heading, options)
            body = apply_text_options(body, options)
            parts.append(page_heading)
            parts.append("")
            parts.append(body)
            parts.append("")
    else:
        full_text = html_to_text(index_html)
        sections = split_by_chapter_headings(full_text)
        if not sections:
            raise RuntimeError(f"No chapter sections found for {entry.title}")
        for heading, body in sections[: options.max_chapters]:
            parts.append(apply_text_options(heading, options))
            parts.append("")
            parts.append(apply_text_options(body, options))
            parts.append("")

    combined = normalize_hui_to_zhang("\n".join(parts).strip())
    return combined + "\n"


def write_sample_files(entry: SampleCatalogEntry, content: str) -> int:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{entry.id}.txt"
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
    session.headers.update({"User-Agent": USER_AGENT})

    records: list[dict] = []
    for entry in SAMPLE_CATALOG:
        print(f"Fetching {entry.title} ...", flush=True)
        try:
            content = fetch_sample(entry, fetch_options, session)
            chapter_count = len(CHAPTER_ZHANG_RE.findall(content))
            word_count = len(re.findall(r"[\u4e00-\u9fff]", content))
            if chapter_count < 3:
                print(f"  SKIP: only {chapter_count} chapters detected", flush=True)
                continue
            if word_count < 500:
                print(f"  SKIP: only {word_count} Chinese chars (likely empty body)", flush=True)
                continue
            print(f"  OK: {chapter_count} chapters, ~{word_count} Chinese chars", flush=True)
            if not args.dry_run:
                write_sample_files(entry, content)
            records.append(
                {
                    "id": entry.id,
                    "title": entry.title,
                    "author": entry.author,
                    "source_url": entry.source_url,
                    "license": entry.license,
                    "chapters_included": chapter_count,
                    "word_count": word_count,
                    "file": f"{entry.id}.txt",
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
