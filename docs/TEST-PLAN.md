# Novel2Script 测试计划

> 版本：1.0  
> 最后更新：2026-06-05  
> 关联文档：[PRD.md](./PRD.md)、[YAML-SCHEMA.md](./YAML-SCHEMA.md)、[USER-GUIDE.md](./USER-GUIDE.md)

---

## 1. 测试范围与策略

### 1.1 测试目标

验证 Novel2Script 满足赛题与 PRD 要求：3 章以上小说输入 → 结构化 YAML 剧本输出，Schema 校验通过，CLI/Web 可用。

### 1.2 测试分层

| 层级 | 目录/标记 | 依赖 | 执行频率 |
|------|-----------|------|----------|
| 单元测试 | `tests/test_*.py`（除 integration） | Mock LLM，无网络 | 每次提交 |
| API 测试 | `tests/test_api.py` | TestClient + Mock | 每次提交 |
| CLI 测试 | `tests/test_cli.py` | CliRunner + Mock | 每次提交 |
| 集成测试 | `tests/test_integration.py` | `@pytest.mark.integration`，需 API Key | 手动/CI optional |
| 冒烟测试 | CI 中 `novel2script validate` | 示例 YAML | 每次提交 |

### 1.3 通过标准

- `pytest -m "not integration"` 全部 PASS
- 示例 [`examples/sample-screenplay.yaml`](../examples/sample-screenplay.yaml) 校验结果为 PASS 或 PASS_WITH_WARNINGS
- 章节覆盖率 100%（每个输入章节出现在 source_refs）

---

## 2. 需求追溯矩阵

| 需求 ID | 来源 | 测试用例 ID | 描述 |
|---------|------|-------------|------|
| US-01 | PRD | TC-PARSER-001~006, TC-PIPE-001 | 3+ 章识别与转换 |
| US-02 | PRD | TC-VAL-010~012, TC-PIPE-001 | source_refs 溯源 |
| US-03 | PRD | TC-EMIT-001~002 | YAML 可序列化/反序列化 |
| US-04 | PRD | TC-PIPE-003, TC-ADAPT-004 | warnings 透明标记 |
| US-05 | PRD | TC-EMIT-003~004, TC-PIPE-002 | 转换报告 stats |
| US-06 | PRD | TC-REG-001~002 | 角色 ID 跨章一致 |
| F-01 | PRD | TC-PARSER-001~006 | 文本输入与章节识别 |
| F-04 | PRD | TC-VAL-001~012 | Schema 校验 |
| F-05 | PRD | TC-EMIT-003, TC-API-004 | 转换报告 |
| §6.1 | Schema | TC-VAL-001~006 | 结构校验 |
| §6.2 | Schema | TC-VAL-007~009 | 引用完整性 |
| §6.3 | Schema | TC-VAL-010~012 | 章节覆盖度 |
| §6.4 | Schema | TC-VAL-013~015 | 内容质量 warning |
| §6.5 | Schema | TC-VAL-001~015 | 结果分级 PASS/FAIL |
| USER-GUIDE §3 | 用户指南 | TC-PARSER-004~005 | 章节/字数上限 |
| Web UI | 架构 | TC-API-001~006 | FastAPI 端点 |
| CLI | 架构 | TC-CLI-001~004 | Typer 命令 |

---

## 3. YAML Schema 校验矩阵（§6）

| 规则 | 用例 ID | 测试函数 | 预期 |
|------|---------|----------|------|
| §6.1-1 schema_version=1.0 | TC-VAL-001 | test_invalid_schema_version | FAIL |
| §6.1-3 chapter_count≥3 | TC-VAL-002 | test_chapter_count_below_three | FAIL |
| §6.1-4 chapters 长度一致 | TC-VAL-003 | test_chapter_count_mismatch | FAIL |
| §6.1-5 scenes≥1 | TC-VAL-004 | test_empty_scenes | FAIL |
| §6.2-1 characters_present 有效 | TC-VAL-005 | test_invalid_character_reference_fails | FAIL |
| §6.2-2 dialogue character_id | TC-VAL-006 | test_dialogue_unknown_character | FAIL |
| §6.2-2 voiceover character_id | TC-VAL-007 | test_voiceover_unknown_character | FAIL |
| §6.2-3 location_id 有效 | TC-VAL-008 | test_invalid_location_ref | FAIL |
| §6.2-4 acts.scenes 有效 | TC-VAL-009 | test_invalid_act_scene_ref | FAIL |
| §6.3 章节全覆盖 | TC-VAL-010 | test_missing_chapter_coverage_fails | FAIL |
| §6.3 示例全覆盖 | TC-VAL-011 | test_sample_screenplay_passes | PASS* |
| §6.4-1 action 过长 | TC-VAL-013 | test_action_too_long_warning | PASS_WITH_WARNINGS |
| §6.4-3 voiceover 过多 | TC-VAL-015 | test_voiceover_excess_warning | PASS_WITH_WARNINGS |
| §6.5 分级 | TC-VAL-011~015 | 各用例 | 见上 |

---

## 4. 用例详表

### 4.1 章节解析（TC-PARSER）

| ID | 用例名 | 前置条件 | 步骤 | 预期 | 优先级 |
|----|--------|----------|------|------|--------|
| TC-PARSER-001 | 中文章节识别 | 示例小说 | parse_chapters | 3 章，标题正确 | P0 |
| TC-PARSER-002 | 英文章节识别 | 构造文本 | parse_chapters | 3 章 | P0 |
| TC-PARSER-003 | Markdown 章节 | 构造文本 | parse_chapters | 3 章 | P1 |
| TC-PARSER-004 | 不足 3 章 | 2 章文本 | parse_chapters | InsufficientChaptersError | P0 |
| TC-PARSER-005 | 超过 20 章 | 21 章文本 | parse_chapters | LimitExceededError | P1 |
| TC-PARSER-006 | 空文本 | 空字符串 | parse_chapters | ChapterParseError | P0 |
| TC-PARSER-007 | 无章节标题 | 纯段落 | parse_chapters | ChapterParseError | P1 |
| TC-PARSER-008 | 章节 ID 连续 | 示例小说 | parse_chapters | chapter_01~03 | P1 |

### 4.2 Schema 校验（TC-VAL）

见 §3 矩阵及 `tests/test_schema_validation.py`。

### 4.3 YAML 输出（TC-EMIT）

| ID | 用例名 | 预期 | 优先级 |
|----|--------|------|--------|
| TC-EMIT-001 | 序列化含 schema_version | YAML 字符串合法 | P0 |
| TC-EMIT-002 | roundtrip 一致 | load(serialize(sp))==sp | P0 |
| TC-EMIT-003 | write 生成 report | .yaml + .report.json | P0 |
| TC-EMIT-004 | report stats 字段 | chapters/scenes/characters/warnings | P1 |
| TC-EMIT-005 | 多行 action 块标量 | 含 `\|` | P2 |

### 4.4 场次改编（TC-ADAPT）

| ID | 用例名 | 预期 | 优先级 |
|----|--------|------|--------|
| TC-ADAPT-001 | scene_id 递增 | scene_001, 002... | P0 |
| TC-ADAPT-002 | excerpt 截断 | len≤200 | P1 |
| TC-ADAPT-003 | 空 source_refs 补全 | 自动填充 excerpt | P1 |
| TC-ADAPT-004 | SCENE_SPLIT warning | 多 scene 时有 info | P2 |

### 4.5 LLM 客户端（TC-LLM）

| ID | 用例名 | 预期 | 优先级 |
|----|--------|------|--------|
| TC-LLM-001 | Mock 实体抽取 | EntityExtractionResult | P0 |
| TC-LLM-002 | Mock 场次改编 | AdaptationChapterResult | P0 |
| TC-LLM-003 | JSON markdown 剥离 | _extract_json 正确 | P1 |
| TC-LLM-004 | 调用计数 | calls 递增 | P2 |

### 4.6 流水线（TC-PIPE）

| ID | 用例名 | 预期 | 优先级 |
|----|--------|------|--------|
| TC-PIPE-001 | Mock 端到端 | PASS*, 3 章覆盖 | P0 |
| TC-PIPE-002 | convert_file 写盘 | 文件存在 | P0 |
| TC-PIPE-003 | warnings 存在 | 列表非空 | P1 |
| TC-PIPE-004 | title/author 覆盖 | meta 正确 | P1 |

### 4.7 API（TC-API）

| ID | 用例名 | 预期 | 优先级 |
|----|--------|------|--------|
| TC-API-001 | GET /api/health | 200 ok | P0 |
| TC-API-002 | GET / | 200 HTML | P0 |
| TC-API-003 | POST /api/convert 成功 | 200 + yaml_content | P0 |
| TC-API-004 | report 结构完整 | stats 字段 | P1 |
| TC-API-005 | 无 API Key | 503 | P1 |
| TC-API-006 | 2 章输入 | 422 | P1 |
| TC-API-007 | 非 UTF-8 | 400 | P2 |

### 4.8 CLI（TC-CLI）

| ID | 用例名 | 预期 | 优先级 |
|----|--------|------|--------|
| TC-CLI-001 | validate 示例 | exit 0 | P0 |
| TC-CLI-002 | validate 不存在文件 | exit 1 | P1 |
| TC-CLI-003 | convert 写输出 | yaml+report | P0 |
| TC-CLI-004 | convert 2 章失败 | exit 非 0 | P1 |

### 4.9 集成（TC-INT）

| ID | 用例名 | 预期 | 优先级 |
|----|--------|------|--------|
| TC-INT-001 | 真实 LLM 转换 | PASS*, 需 API Key | P2 |

---

## 5. 执行说明

### 5.1 本地运行

```bash
pip install -e ".[dev]"

# 全部单元/API/CLI 测试（无需 API Key）
pytest -v -m "not integration"

# 含覆盖率
pytest -m "not integration" --cov=novel2script --cov-report=term-missing

# 真实 LLM 集成测试
LLM_API_KEY=sk-xxx pytest -m integration -v

# CLI 冒烟
novel2script validate examples/sample-screenplay.yaml
```

### 5.2 CI

GitHub Actions 工作流 [`.github/workflows/test.yml`](../.github/workflows/test.yml) 在 push/PR 时自动执行：

1. `pytest -q -m "not integration"`
2. `novel2script validate examples/sample-screenplay.yaml`

### 5.3 测试数据

| 文件 | 用途 |
|------|------|
| `examples/sample-novel-chapters.txt` | 合法 3 章输入 |
| `examples/sample-screenplay.yaml` | 合法输出样例 |
| `tests/fixtures/novel_two_chapters.txt` | 不足 3 章 |
| `tests/fixtures/novel_empty.txt` | 空输入 |
| `tests/fixtures/invalid_*.yaml` | 非法 YAML |
| `tests/conftest.py` | screenplay_factory、Mock LLM |

---

## 6. 用例统计

| 模块 | 用例数 |
|------|--------|
| 章节解析 | 8 |
| Schema 校验 | 15 |
| YAML 输出 | 5 |
| 场次改编 | 4 |
| LLM 客户端 | 4 |
| 实体注册 | 2 |
| 流水线 | 5 |
| API | 7 |
| CLI | 4 |
| 集成 | 1 |
| **合计** | **55** |

---

## 7. 变更记录

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-06-05 | 初始版本，覆盖 MVP 全模块 |
