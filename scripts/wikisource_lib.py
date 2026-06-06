"""Shared Wikisource fetch utilities for PD Chinese novels."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from html import unescape
from urllib.parse import quote, unquote

import requests
from bs4 import BeautifulSoup

WIKISOURCE_API = "https://zh.wikisource.org/w/api.php"
WIKISOURCE_BASE = "https://zh.wikisource.org/wiki/"
USER_AGENT = "Novel2Script/0.1.0 (PD sample fetcher; educational use)"
REQUEST_DELAY_SEC = 2.5
MAX_RETRIES = 5

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
INVALID_FILENAME_CHARS_RE = re.compile(r'[\\/:*?"<>|]')

DEFAULT_CATEGORIES = [
    "Category:章回小说",
    "Category:清代小说",
    "Category:明代小說",
    "Category:神魔小说",
    "Category:小說",
    "Category:古典小说",
    "Category:演义",
    "Category:笔记小说",
    "Category:長篇小說",
    "Category:中國小說",
]

# Common PD novels on zh.wikisource (wiki page title; traditional/simplified mixed).
# Smaller / faster books first; large classics last.
SEED_NOVEL_PAGES = list(
    dict.fromkeys(
        [
            "咒枣记",
            "斩鬼传",
            "续西游记",
            "锋剑春秋",
            "二十四尊得道罗汉传",
            "飞剑记",
            "西游记补",
            "后西游记",
            "三遂平妖传",
            "燕丹子",
            "西京杂记",
            "大唐三藏取经诗话",
            "穆天子传",
            "搜神记",
            "世说新语",
            "孽海花",
            "官场现形记",
            "二十年目睹之怪现状",
            "老残游记",
            "官場現形記",
            "二十年目睹之怪現狀",
            "老殘遊記",
            "好逑传",
            "平山冷燕",
            "玉娇梨",
            "花月痕",
            "青楼梦",
            "镜花缘",
            "歧路灯",
            "醒世姻缘传",
            "初刻拍案惊奇",
            "二刻拍案惊奇",
            "今古奇观",
            "喻世明言",
            "警世通言",
            "醒世恒言",
            "古今小说",
            "荡寇志",
            "说唐演义全传",
            "隋唐演义",
            "残唐五代史演义",
            "粉妆楼",
            "万花楼",
            "岳传",
            "大明英烈传",
            "韩湘子全传",
            "八仙得道传",
            "何仙姑全传",
            "东度记",
            "归莲梦",
            "绿野仙踪",
            "天豹图",
            "天雨花",
            "生花梦",
            "林兰香",
            "梅兰佳话",
            "女娲石",
            "雪月梅",
            "合浦珠",
            "定情人",
            "飞花咏",
            "玉支玑",
            "画眉缘",
            "人间乐",
            "情梦柝",
            "凤凰池",
            "驻春园",
            "快心编",
            "炎凉岸",
            "锦香亭",
            "赛红丝",
            "飞花艳想",
            "八洞天",
            "五色石",
            "二度梅",
            "驻春园小史",
            "听月楼",
            "蝴蝶媒",
            "阅微草堂笔记",
            "子不语",
            "萤窗异草",
            "夜谭随录",
            "淞隐漫录",
            "淞滨琐话",
            "新齐谐",
            "耳食录",
            "醉醒石",
            "剪灯新话",
            "剪灯余话",
            "觅灯因话",
            "三宝太监西洋记",
            "平妖传",
            "东游记",
            "南游记",
            "北游记",
            "包公案",
            "施公案",
            "彭公案",
            "狄公案",
            "三侠五义",
            "小五义",
            "儿女英雄传",
            "野叟曝言",
            "说岳全传",
            "杨家将演义",
            "聊斋志异",
            "聊齋誌異",
            "儒林外史",
            "封神演义",
            "封神演義",
            "东周列国志",
            "東周列國志",
            "水浒传",
            "水滸傳",
            "三国演义",
            "三國演義",
            "西游记",
            "西遊記",
            "金瓶梅",
            "红楼梦",
            "紅樓夢",
        ]
    )
)

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

_opencc_converter = None


@dataclass
class FetchOptions:
    max_chapters: int | None = 3
    variant: str | None = None
    simplify: bool = False
    max_chars: int | None = None


@dataclass
class NovelPageInfo:
    wiki_page: str
    title: str
    source_url: str


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


def count_chinese_chars(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def sanitize_chinese_filename(title: str, used: set[str] | None = None) -> str:
    """Build a safe Chinese filename like ``书名.txt``."""
    name = title.strip().strip("《》")
    name = INVALID_FILENAME_CHARS_RE.sub("·", name)
    name = name.strip(". ") or "未命名"
    filename = f"{name}.txt"
    if not used:
        return filename
    if filename not in used:
        used.add(filename)
        return filename
    base = name
    counter = 2
    while True:
        candidate = f"{base}（{counter}）.txt"
        if candidate not in used:
            used.add(candidate)
            return candidate
        counter += 1


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
            if resp.status_code == 429:
                wait = REQUEST_DELAY_SEC * (2 ** attempt)
                retry_after = resp.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    wait = max(wait, int(retry_after))
                time.sleep(wait)
                raise RuntimeError(f"429 Too Many Requests (retry in {wait:.1f}s)")
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(REQUEST_DELAY_SEC * (2 ** attempt))
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


def probe_novel_structure(
    wiki_page: str,
    session: requests.Session,
    options: FetchOptions,
) -> int:
    """Return estimated chapter count without fetching all subpages."""
    index_html, api_links = fetch_wiki_parse(
        wiki_page, session, options, include_links=True
    )
    subpages = find_chapter_subpages(index_html, wiki_page, api_links)
    if subpages:
        return len(subpages)
    full_text = html_to_text(index_html)
    sections = split_by_chapter_headings(full_text)
    return len(sections)


def discover_novel_pages(
    session: requests.Session,
    categories: list[str] | None = None,
    *,
    max_pages: int | None = None,
) -> list[NovelPageInfo]:
    """Discover novel index pages from Wikisource categories."""
    categories = categories or DEFAULT_CATEGORIES
    seen_titles: set[str] = set()
    results: list[NovelPageInfo] = []

    def walk_category(category: str, depth: int = 0) -> None:
        if max_pages is not None and len(results) >= max_pages:
            return
        if depth > 3:
            return
        cmcontinue: str | None = None
        while True:
            params: dict = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": category,
                "cmlimit": "500",
                "cmtype": "page|subcat",
                "format": "json",
            }
            if cmcontinue:
                params["cmcontinue"] = cmcontinue
            data = api_get(session, params)
            for member in data.get("query", {}).get("categorymembers", []):
                if max_pages is not None and len(results) >= max_pages:
                    return
                ns = member.get("ns", 0)
                title = member.get("title", "")
                if ns == 14:
                    walk_category(title, depth + 1)
                    continue
                if ns != 0:
                    continue
                if title.startswith(("Template:", "Author:", "作者:", "Portal:", "Help:")):
                    continue
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                display_title = to_simplified(title) if title else title
                results.append(
                    NovelPageInfo(
                        wiki_page=title,
                        title=display_title,
                        source_url=WIKISOURCE_BASE + quote(title.replace(" ", "_")),
                    )
                )
            cmcontinue = data.get("continue", {}).get("cmcontinue")
            if not cmcontinue:
                break
            time.sleep(REQUEST_DELAY_SEC)

    for category in categories:
        walk_category(category)
        if max_pages is not None and len(results) >= max_pages:
            break
    return results


def seed_novel_pages() -> list[NovelPageInfo]:
    """Build candidate list from predefined seed titles."""
    results: list[NovelPageInfo] = []
    for wiki_page in SEED_NOVEL_PAGES:
        display_title = to_simplified(wiki_page)
        results.append(
            NovelPageInfo(
                wiki_page=wiki_page,
                title=display_title,
                source_url=WIKISOURCE_BASE + quote(wiki_page.replace(" ", "_")),
            )
        )
    return results


def discover_all_novel_candidates(
    session: requests.Session,
    categories: list[str] | None = None,
) -> list[NovelPageInfo]:
    """Merge seed list with category discovery; seeds come first."""
    seen: set[str] = set()
    merged: list[NovelPageInfo] = []
    for page in seed_novel_pages():
        if page.wiki_page not in seen:
            seen.add(page.wiki_page)
            merged.append(page)
    for page in discover_novel_pages(session, categories):
        if page.wiki_page not in seen:
            seen.add(page.wiki_page)
            merged.append(page)
    return merged


def fetch_novel_content(
    wiki_page: str,
    *,
    title: str,
    author: str,
    options: FetchOptions,
    session: requests.Session,
) -> str:
    """Fetch novel text; ``max_chapters=None`` means all available chapters."""
    index_html, api_links = fetch_wiki_parse(
        wiki_page, session, options, include_links=True
    )
    subpages = find_chapter_subpages(index_html, wiki_page, api_links)

    header_title = apply_text_options(f"《{title}》", options)
    header_author = apply_text_options(f"作者：{author}", options)
    parts: list[str] = [header_title, header_author, ""]
    char_budget = options.max_chars
    chars_so_far = count_chinese_chars("\n".join(parts))

    chapter_limit = options.max_chapters

    if subpages:
        selected = subpages if chapter_limit is None else subpages[:chapter_limit]
        for slug, heading in selected:
            time.sleep(REQUEST_DELAY_SEC)
            page_title = f"{wiki_page}/{slug}"
            chapter_html, _ = fetch_wiki_parse(page_title, session, options)
            body = html_to_text(chapter_html)
            page_heading = extract_hui_heading(body) or heading
            page_heading = apply_text_options(page_heading, options)
            body = apply_text_options(body, options)
            if char_budget is not None:
                body_chars = count_chinese_chars(body)
                if chars_so_far + body_chars > char_budget:
                    remaining = char_budget - chars_so_far
                    if remaining < 200:
                        break
                    body = _truncate_chinese(body, remaining)
            parts.append(page_heading)
            parts.append("")
            parts.append(body)
            parts.append("")
            chars_so_far = count_chinese_chars("\n".join(parts))
            if char_budget is not None and chars_so_far >= char_budget:
                break
    else:
        full_text = html_to_text(index_html)
        sections = split_by_chapter_headings(full_text)
        if not sections:
            raise RuntimeError(f"No chapter sections found for {title}")
        selected = sections if chapter_limit is None else sections[:chapter_limit]
        for heading, body in selected:
            heading = apply_text_options(heading, options)
            body = apply_text_options(body, options)
            if char_budget is not None:
                body_chars = count_chinese_chars(body)
                if chars_so_far + body_chars > char_budget:
                    remaining = char_budget - chars_so_far
                    if remaining < 200:
                        break
                    body = _truncate_chinese(body, remaining)
            parts.append(heading)
            parts.append("")
            parts.append(body)
            parts.append("")
            chars_so_far = count_chinese_chars("\n".join(parts))
            if char_budget is not None and chars_so_far >= char_budget:
                break

    combined = normalize_hui_to_zhang("\n".join(parts).strip())
    return combined + "\n"


def _truncate_chinese(text: str, max_chars: int) -> str:
    count = 0
    out: list[str] = []
    for ch in text:
        out.append(ch)
        if "\u4e00" <= ch <= "\u9fff":
            count += 1
            if count >= max_chars:
                break
    return "".join(out)
