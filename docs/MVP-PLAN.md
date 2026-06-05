# MVP 实现计划

> 版本：1.0  
> 最后更新：2026-06-05

---

## 1. 目标

在 4 周内交付可运行的 CLI 工具，实现「3 章以上小说 → 结构化 YAML 剧本」的核心链路，并通过 Schema 校验与样例回归测试验证质量。

---

## 2. 里程碑

### M0：文档与规范（第 1 周）

| 任务 | 产出 | 状态 |
|------|------|------|
| PRD 编写 | `docs/PRD.md` | 完成 |
| YAML Schema 规范 | `docs/YAML-SCHEMA.md` | 完成 |
| 技术架构文档 | `docs/ARCHITECTURE.md` | 完成 |
| 示例小说 + 示例剧本 | `examples/` | 完成 |
| 合并长文档 | `PROJECT-DOCUMENT.md` | 完成 |

**验收标准**：Schema 文档可被第三方独立实现；示例 YAML 通过全部校验规则。

---

### M1：核心管道（第 2 周）

| 任务 | 产出 | 优先级 |
|------|------|--------|
| 项目脚手架 | `pyproject.toml`, 目录结构 | P0 |
| Pydantic 模型 | `src/models/schema.py` | P0 |
| 章节解析器 | `src/parser/chapter.py` | P0 |
| LLM 客户端 | `src/llm/client.py` | P0 |
| 实体抽取 | `src/extractor/entity.py` | P0 |
| 场次改编 | `src/adapter/scene_adapter.py` | P0 |
| YAML 输出 | `src/emitter/yaml_writer.py` | P0 |
| CLI 入口 | `src/cli/main.py` | P0 |

**验收标准**：

```bash
novel2script convert examples/sample-novel-chapters.txt -o /tmp/out.yaml
# 输出合法 YAML，scenes ≥ 1，覆盖 3 章
```

**关键命令**：

```bash
novel2script convert <input> -o <output.yaml> [--model gpt-4o] [--provider openai]
```

---

### M2：质量保障（第 3 周）

| 任务 | 产出 | 优先级 |
|------|------|--------|
| Schema 校验器 | `src/validator/validate.py` | P0 |
| warnings 生成逻辑 | 集成到 adapter | P0 |
| 章节覆盖度检查 | validator 业务规则 | P0 |
| 单元测试：章节解析 | `tests/test_chapter_parser.py` | P0 |
| 单元测试：Schema 校验 | `tests/test_schema_validation.py` | P0 |
| 回归测试：样例端到端 | `tests/test_e2e.py` | P1 |
| LLM 输出修复轮 | adapter retry 逻辑 | P1 |

**验收标准**：

- `pytest` 全部通过
- 样例小说转换后校验结果为 PASS 或 PASS_WITH_WARNINGS
- 3 章全部出现在 source_refs 中

---

### M3：体验完善（第 4 周）

| 任务 | 产出 | 优先级 |
|------|------|--------|
| 转换报告 | `conversion-report.json` 输出 | P1 |
| README | 安装、配置、使用说明 | P0 |
| 用户指南 | `docs/USER-GUIDE.md` | 完成 |
| 错误信息优化 | CLI 友好提示 | P1 |
| 配置文档 | `.env.example` | P1 |
| Web UI（可选） | FastAPI + 简单上传页 | P2 |

**验收标准**：

- 新用户按 README 可在 10 分钟内完成首次转换
- 转换报告包含：场次数、角色数、警告列表、耗时

---

## 3. 任务分解（WBS）

```
M1 核心管道
├── 1.1 项目初始化
│   ├── pyproject.toml（依赖：pydantic, typer, pyyaml, litellm, pytest）
│   └── src/ 目录结构
├── 1.2 数据模型
│   ├── Screenplay, Meta, Character, Location, Scene, Element, Warning
│   └── JSON Schema 导出脚本
├── 1.3 章节解析
│   ├── 正则模式匹配
│   ├── 章节数校验（≥3）
│   └── 字数统计
├── 1.4 LLM 集成
│   ├── 统一 Client 接口
│   ├── OpenAI / Ollama 适配
│   └── JSON mode 输出
├── 1.5 改编引擎
│   ├── Prompt 模板
│   ├── 按章调用 + 结果合并
│   └── scene_id 自动分配
├── 1.6 输出
│   ├── YAML 序列化（ruamel.yaml）
│   └── CLI 命令
└── 1.7 冒烟测试
    └── 样例小说端到端

M2 质量保障
├── 2.1 校验器
│   ├── Pydantic 模型校验
│   ├── 引用完整性
│   └── 章节覆盖度
├── 2.2 warnings
│   ├── 推断类 warning 自动生成
│   └── 校验失败 error warning
├── 2.3 修复轮
│   └── LLM 修复 JSON 结构（最多 2 轮）
└── 2.4 测试
    ├── 单元测试
    └── 回归 fixture

M3 体验完善
├── 3.1 转换报告
├── 3.2 README + .env.example
├── 3.3 CLI 错误优化
└── 3.4 Web UI（可选）
```

---

## 4. 技术依赖

```toml
# pyproject.toml 核心依赖
[project]
name = "novel2script"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "typer>=0.9",
    "ruamel.yaml>=0.18",
    "litellm>=1.0",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio"]

[project.scripts]
novel2script = "src.cli.main:app"
```

---

## 5. 风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| LLM 输出 JSON 不稳定 | 高 | 高 | JSON mode + 重试 + 修复轮；降级为逐场生成 |
| 长章节 token 超限 | 中 | 高 | 按章分片；单章超 8000 字则按段落二次分片 |
| 角色名不一致 | 中 | 中 | 全局 Registry + 别名表；Prompt 注入已知角色 |
| 改编质量参差 | 中 | 中 | warnings 透明标记；提供示例供 Few-shot |
| API 成本过高 | 低 | 中 | 支持 Ollama 本地模型；按章计费可控 |
| 章节格式识别失败 | 中 | 中 | 支持多种模式；允许用户自定义正则 |
| Schema 演进破坏兼容 | 低 | 低 | schema_version 字段；变更日志 |

---

## 6. 质量门禁

每个里程碑结束前必须通过：

| 门禁 | 标准 |
|------|------|
| Schema 合规 | 输出 YAML 通过 validator |
| 章节覆盖 | 全部输入章节出现在 source_refs |
| 测试 | `pytest` 零失败 |
| 文档 | README 可指导新用户完成首次转换 |
| 示例 | examples/ 中样例可复现 |

---

## 7. 团队分工建议

| 角色 | 职责 | M1 | M2 | M3 |
|------|------|----|----|-----|
| 后端开发 A | 解析器 + 模型 + 校验 | 主 | 辅 | — |
| 后端开发 B | LLM 集成 + 改编引擎 | 主 | 主 | — |
| 产品/测试 | 文档 + 测试 + 样例 | 辅 | 主 | 主 |
| 前端（可选） | Web UI | — | — | 主 |

2 人小团队：开发 A 负责 M1 全部 + M2 校验；开发 B 负责 Prompt 调优 + M2 测试 + M3。

---

## 8. 交付清单

### 8.1 文档交付

- [x] `docs/PRD.md`
- [x] `docs/YAML-SCHEMA.md`
- [x] `docs/ARCHITECTURE.md`
- [x] `docs/MVP-PLAN.md`
- [x] `docs/USER-GUIDE.md`
- [x] `PROJECT-DOCUMENT.md`
- [x] `examples/sample-novel-chapters.txt`
- [x] `examples/sample-screenplay.yaml`

### 8.2 代码交付（M1–M3）

- [ ] `src/` 完整源码
- [ ] `tests/` 测试套件
- [ ] `pyproject.toml`
- [ ] `README.md`
- [ ] `.env.example`

---

## 9. 后续路线图（MVP 后）

| 版本 | 时间 | 功能 |
|------|------|------|
| V1.1 | +2 周 | Fountain 导出、Web UI |
| V1.2 | +2 周 | 场次 AI 重写、多轮对话 |
| V2.0 | +4 周 | 英文支持、PDF 导出、角色关系图 |
