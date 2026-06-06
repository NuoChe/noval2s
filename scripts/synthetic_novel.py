"""Generate reproducible synthetic Chinese test novels."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from wikisource_lib import CHAPTER_ZHANG_RE, count_chinese_chars, normalize_hui_to_zhang

DEFAULT_SEED = 20260605

PREFIXES = ["长风", "夜雨", "长安", "江南", "云水", "孤城", "青衫", "寒江", "落花", "明月"]
NOUNS = ["记", "传", "录", "行", "梦", "缘", "书", "志", "吟", "谭"]
PLACES = ["客栈", "书院", "码头", "府邸", "山林", "街市", "河桥", "关隘", "茶肆", "医馆"]
NAMES = ["张文远", "李青云", "王怀瑾", "赵子衿", "周明远", "陈若兰", "林清和", "沈知秋"]
ACTIONS = [
    "缓步走入",
    "驻足观望",
    "低声说道",
    "提笔写下",
    "转身离去",
    "拱手一礼",
    "轻轻叹息",
    "抬头望天",
]
NARRATIVES = [
    "风从巷口吹来，带着几分凉意。",
    "远处传来更鼓声，夜色渐深。",
    "堂中灯火摇曳，人影绰绰。",
    "他心中暗想，此事未必如此简单。",
    "街市上人声鼎沸，叫卖声此起彼伏。",
    "雨丝细密，打湿青石板路。",
    "书页翻动的沙沙声，在静夜里格外清晰。",
]


@dataclass
class SyntheticNovel:
    title: str
    author: str
    content: str
    kind: str
    chapters_included: int
    word_count: int


def _chapter_number(n: int) -> str:
    return f"第{n}章"


def _generate_paragraph(rng: random.Random) -> str:
    place = rng.choice(PLACES)
    name = rng.choice(NAMES)
    action = rng.choice(ACTIONS)
    narrative = rng.choice(NARRATIVES)
    dialogue = rng.choice(
        [
            f"「{name}，你可曾听闻城外那桩旧事？」",
            f"「今日风大，不宜远行。」",
            f"「且慢，此事还需从长计议。」",
            f"「既然如此，便依你所言。」",
        ]
    )
    return f"{narrative}{name}{action}{place}。{dialogue}又有人应道：「正是如此。」"


def _generate_chapter_body(rng: random.Random, min_chars: int, max_chars: int) -> str:
    target = rng.randint(min_chars, max_chars)
    paragraphs: list[str] = []
    while count_chinese_chars("\n\n".join(paragraphs)) < target:
        paragraphs.append(_generate_paragraph(rng))
    return "\n\n".join(paragraphs)


def _make_title(rng: random.Random, index: int) -> str:
    prefix = rng.choice(PREFIXES)
    suffix = rng.choice(NOUNS)
    return f"测试·{prefix}{suffix}{index:04d}"


def generate_synthetic_novel(
    index: int,
    *,
    kind: str = "full",
    seed: int = DEFAULT_SEED,
) -> SyntheticNovel:
    """Generate one synthetic novel. ``kind`` is ``excerpt`` (3 chapters) or ``full``."""
    rng = random.Random(seed + index * 9973)
    title = _make_title(rng, index)
    author = f"测试作者{index:04d}"

    if kind == "excerpt":
        chapter_count = 3
        min_chars, max_chars = 800, 1500
    elif kind == "full":
        chapter_count = rng.randint(20, 35)
        min_chars, max_chars = 600, 1200
    else:
        raise ValueError(f"Unknown kind: {kind}")

    parts = [f"《{title}》", f"作者：{author}", ""]
    for n in range(1, chapter_count + 1):
        subtitle = rng.choice(["初遇", "风波", "转折", "重逢", "抉择", "归途", ""])
        heading = _chapter_number(n)
        if subtitle:
            heading += f" {subtitle}"
        body = _generate_chapter_body(rng, min_chars, max_chars)
        parts.extend([heading, "", body, ""])

    content = normalize_hui_to_zhang("\n".join(parts).strip()) + "\n"
    chapters_included = len(CHAPTER_ZHANG_RE.findall(content))
    word_count = count_chinese_chars(content)
    return SyntheticNovel(
        title=title,
        author=author,
        content=content,
        kind=kind,
        chapters_included=chapters_included,
        word_count=word_count,
    )
