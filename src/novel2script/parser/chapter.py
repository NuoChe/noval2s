"""Chapter parsing from novel text."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from novel2script.config import Settings, get_settings
from novel2script.exceptions import (
    ChapterParseError,
    InsufficientChaptersError,
    LimitExceededError,
)

CHAPTER_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "chinese",
        re.compile(
            r"^第[零一二三四五六七八九十百千\d]+章\s*(.*)$",
            re.MULTILINE,
        ),
    ),
    (
        "chinese_hui",
        re.compile(
            r"^第[零一二三四五六七八九十百千\d]+回\s*(.*)$",
            re.MULTILINE,
        ),
    ),
    (
        "english",
        re.compile(
            r"^Chapter\s+(\d+)\s*[:\.]?\s*(.*)$",
            re.MULTILINE | re.IGNORECASE,
        ),
    ),
    (
        "markdown",
        re.compile(r"^#\s+(.+)$", re.MULTILINE),
    ),
]


@dataclass
class Chapter:
    id: str
    title: str
    content: str
    word_count: int
    paragraphs: list[str] = field(default_factory=list)
    index: int = 0


def _count_words(text: str) -> int:
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    english = len(re.findall(r"[a-zA-Z]+", text))
    return chinese + english


def _split_paragraphs(content: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", content.strip()) if p.strip()]
    return parts


BOOK_TITLE_RE = re.compile(r"^《(.+?)》\s*$", re.MULTILINE)
AUTHOR_RE = re.compile(r"^作者[：:]\s*(.+?)\s*$", re.MULTILINE)


def parse_book_metadata(text: str) -> tuple[str | None, str | None]:
    """Extract optional book title and author from file header."""
    title_match = BOOK_TITLE_RE.search(text)
    author_match = AUTHOR_RE.search(text)
    title = title_match.group(1).strip() if title_match else None
    author = author_match.group(1).strip() if author_match else None
    return title, author


def _detect_chapter_matches(text: str) -> list[tuple[int, str, str]]:
    """Return list of (start_pos, title, pattern_name)."""
    matches: list[tuple[int, str, str, int]] = []

    for pattern_name, pattern in CHAPTER_PATTERNS:
        for match in pattern.finditer(text):
            if pattern_name == "english":
                num, title = match.group(1), match.group(2).strip()
                full_title = f"Chapter {num}" + (f" {title}" if title else "")
            elif pattern_name in ("chinese", "chinese_hui"):
                title = match.group(1).strip() or match.group(0).strip()
                full_title = title if title else match.group(0).strip()
            else:
                full_title = match.group(1).strip()
            matches.append((match.start(), full_title, pattern_name, match.start()))

    if not matches:
        return []

    matches.sort(key=lambda x: x[0])

    # Prefer chinese/english over markdown when overlapping at same position
    deduped: list[tuple[int, str, str]] = []
    seen_positions: set[int] = set()
    for start, title, pattern_name, _ in matches:
        if start in seen_positions:
            continue
        seen_positions.add(start)
        deduped.append((start, title, pattern_name))

    return deduped


def parse_chapters(text: str, settings: Settings | None = None) -> list[Chapter]:
    settings = settings or get_settings()
    text = text.strip()
    if not text:
        raise ChapterParseError("Input text is empty.")

    matches = _detect_chapter_matches(text)
    if not matches:
        raise ChapterParseError(
            "No chapters detected. Use headings like '第一章 标题', '第一回 标题', "
            "'Chapter 1', or '# Title'."
        )

    chapters: list[Chapter] = []
    for i, (start, title, _) in enumerate(matches):
        end = matches[i + 1][0] if i + 1 < len(matches) else len(text)
        block = text[start:end]
        # Remove heading line from content
        content_lines = block.split("\n", 1)
        content = content_lines[1].strip() if len(content_lines) > 1 else ""
        paragraphs = _split_paragraphs(content)
        chapter_id = f"chapter_{i + 1:02d}"
        chapters.append(
            Chapter(
                id=chapter_id,
                title=title,
                content=content,
                word_count=_count_words(content),
                paragraphs=paragraphs,
                index=i,
            )
        )

    if len(chapters) < settings.min_chapters:
        raise InsufficientChaptersError(
            f"At least {settings.min_chapters} chapters required, found {len(chapters)}."
        )

    if len(chapters) > settings.max_chapters:
        raise LimitExceededError(
            f"Maximum {settings.max_chapters} chapters allowed, found {len(chapters)}."
        )

    total_words = sum(c.word_count for c in chapters)
    if total_words > settings.max_words:
        raise LimitExceededError(
            f"Maximum {settings.max_words} words allowed, found {total_words}."
        )

    return chapters
