# 公有领域小说样本

本目录存放用于 pytest 与演示的公有领域（Public Domain）小说章节样本。

## 来源

| 文件 | 书名 | 作者 | 来源 |
|------|------|------|------|
| 见 `manifest.json` | — | — | [维基文库](https://zh.wikisource.org) |

所有样本均来自维基文库等合法公有领域/CC 来源，**不包含**商业网文站内容。

## 格式

- UTF-8 纯文本（`.txt`）
- 文件名使用**中文书名**（如 `孽海花.txt`）
- 每部书保留前 3 章（可在采集时调整）
- 章回体 `第X回` 已规范化为 `第X章`，兼容 `parse_chapters()`
- 文件头含 `《书名》` 与 `作者：xxx`，供转换 pipeline 提取元数据

## 更新样本（演示用 4 本）

需安装开发依赖（含 `requests`、`beautifulsoup4`、`opencc-python-reimplemented`）：

```bash
pip install -e ".[dev]"
# 推荐：维基文库 zh-hans API + OpenCC 双重简体化
python scripts/fetch_pd_novels.py --chapters 3 --simplified
```

选项：

- `--chapters N`：每书保留前 N 章（默认 3）
- `--variant zh-hans`：维基文库 API 请求简体变体
- `--simplify`：OpenCC `t2s` 后处理（近代小说繁体残留时补转简体）
- `--simplified`：等价于 `--variant zh-hans --simplify`（推荐）
- `--dry-run`：仅拉取、不写文件

脚本会同步写入：

- `tests/fixtures/novels/`（本目录）
- `examples/novels/`（演示 / Web 上传用）

并生成 `manifest.json` 记录来源 URL 与 license。

## 大批量测试语料（1000 本全本）

`bulk/` 子目录存放 **1000** 本中文测试小说（**全部为全本**，无节选），供批量测试与压测使用：

| 项 | 说明 |
|---|---|
| 总量 | 1000 个 `.txt` |
| 维基文库全本 | 目标 100 部（[zh.wikisource.org](https://zh.wikisource.org)，公有领域） |
| 合成全本 | 补齐至 1000 部（`Synthetic Test Data`） |
| 命名 | 中文书名，如 `咒枣记.txt`、`测试·长风记0001.txt` |

生成命令（**默认会先清空** `bulk/` 与缓存；续跑请加 `--resume`）：

```bash
python scripts/build_novel_corpus.py --total 1000 --crawled-full 100 --simplified
```

选项：

- `--crawled-full 100`：维基文库全本目标数量
- `--resume`：断点续跑，不清空已有文件（状态在 `scripts/.cache/corpus_state.json`）
- `--pd-max-chapters 120`：单本维基文库全本最多章节数
- `--pd-max-chars 200000`：单本最大汉字数
- `--skip-pd`：跳过维基文库，仅生成合成全本（调试）

`bulk/manifest.json` 字段说明：

- `source`：`wikisource` 或 `synthetic`
- `kind`：均为 `full`（全本）
- `crawled_full_count` / `synthetic_full_count`：实际数量
- `license`：`Public Domain` 或 `Synthetic Test Data`

测试：`pytest tests/test_bulk_corpus.py`

测试记录见 [`TEST-RECORD.md`](TEST-RECORD.md)，可通过以下命令重新生成：

```bash
python scripts/record_pd_sample_tests.py
```

## 许可证

样本文本属于公有领域，可自由用于测试与演示。重新分发时请保留 `manifest.json` 中的 `source_url` 与 `license` 字段。合成测试文本仅用于自动化测试，不代表真实文学作品。
