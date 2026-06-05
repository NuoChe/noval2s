# 剧本 YAML Schema 规范

> 版本：1.0  
> 适用工具：AI 小说转剧本工具  
> 最后更新：2026-06-05

---

## 1. 概述

本规范定义了 AI 小说转剧本工具的输出格式——**结构化 YAML 剧本**。该格式旨在：

- 让 AI 能够稳定、可校验地生成剧本初稿
- 让作者能够像编辑代码一样 diff、版本管理、协作修改
- 作为中间层，可进一步导出为 Fountain、Final Draft 等行业标准格式

---

## 2. 设计原则与设计原因

| 设计原则 | 设计原因 |
|----------|----------|
| **场次（Scene）为一等公民** | 影视制作以「场」为单位调度、拍摄、预算，而非小说的「章」。将 `scenes` 作为核心数组，使输出直接对齐生产流程。 |
| **保留原文溯源（provenance）** | AI 改编必然存在删改与推断。每场戏通过 `source_refs` 关联原文章节与段落，作者可快速对照原文，避免「黑盒改编」带来的信任问题。 |
| **角色/地点注册表** | 小说中同一人物有多种称呼（「黛玉」「林妹妹」「潇湘妃子」）。全局 `characters` 与 `locations` 表提供稳定 ID，避免每场重复定义，并支持戏份统计与一致性校验。 |
| **动作与对白分离** | 行业标准剧本将 Action（动作行）与 Dialogue（对白行）严格区分。独立 `elements` 类型使输出可映射至 Fountain 格式，也便于作者按类型批量修改。 |
| **元数据与正文分离** | `meta` 块存放标题、作者、模型版本等信息，不参与场次编辑。作者修改剧本时只需关注 `scenes`，减少误改。 |
| **warnings 显式列出** | AI 对地点、时间、对白外化等推断应透明呈现。静默省略会导致作者误以为 AI 输出即原文忠实还原。 |
| **选用 YAML 而非 JSON** | 剧本含大量多行对白与动作描述。YAML 的 `\|` 块标量支持换行，人类可读性远优于 JSON 转义字符串。 |
| **可选 acts 分层** | 长篇改编常按「幕」组织。`acts` 为可选字段，不影响短篇或单幕作品，但为长篇提供大纲视图。 |

---

## 3. 顶层结构

```yaml
schema_version: "1.0"    # 必填，Schema 版本号
meta: { ... }             # 必填，元数据
characters: [ ... ]       # 必填，角色注册表（可为空数组，但不建议）
locations: [ ... ]        # 可选，地点注册表
acts: [ ... ]             # 可选，幕结构
scenes: [ ... ]           # 必填，场次列表（至少 1 场）
warnings: [ ... ]         # 可选，转换警告
```

---

## 4. 字段定义

### 4.1 `schema_version`

| 属性 | 值 |
|------|-----|
| 类型 | `string` |
| 必填 | 是 |
| 当前值 | `"1.0"` |

标识本文件遵循的 Schema 版本，便于工具升级时做向后兼容处理。

---

### 4.2 `meta`

作品及改编过程的元信息。

```yaml
meta:
  title: string           # 必填，作品名称
  author: string          # 必填，小说原作者
  adapted_by: string      # 可选，改编者或工具标识
  source:                 # 必填，源文本信息
    format: novel         # 固定值：novel
    chapter_count: int    # 必填，源章节总数
    chapters:             # 必填，章节列表
      - id: string        # 章节 ID，如 chapter_01
        title: string     # 章节标题
        word_count: int   # 该章字数
  adaptation:             # 必填，改编信息
    created_at: string    # ISO 8601 时间戳
    model: string         # 使用的 AI 模型名称
    prompt_version: string # Prompt 模板版本
```

**设计原因**：`source.chapters` 记录输入边界，校验时可确认「是否覆盖了全部输入章节」。`adaptation` 块使同一小说多次改编的结果可对比（模型升级、Prompt 迭代）。

---

### 4.3 `characters`

角色注册表，按首次出场顺序排列。

```yaml
characters:
  - id: string                    # 必填，稳定 ID，格式：char_{拼音或英文}
    name: string                  # 必填，主要显示名
    aliases: [string]             # 可选，别名列表
    description: string           # 可选，角色简介（≤100 字）
    first_appearance:             # 可选，首次出场位置
      scene_id: string
      chapter_id: string
```

**ID 命名规范**：

- 使用小写字母、数字、下划线
- 前缀 `char_`，如 `char_lin_mo`、`char_protagonist`
- 同一人物在全文中 ID 不可变

**设计原因**：对白元素通过 `character_id` 引用角色，而非直接写名字，避免「张三/张先生/张总」被识别为三个角色。

---

### 4.4 `locations`

地点注册表。

```yaml
locations:
  - id: string                    # 必填，格式：loc_{名称拼音}
    name: string                  # 必填，地点名称
    int_ext: interior | exterior | mixed  # 必填，内/外/混合
    description: string           # 可选，地点描述
```

**设计原因**：`slugline.location_id` 引用地点 ID，`int_ext` 在地点层提供默认值，场次层可覆盖。

---

### 4.5 `acts`（可选）

按幕组织场次，适用于长篇或多幕结构。

```yaml
acts:
  - id: string          # 必填，如 act_1
    title: string       # 可选，幕标题
    scenes: [string]    # 必填，该幕包含的 scene_id 列表，有序
```

**设计原因**：章节≠幕。AI 改编时可能将多章合并为一幕，或一章拆为多幕。`acts` 提供大纲视图，不影响 `scenes` 的完整性。

---

### 4.6 `scenes`

场次列表，剧本核心内容。

```yaml
scenes:
  - id: string                    # 必填，格式：scene_{三位数字}，如 scene_001
    slugline:                     # 必填，场次标题（Scene Heading）
      int_ext: interior | exterior
      location_id: string         # 引用 locations[].id，或直接内联见下方
      location_name: string       # 若无 location_id，可内联地点名
      time_of_day: day | night | dawn | dusk | continuous | unspecified
      heading: string             # 必填，完整标题行，如「内景 林家旧宅 客厅 - 日」
    summary: string               # 可选，本场一句话概述（≤50 字）
    source_refs:                  # 必填，原文溯源（至少 1 条）
      - chapter_id: string
        excerpt: string           # 原文摘要或引用，≤200 字
        paragraph_range: [int, int]  # 可选，段落起止索引（从 0 开始）
    characters_present: [string]  # 必填，出场角色 ID 列表
    elements: [ ... ]             # 必填，场次内容元素（至少 1 个）
    estimated_duration_min: float # 可选，预估时长（分钟）
```

**slugline 设计原因**：`heading` 为人类可读的完整标题行，可直接导出为 Fountain 的 Scene Heading；结构化字段（`int_ext`、`time_of_day`）便于程序筛选「全部夜戏」等。

**source_refs 设计原因**：改编是创造性劳动，AI 初稿必须可追溯。`excerpt` 帮助作者 3 秒内定位原文上下文。

---

### 4.7 `elements`

场次内的有序内容元素。通过 `type` 字段区分类型，不同类型携带不同字段。

#### 4.7.1 `action` — 动作/环境描述

```yaml
- type: action
  text: string    # 必填，可视化的动作或环境描写，支持多行（| 块标量）
```

**设计原因**：小说中的叙述性文字需改写为「可被摄影机拍到」的内容。心理独白不应出现在 action 中，应转为 dialogue 或 voiceover。

#### 4.7.2 `dialogue` — 角色对白

```yaml
- type: dialogue
  character_id: string       # 必填，引用 characters[].id
  lines: string              # 必填，台词内容，支持多行
  parenthetical: string      # 可选，括号内语气/动作提示，如「轻声」「转向窗口」
```

**设计原因**：对标行业标准剧本格式——角色名 + 可选括号提示 + 台词。`parenthetical` 合并为 dialogue 的子字段，而非独立 element，因其从属于对白。

#### 4.7.3 `voiceover` — 画外音/旁白

```yaml
- type: voiceover
  character_id: string    # 可选，若为角色内心独白则引用角色 ID
  text: string            # 必填，旁白内容
```

**设计原因**：极少数无法外化的内心活动可保留为 V.O.，但应节制使用。独立类型便于作者统计「旁白占比」并批量删减。

#### 4.7.4 `transition` — 转场

```yaml
- type: transition
  text: string    # 必填，如「切至」「淡入」「黑屏」
```

**设计原因**：转场在 Fountain 中右对齐独立成行。独立类型便于导出时格式化。

---

### 4.8 `warnings`

AI 转换过程中产生的警告与待确认项。

```yaml
warnings:
  - code: string              # 必填，警告码（见下表）
    scene_id: string          # 可选，关联场次
    message: string           # 必填，人类可读说明
    severity: info | warning | error  # 必填
```

**警告码枚举**：

| code | severity | 含义 |
|------|----------|------|
| `LOCATION_INFERRED` | warning | 地点由 AI 推断，原文未明确 |
| `TIME_INFERRED` | warning | 时间（日/夜）由 AI 推断 |
| `DIALOGUE_SYNTHESIZED` | warning | 对白由 AI 从叙述外化，原文无直接引语 |
| `CHARACTER_MERGED` | info | 多个称呼合并为同一角色 |
| `SCENE_SPLIT` | info | 原文一段拆分为多个场次 |
| `SCENE_MERGED` | info | 原文多段合并为一个场次 |
| `INNER_MONOLOGUE_OMITTED` | info | 内心独白已省略或转为动作 |
| `MISSING_SOURCE_REF` | error | 场次缺少原文溯源 |
| `INVALID_CHARACTER_REF` | error | 引用了不存在的 character_id |

**设计原因**：透明度是 AI 工具可信度的核心。作者应明确知道「哪些是 AI 编的」。

---

## 5. 完整示例

参见 [`examples/sample-screenplay.yaml`](../examples/sample-screenplay.yaml)。

最小合法示例：

```yaml
schema_version: "1.0"

meta:
  title: "示例作品"
  author: "作者甲"
  adapted_by: "novel2script/1.0"
  source:
    format: novel
    chapter_count: 3
    chapters:
      - id: chapter_01
        title: "初遇"
        word_count: 3200
      - id: chapter_02
        title: "误会"
        word_count: 4100
      - id: chapter_03
        title: "和解"
        word_count: 3800
  adaptation:
    created_at: "2026-06-05T10:00:00+08:00"
    model: "gpt-4o"
    prompt_version: "v1.2"

characters:
  - id: char_zhou_mo
    name: "周默"
    aliases: ["小周"]
    description: "青年程序员，内向但执着"
    first_appearance:
      scene_id: scene_001
      chapter_id: chapter_01

  - id: char_su_wan
    name: "苏晚"
    aliases: ["晚晚"]
    description: "独立书店店主，温和敏锐"
    first_appearance:
      scene_id: scene_001
      chapter_id: chapter_01

locations:
  - id: loc_bookstore
    name: "晚风书店"
    int_ext: interior
    description: "老城区街角的小书店"

scenes:
  - id: scene_001
    slugline:
      int_ext: interior
      location_id: loc_bookstore
      time_of_day: day
      heading: "内景 晚风书店 - 日"
    summary: "周默误入书店，与苏晚初次相遇"
    source_refs:
      - chapter_id: chapter_01
        excerpt: "周默推开门，风铃叮当作响。柜台后坐着一个扎马尾的女孩，头也不抬地说：「随便看。」"
        paragraph_range: [2, 5]
    characters_present:
      - char_zhou_mo
      - char_su_wan
    elements:
      - type: action
        text: |
          风铃轻响。周默推门进入书店。
          苏晚坐在柜台后，目光落在书上，没有抬头。
      - type: dialogue
        character_id: char_su_wan
        lines: "随便看。"
      - type: action
        text: |
          周默点点头，走向科幻小说区。
          他在《神经漫游者》前停下，伸手——
          另一只手几乎同时伸来。
      - type: dialogue
        character_id: char_zhou_mo
        parenthetical: "惊讶"
        lines: "你也喜欢这本？"
      - type: dialogue
        character_id: char_su_wan
        lines: "它摆在我店里三个月了，还没人买。你是第一个伸手的人。"

warnings:
  - code: TIME_INFERRED
    scene_id: scene_001
    message: "原文未明确时间，默认设置为「日」"
    severity: warning
```

---

## 6. 校验规则

### 6.1 结构校验（必须通过）

1. `schema_version` 必须为 `"1.0"`
2. `meta.title`、`meta.author`、`meta.source`、`meta.adaptation` 必填
3. `meta.source.chapter_count` 必须 ≥ 3（赛题要求）
4. `meta.source.chapters` 长度必须等于 `chapter_count`
5. `scenes` 数组长度必须 ≥ 1
6. 每个 scene 必须包含 `id`、`slugline`、`slugline.heading`、`source_refs`（≥1 条）、`characters_present`、`elements`（≥1 个）
7. 每个 element 的 `type` 必须为合法枚举值

### 6.2 引用完整性校验

1. `characters_present` 中的每个 ID 必须存在于 `characters[].id`
2. `dialogue` 和 `voiceover` 的 `character_id`（若存在）必须存在于 `characters[].id`
3. `slugline.location_id`（若存在）必须存在于 `locations[].id`
4. `acts[].scenes` 中的每个 ID 必须存在于 `scenes[].id`
5. `source_refs[].chapter_id` 必须存在于 `meta.source.chapters[].id`

### 6.3 覆盖度校验

1. `meta.source.chapters` 中的每个章节 ID 必须至少出现在一个 scene 的 `source_refs` 中
2. 若某章节未被任何 scene 引用，产生 `severity: error` 的 warning

### 6.4 内容质量校验（建议）

1. `action.text` 单行不超过 4 行（超过则 warning：动作描述过长）
2. `dialogue.lines` 单次对白不超过 5 行（超过则 warning：台词过长，建议拆分）
3. 同一 scene 中 `voiceover` 元素不超过 2 个（超过则 warning：旁白过多）

### 6.5 校验结果分级

| 结果 | 条件 |
|------|------|
| **PASS** | 结构校验 + 引用校验全部通过，无 severity: error 的 warning |
| **PASS_WITH_WARNINGS** | 上述通过，但存在 warning 级别警告 |
| **FAIL** | 任一结构/引用校验失败，或存在 error 级别 warning |

---

## 7. 与 Fountain 格式映射

| YAML 字段 | Fountain 等价 |
|-----------|---------------|
| `slugline.heading` | Scene Heading（前缀 `.` 或 `INT./EXT.`） |
| `elements[type=action].text` | Action |
| `elements[type=dialogue].character_id` → name | Character（前缀 `@`） |
| `elements[type=dialogue].parenthetical` | Parenthetical（括号包裹） |
| `elements[type=dialogue].lines` | Dialogue |
| `elements[type=voiceover].text` | `(V.O.)` 后缀 |
| `elements[type=transition].text` | Transition（前缀 `>`） |

此映射关系为 V1.1 导出功能的实现基础。

---

## 8. 版本变更记录

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-06-05 | 初始版本 |
