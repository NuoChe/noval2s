"""Prompt templates for LLM calls."""

SYSTEM_PROMPT = """你是一位资深影视编剧，擅长将小说改编为可拍摄的剧本。

改编规则：
1. 将小说叙述改写为可视化的动作（action），禁止大段心理描写
2. 保留原文中的直接引语作为对白（dialogue）
3. 无引语的对话需从上下文中合理外化，并在 warnings 中标记 DIALOGUE_SYNTHESIZED
4. 按「时间+地点」变化划分场次（scene）
5. 每场必须包含 slugline（内景/外景 + 地点 + 时间）
6. 内心独白优先转为动作或对白，仅在必要时使用画外音（voiceover）
7. 输出严格遵循指定的 JSON 格式，不要输出任何其他文字
"""

ENTITY_EXTRACTION_USER = """从以下小说章节中抽取：
1. 出现的角色（姓名、别名、简要描述）
2. 出现的地点（名称、内/外景 interior/exterior/mixed）

已知角色表：{existing_characters}
已知地点表：{existing_locations}

若角色/地点已在已知表中，请使用相同 id。

章节 ID：{chapter_id}
章节文本：
{chapter_text}

输出 JSON 格式：
{{
  "characters": [{{"id": "char_xxx", "name": "...", "aliases": [], "description": "..."}}],
  "locations": [{{"id": "loc_xxx", "name": "...", "int_ext": "interior", "description": "..."}}]
}}
"""

SCENE_ADAPTATION_USER = """将以下小说章节改编为剧本场次。

已知角色表：{characters}
已知地点表：{locations}
章节 ID：{chapter_id}

章节文本：
{chapter_text}

输出 JSON 格式：
{{
  "scenes": [
    {{
      "slugline": {{
        "int_ext": "interior",
        "location_id": "loc_xxx",
        "time_of_day": "day",
        "heading": "内景 地点名 - 日"
      }},
      "summary": "一句话概述",
      "source_refs": [
        {{"chapter_id": "{chapter_id}", "excerpt": "原文摘要200字内", "paragraph_range": [0, 2]}}
      ],
      "characters_present": ["char_xxx"],
      "elements": [
        {{"type": "action", "text": "动作描述"}},
        {{"type": "dialogue", "character_id": "char_xxx", "lines": "台词", "parenthetical": null}}
      ]
    }}
  ],
  "warnings": [
    {{"code": "TIME_INFERRED", "message": "...", "severity": "warning"}}
  ]
}}

element type 只能是：action, dialogue, voiceover, transition。
int_ext: interior | exterior | mixed
time_of_day: day | night | dawn | dusk | continuous | unspecified
severity: info | warning | error
"""
