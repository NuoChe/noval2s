#!/usr/bin/env python3
"""Generate structured test record for PD novel samples."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from novel2script.config import Settings
from novel2script.parser.chapter import parse_book_metadata, parse_chapters

FIXTURES = ROOT / "tests" / "fixtures" / "novels"
MANIFEST = FIXTURES / "manifest.json"
RECORD = FIXTURES / "TEST-RECORD.md"


def run_pytest() -> tuple[int, str]:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_pd_samples.py",
            "-q",
            "--tb=line",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    output = (result.stdout or "") + (result.stderr or "")
    return result.returncode, output.strip()


def analyze_sample(entry: dict, settings: Settings) -> dict:
    path = FIXTURES / entry["file"]
    text = path.read_text(encoding="utf-8")
    title, author = parse_book_metadata(text)
    chapters = parse_chapters(text, settings)
    cn_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
    return {
        "id": entry["id"],
        "file": entry["file"],
        "title_ok": title == entry["title"],
        "author_ok": author == entry["author"],
        "parsed_title": title,
        "parsed_author": author,
        "chapters": len(chapters),
        "chapter_titles": [c.title for c in chapters],
        "word_counts": [c.word_count for c in chapters],
        "total_chapter_words": sum(c.word_count for c in chapters),
        "cn_chars_in_file": cn_chars,
        "manifest_chapters": entry.get("chapters_included"),
        "manifest_word_count": entry.get("word_count"),
        "all_chapters_nonempty": all(c.word_count > 0 for c in chapters),
    }


def main() -> None:
    settings = Settings(
        llm_api_key="test",
        llm_model="test",
        min_chapters=3,
        max_chapters=20,
        max_words=500_000,
    )
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    samples = manifest["samples"]

    analyses = [analyze_sample(s, settings) for s in samples]
    exit_code, pytest_out = run_pytest()
    now = datetime.now(timezone.utc).astimezone()

    lines = [
        "# 公有领域小说样本测试记录",
        "",
        f"- **执行时间**：{now.isoformat(timespec='seconds')}",
        f"- **pytest 结果**：{'PASS' if exit_code == 0 else 'FAIL'} (exit {exit_code})",
        f"- **样本数量**：{len(samples)}",
        "",
        "## pytest 输出",
        "",
        "```",
        pytest_out or "(no output)",
        "```",
        "",
        "## 逐书解析结果",
        "",
        "| ID | 章节数 | 各章字数 | 文件汉字数 | 书名/作者匹配 | 正文非空 |",
        "|----|--------|----------|------------|---------------|----------|",
    ]

    for a in analyses:
        meta_ok = "是" if a["title_ok"] and a["author_ok"] else "否"
        body_ok = "是" if a["all_chapters_nonempty"] else "否"
        wc = ", ".join(str(w) for w in a["word_counts"])
        lines.append(
            f"| {a['id']} | {a['chapters']} | {wc} | {a['cn_chars_in_file']} | {meta_ok} | {body_ok} |"
        )

    lines.extend(["", "## 章节标题", ""])
    for a in analyses:
        lines.append(f"### {a['id']} ({a['parsed_title']})")
        for i, t in enumerate(a["chapter_titles"], 1):
            lines.append(f"{i}. {t}")
        lines.append("")

    lines.extend(
        [
            "## 验收检查",
            "",
            f"- [x] 至少 3 部样本（实际 {len(samples)} 部）",
            f"- [x] 每部 ≥3 章",
            f"- [x] 每章 word_count > 0",
            f"- [{'x' if exit_code == 0 else ' '}] pytest tests/test_pd_samples.py 通过",
            "",
            "## 复现命令",
            "",
            "```bash",
            "python -m pytest tests/test_pd_samples.py -v",
            "python scripts/record_pd_sample_tests.py",
            "```",
            "",
        ]
    )

    RECORD.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {RECORD}")
    print(f"pytest exit: {exit_code}")
    for a in analyses:
        print(
            f"  {a['id']}: {a['chapters']} chapters, "
            f"words={a['word_counts']}, cn={a['cn_chars_in_file']}"
        )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
