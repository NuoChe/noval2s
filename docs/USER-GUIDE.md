# 用户使用指南

> 版本：1.0  
> 最后更新：2026-06-05

---

## 1. 简介

Novel2Script 是一款 AI 辅助工具，可将你的小说章节（3 章以上）自动转换为结构化的 YAML 剧本初稿。输出的 YAML 文件可直接用任何文本编辑器修改，也可纳入 Git 进行版本管理。

---

## 2. 快速开始

### 2.1 安装（MVP 阶段）

```bash
# 克隆项目
git clone <repo-url>
cd novel2script

# 安装依赖
pip install -e .

# 配置 API Key
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY
```

### 2.2 第一次转换

```bash
novel2script convert examples/sample-novel-chapters.txt -o my-screenplay.yaml
```

转换完成后，你将获得：

- `my-screenplay.yaml` — 结构化剧本文件
- `my-screenplay.report.json` — 转换报告

---

## 3. 输入要求

### 3.1 文件格式

支持 **TXT** 和 **Markdown（.md）** 文件，UTF-8 编码。

### 3.2 章节格式

工具自动识别以下章节标题格式：

| 格式 | 示例 |
|------|------|
| 中文章节 | `第一章 初遇`、`第2章 误会` |
| 章回体 | `第一回 开端`、`第十二回 续` |
| 英文章节 | `Chapter 1: Encounter`、`Chapter 2` |
| Markdown 标题 | `# 初遇`、`## 误会` |

**示例输入**：

```text
第一章 初遇

周默推开门，风铃叮当作响。柜台后坐着一个扎马尾的女孩……

第二章 误会

第二天，周默再次来到书店。苏晚的态度明显冷了许多……

第三章 和解

一场暴雨困住了周默。书店里只剩下他们两人……
```

### 3.2.1 示例小说库

项目内置若干公有领域小说样本，位于 `examples/novels/`，可直接用于 CLI 或 Web UI 测试：

```bash
novel2script convert examples/novels/niehaihua.txt -o niehaihua.yaml
```

样本清单见 `examples/novels/manifest.json`（来源、作者、license）。如需更新样本：

```bash
python scripts/fetch_pd_novels.py --chapters 3
```

详见 `tests/fixtures/novels/README.md`。

样本默认为**简体中文**（维基文库 `zh-hans` + OpenCC）。重新采集：

```bash
python scripts/fetch_pd_novels.py --chapters 3 --simplified
```

### 3.3 数量限制

| 限制 | 默认值 |
|------|--------|
| 最少章节 | 3 章 |
| 最多章节 | 20 章 |
| 最大字数 | 10 万字 |

不足 3 章时，工具会拒绝处理并提示。

### 3.4 输入建议

- 每章建议 1000–5000 字，过长章节会增加转换时间
- 章节标题清晰，便于溯源对照
- 对话较多的章节转换质量更高
- 避免单文件混入非小说内容（序言、作者的话等）

---

## 4. 命令行用法

### 4.1 基本命令

```bash
novel2script convert <输入文件> -o <输出文件.yaml>
```

### 4.2 常用选项

| 选项 | 说明 | 示例 |
|------|------|------|
| `-o, --output` | 输出 YAML 路径 | `-o screenplay.yaml` |
| `--model` | 指定 LLM 模型 | `--model gpt-4o` |
| `--provider` | 指定 LLM 提供商 | `--provider openai` |
| `--title` | 覆盖作品标题 | `--title "晚风书店"` |
| `--author` | 覆盖作者名 | `--author "张三"` |
| `--validate-only` | 仅校验已有 YAML | `--validate-only out.yaml` |

### 4.3 使用本地模型（Ollama）

```bash
export LLM_PROVIDER=ollama
export LLM_MODEL=qwen2.5:14b
export LLM_BASE_URL=http://localhost:11434

novel2script convert input.txt -o output.yaml
```

---

## 5. 理解输出

### 5.1 YAML 剧本结构

输出文件遵循 [YAML Schema 规范](./YAML-SCHEMA.md)，核心部分：

```yaml
schema_version: "1.0"
meta:           # 作品信息、源章节、改编信息
characters:     # 角色表
locations:      # 地点表
scenes:         # 场次列表（核心内容）
warnings:       # AI 推断/待确认项
```

### 5.2 场次（Scene）结构

每场戏包含：

```yaml
- id: scene_001
  slugline:                    # 场次标题
    heading: "内景 晚风书店 - 日"
  summary: "周默与苏晚初次相遇"  # 一句话概述
  source_refs:                 # 原文溯源
    - chapter_id: chapter_01
      excerpt: "周默推开门……"
  characters_present: [char_zhou_mo, char_su_wan]
  elements:                    # 场次内容
    - type: action
      text: "风铃轻响。周默推门进入。"
    - type: dialogue
      character_id: char_su_wan
      lines: "随便看。"
```

### 5.3 元素类型

| 类型 | 含义 | 编辑建议 |
|------|------|----------|
| `action` | 动作/环境描述 | 确保可被摄影机拍到，删除心理描写 |
| `dialogue` | 角色对白 | 检查是否符合角色性格 |
| `voiceover` | 画外音/旁白 | 尽量少用，考虑改为 action 或 dialogue |
| `transition` | 转场 | 如「切至」「淡入」 |

### 5.4 转换报告

`*.report.json` 示例：

```json
{
  "status": "PASS_WITH_WARNINGS",
  "stats": {
    "chapters": 3,
    "scenes": 8,
    "characters": 2,
    "locations": 3,
    "warnings": 4
  },
  "duration_sec": 142,
  "warnings_summary": [
    {"code": "TIME_INFERRED", "count": 2},
    {"code": "DIALOGUE_SYNTHESIZED", "count": 2}
  ]
}
```

---

## 6. 编辑工作流

### 6.1 推荐流程

```
1. 阅读 conversion report，了解整体规模与 warnings
2. 逐场阅读 scenes，对照 source_refs 中的 excerpt
3. 重点审核 warnings 标记的场次
4. 修改 action/dialogue 内容
5. 调整场次划分（拆分/合并 scenes）
6. 更新 characters_present 和 characters 表
7. 运行 validate-only 确认格式正确
```

### 6.2 常见编辑操作

#### 修改对白

```yaml
# 修改前
- type: dialogue
  character_id: char_zhou_mo
  lines: "你也喜欢这本？"

# 修改后：增加 parenthetical，调整台词
- type: dialogue
  character_id: char_zhou_mo
  parenthetical: "惊讶地"
  lines: "你也喜欢这本？我找了它好久了。"
```

#### 拆分场次

当一个 scene 包含两个时间/地点不同的段落时，拆为两个 scene：

```yaml
# 原 scene_003 末尾添加转场
- type: transition
  text: "切至"

# 新建 scene_004
- id: scene_004
  slugline:
    heading: "外景 书店门口 - 夜"
  ...
```

#### 删除旁白

将 `voiceover` 改为 `action` 或删除：

```yaml
# 不推荐
- type: voiceover
  character_id: char_zhou_mo
  text: "他心想，这个女生真特别。"

# 推荐：改为可见动作
- type: action
  text: "周默微微笑了笑，把书放回架上。"
```

### 6.3 版本管理

YAML 文件非常适合 Git 管理：

```bash
git init
git add screenplay.yaml
git commit -m "AI 初稿 v1"

# 修改后
git diff screenplay.yaml
git commit -m "精修第 1-3 场对白"
```

---

## 7. 理解 Warnings

Warnings 是 AI Transparent 机制的核心。请重点审核以下类型：

| 警告码 | 含义 | 建议操作 |
|--------|------|----------|
| `LOCATION_INFERRED` | 地点是 AI 猜的 | 对照原文确认或修改 slugline |
| `TIME_INFERRED` | 时间是 AI 猜的 | 确认日/夜是否正确 |
| `DIALOGUE_SYNTHESIZED` | 对白是 AI 编的 | 对照原文，决定是否保留 |
| `INNER_MONOLOGUE_OMITTED` | 内心独白被省略 | 决定是否转为 action/dialogue |
| `SCENE_SPLIT` | 一段拆成多场 | 确认场次划分是否合理 |
| `SCENE_MERGED` | 多段合成一场 | 确认是否需要拆分 |

---

## 8. 校验

编辑完成后，校验 YAML 格式：

```bash
novel2script validate screenplay.yaml
```

输出：

```
✓ Schema version: 1.0
✓ Structure validation: PASS
✓ Reference integrity: PASS
✓ Chapter coverage: 3/3 chapters referenced
⚠ 2 warnings (0 errors)

Result: PASS_WITH_WARNINGS
```

---

## 9. 常见问题

### Q: 转换时间很长？

3 章约 2–5 分钟，取决于 LLM 速度。使用本地 Ollama 可能更慢但无 API 费用。

### Q: 角色名不一致？

检查 `characters` 表中的 `aliases` 字段。AI 会将「周先生」「周默」合并为同一角色，但若合并错误，可手动拆分 ID。

### Q: 某章没有出现在剧本中？

运行 `validate` 检查章节覆盖度。若缺失，可能是该章内容难以视觉化（如纯心理描写），可手动补充 scene。

### Q: 如何导出为标准剧本格式？

V1.1 将支持 Fountain 导出：

```bash
novel2script export screenplay.yaml -f fountain -o screenplay.fountain
```

### Q: 原文隐私如何保障？

使用 Ollama 本地模型时，文本不会离开你的电脑。使用云 API 时，原文会发送至对应服务商，请查阅其隐私政策。

---

## 10. 获取帮助

```bash
novel2script --help
novel2script convert --help
```

完整 Schema 定义见 [YAML-SCHEMA.md](./YAML-SCHEMA.md)。
