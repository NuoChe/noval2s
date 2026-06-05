"""Tests for chapter parser."""

import pytest

from novel2script.exceptions import (
    ChapterParseError,
    InsufficientChaptersError,
    LimitExceededError,
)
from novel2script.parser.chapter import parse_chapters


def test_parse_three_chapters(sample_novel_text, settings):
    chapters = parse_chapters(sample_novel_text, settings)
    assert len(chapters) == 3
    assert chapters[0].id == "chapter_01"
    assert chapters[0].title == "初遇"
    assert chapters[1].title == "误会"
    assert chapters[2].title == "和解"
    assert all(c.word_count > 0 for c in chapters)
    assert all(len(c.paragraphs) > 0 for c in chapters)


def test_insufficient_chapters(settings):
    text = "第一章 只有一章\n\n一些内容。"
    with pytest.raises(InsufficientChaptersError):
        parse_chapters(text, settings)


def test_two_chapters_raises(two_chapter_novel_text, settings):
    with pytest.raises(InsufficientChaptersError):
        parse_chapters(two_chapter_novel_text, settings)


def test_english_chapters(settings):
    text = """Chapter 1: Start

Content one.

Chapter 2: Middle

Content two.

Chapter 3: End

Content three."""
    chapters = parse_chapters(text, settings)
    assert len(chapters) == 3


def test_markdown_chapters(settings):
    text = """# First

Para one.

# Second

Para two.

# Third

Para three."""
    chapters = parse_chapters(text, settings)
    assert len(chapters) == 3


def test_empty_text_raises(empty_novel_text, settings):
    with pytest.raises(ChapterParseError):
        parse_chapters(empty_novel_text, settings)


def test_no_chapter_heading_raises(settings):
    text = "这是一段没有章节标题的纯文本。\n\n只有段落内容。"
    with pytest.raises(ChapterParseError):
        parse_chapters(text, settings)


def test_exceeds_max_chapters(settings):
    settings.max_chapters = 20
    parts = []
    for i in range(1, 22):
        parts.append(f"第{i}章 章节{i}\n\n内容{i}。")
    text = "\n\n".join(parts)
    with pytest.raises(LimitExceededError):
        parse_chapters(text, settings)


def test_chapter_ids_sequential(sample_novel_text, settings):
    chapters = parse_chapters(sample_novel_text, settings)
    assert [c.id for c in chapters] == ["chapter_01", "chapter_02", "chapter_03"]


def test_word_count_positive(sample_novel_text, settings):
    chapters = parse_chapters(sample_novel_text, settings)
    for chapter in chapters:
        assert chapter.word_count > 0


def test_chinese_hui_chapters(settings):
    text = """第一回 开端

第一段正文内容。

第二回 发展

第二段正文内容。

第三回 结局

第三段正文内容。"""
    chapters = parse_chapters(text, settings)
    assert len(chapters) == 3
    assert chapters[0].title == "开端"
    assert chapters[0].word_count > 0
