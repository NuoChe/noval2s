#!/usr/bin/env python3
"""Build bulk Chinese test novel corpus (Wikisource full + synthetic full)."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import uuid
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from synthetic_novel import DEFAULT_SEED, generate_synthetic_novel  # noqa: E402
from wikisource_lib import (  # noqa: E402
    CHAPTER_ZHANG_RE,
    FetchOptions,
    REQUEST_DELAY_SEC,
    USER_AGENT,
    count_chinese_chars,
    discover_all_novel_candidates,
    fetch_novel_content,
    fetch_wiki_parse,
    html_to_text,
    probe_novel_structure,
    sanitize_chinese_filename,
    to_simplified,
)

ROOT = Path(__file__).resolve().parent.parent
BULK_DIR = ROOT / "tests" / "fixtures" / "novels" / "bulk"
CACHE_DIR = Path(__file__).resolve().parent / ".cache"
STATE_PATH = CACHE_DIR / "corpus_state.json"
DISCOVERED_PATH = CACHE_DIR / "discovered_pages.json"

AUTHOR_RE = re.compile(r"作者[：:]\s*(.+?)(?:\n|$)")


def load_state() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"samples": [], "used_filenames": [], "processed_wiki_pages": [], "failed": []}


def save_state(state: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def count_wikisource(samples: list[dict]) -> int:
    return sum(1 for s in samples if s.get("source") == "wikisource")


def count_synthetic(samples: list[dict]) -> int:
    return sum(1 for s in samples if s.get("source") == "synthetic")


def wipe_corpus() -> None:
    """Remove existing bulk txt files and cache (fresh rebuild)."""
    BULK_DIR.mkdir(parents=True, exist_ok=True)
    for path in BULK_DIR.glob("*.txt"):
        path.unlink()
    manifest = BULK_DIR / "manifest.json"
    if manifest.exists():
        manifest.unlink()
    for cache_file in (STATE_PATH, DISCOVERED_PATH):
        if cache_file.exists():
            cache_file.unlink()
    print(f"Wiped {BULK_DIR} and cache", flush=True)


def extract_author_from_index(
    wiki_page: str,
    session: requests.Session,
    options: FetchOptions,
) -> str:
    html, _ = fetch_wiki_parse(wiki_page, session, options)
    text = html_to_text(html)
    if options.simplify:
        text = to_simplified(text)
    match = AUTHOR_RE.search(text)
    if match:
        author = match.group(1).strip()
        if len(author) <= 30:
            return author
    return "佚名"


def write_bulk_file(filename: str, content: str) -> Path:
    BULK_DIR.mkdir(parents=True, exist_ok=True)
    path = BULK_DIR / filename
    path.write_text(content, encoding="utf-8")
    return path


def options_from_state(state: dict) -> FetchOptions:
    opt = state.get("options", {})
    return FetchOptions(
        variant=opt.get("variant"),
        simplify=bool(opt.get("simplify")),
    )


def build_manifest_file(samples: list[dict], options: FetchOptions, state: dict) -> None:
    ws_count = count_wikisource(samples)
    syn_count = count_synthetic(samples)
    manifest = {
        "total": len(samples),
        "crawled_full_target": state["crawled_full"],
        "crawled_full_count": ws_count,
        "synthetic_full_count": syn_count,
        "target_total": state["total"],
        "locale": "zh-hans" if (options.variant or options.simplify) else "zh-hant",
        "wikisource_variant": options.variant,
        "opencc_simplified": options.simplify,
        "samples": samples,
    }
    manifest_path = BULK_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def add_sample(
    state: dict,
    *,
    title: str,
    author: str,
    filename: str,
    content: str,
    source: str,
    source_url: str | None,
    license_name: str,
) -> bool:
    chapter_count = len(CHAPTER_ZHANG_RE.findall(content))
    word_count = count_chinese_chars(content)
    if chapter_count < 3:
        return False
    if word_count < 500:
        return False

    write_bulk_file(filename, content)
    record = {
        "id": str(uuid.uuid4()),
        "title": title,
        "author": author,
        "file": filename,
        "source": source,
        "kind": "full",
        "chapters_included": chapter_count,
        "word_count": word_count,
        "source_url": source_url or "",
        "license": license_name,
    }
    state["samples"].append(record)
    state["used_filenames"].append(filename)
    save_state(state)
    build_manifest_file(state["samples"], options_from_state(state), state)
    return True


def load_or_discover_pages(session: requests.Session, resume: bool) -> list[dict]:
    if resume and DISCOVERED_PATH.exists():
        return json.loads(DISCOVERED_PATH.read_text(encoding="utf-8"))
    pages = discover_all_novel_candidates(session)
    payload = [
        {"wiki_page": p.wiki_page, "title": p.title, "source_url": p.source_url}
        for p in pages
    ]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    DISCOVERED_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def _is_retryable_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    if "doesn't exist" in msg or "missingtitle" in msg:
        return False
    return any(
        token in msg
        for token in (
            "429",
            "too many requests",
            "getaddrinfo failed",
            "name resolution",
            "connection",
            "timeout",
            "timed out",
        )
    )


def try_add_wikisource_book(
    state: dict,
    page: dict,
    options: FetchOptions,
    session: requests.Session,
    *,
    pd_max_chapters: int | None,
    pd_max_chars: int | None,
) -> str:
    """Return ``ok``, ``skip``, or ``retry``."""
    if count_wikisource(state["samples"]) >= state["crawled_full"]:
        return "skip"

    wiki_page = page["wiki_page"]
    title = page["title"]
    used = set(state["used_filenames"])
    filename = sanitize_chinese_filename(title, used)

    try:
        chapter_count = probe_novel_structure(wiki_page, session, options)
        time.sleep(REQUEST_DELAY_SEC)
        if chapter_count < 3:
            return "skip"

        fetch_opts = FetchOptions(
            max_chapters=pd_max_chapters,
            variant=options.variant,
            simplify=options.simplify,
            max_chars=pd_max_chars,
        )

        author = extract_author_from_index(wiki_page, session, options)
        time.sleep(REQUEST_DELAY_SEC)
        content = fetch_novel_content(
            wiki_page,
            title=title,
            author=author,
            options=fetch_opts,
            session=session,
        )
        actual_chapters = len(CHAPTER_ZHANG_RE.findall(content))
        if actual_chapters < 3:
            return "skip"

        ok = add_sample(
            state,
            title=title,
            author=author,
            filename=filename,
            content=content,
            source="wikisource",
            source_url=page["source_url"],
            license_name="Public Domain",
        )
        if ok:
            n = count_wikisource(state["samples"])
            print(f"  Wikisource OK [{n}/{state['crawled_full']}]: {title} -> {filename}", flush=True)
            return "ok"
        return "skip"
    except Exception as exc:
        state["failed"].append({"wiki_page": wiki_page, "error": str(exc)})
        save_state(state)
        print(f"  Wikisource FAIL: {title}: {exc}", flush=True)
        return "retry" if _is_retryable_error(exc) else "skip"


def fill_synthetic(state: dict, seed: int) -> None:
    synthetic_index = 0
    while len(state["samples"]) < state["total"]:
        synthetic_index += 1
        novel = generate_synthetic_novel(synthetic_index, kind="full", seed=seed)
        used = set(state["used_filenames"])
        filename = sanitize_chinese_filename(novel.title, used)
        add_sample(
            state,
            title=novel.title,
            author=novel.author,
            filename=filename,
            content=novel.content,
            source="synthetic",
            source_url=None,
            license_name="Synthetic Test Data",
        )
        if synthetic_index % 50 == 0:
            print(f"  Synthetic progress: {len(state['samples'])}/{state['total']}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build bulk test corpus (Wikisource full + synthetic)")
    parser.add_argument("--total", type=int, default=1000)
    parser.add_argument("--crawled-full", type=int, default=100, help="Wikisource full-book target")
    parser.add_argument("--simplified", action="store_true")
    parser.add_argument("--resume", action="store_true", help="Resume from cache; do not wipe bulk")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--pd-max-chapters", type=int, default=120)
    parser.add_argument("--pd-max-chars", type=int, default=200_000)
    parser.add_argument("--skip-pd", action="store_true", help="Skip Wikisource fetch (synthetic only)")
    args = parser.parse_args()

    if not args.resume:
        wipe_corpus()

    options = FetchOptions(
        max_chapters=None,
        variant="zh-hans" if args.simplified else None,
        simplify=args.simplified,
    )

    state = load_state() if args.resume else {"samples": [], "used_filenames": [], "processed_wiki_pages": [], "failed": []}
    state["total"] = args.total
    state["crawled_full"] = args.crawled_full
    state["options"] = {
        "variant": options.variant,
        "simplify": options.simplify,
    }
    save_state(state)

    if args.resume:
        retryable = {
            item["wiki_page"]
            for item in state.get("failed", [])
            if _is_retryable_error(RuntimeError(item.get("error", "")))
        }
        state["processed_wiki_pages"] = [
            page for page in state.get("processed_wiki_pages", []) if page not in retryable
        ]
        state["failed"] = [
            item for item in state.get("failed", []) if item["wiki_page"] not in retryable
        ]
        save_state(state)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    if not args.skip_pd:
        print("Discovering Wikisource novel pages (seeds + categories) ...", flush=True)
        pages = load_or_discover_pages(session, args.resume)
        print(f"  Found {len(pages)} candidate pages", flush=True)

        for page in pages:
            if count_wikisource(state["samples"]) >= args.crawled_full:
                break

            wiki_page = page["wiki_page"]
            if wiki_page in state["processed_wiki_pages"]:
                continue

            result = try_add_wikisource_book(
                state,
                page,
                options,
                session,
                pd_max_chapters=args.pd_max_chapters,
                pd_max_chars=args.pd_max_chars,
            )

            if result != "retry":
                state["processed_wiki_pages"].append(wiki_page)
                save_state(state)

        ws = count_wikisource(state["samples"])
        print(f"Wikisource crawl finished: {ws}/{args.crawled_full}", flush=True)

    print("Generating synthetic full novels to fill quota ...", flush=True)
    fill_synthetic(state, args.seed)

    build_manifest_file(state["samples"], options, state)
    ws_count = count_wikisource(state["samples"])
    syn_count = count_synthetic(state["samples"])
    print(
        f"\nDone: {len(state['samples'])}/{args.total} "
        f"(wikisource={ws_count}, synthetic={syn_count}, failed_pd={len(state['failed'])})",
        flush=True,
    )
    print(f"Output: {BULK_DIR}", flush=True)


if __name__ == "__main__":
    main()
