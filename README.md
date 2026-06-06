# Novel2Script

AI 辅助小说转剧本工具：将 3 章以上的小说文本自动转换为结构化 YAML 剧本初稿。

**当前版本：** 文档 v2.0 · 应用包建议 0.2.0

## 功能

- 自动识别章节（中文 / 英文 / Markdown）
- LLM 抽取角色、地点，按章改编为场次
- 输出符合 [YAML Schema v1.0](docs/YAML-SCHEMA.md) 的剧本
- CLI 与 Web UI 双入口
- **V2：** Web 五模型切换（OpenAI / 千问 / 智谱 / Kimi / DeepSeek）
- **V2：** 登录注册 Demo（登录后可用 Web 转换）
- Schema 校验与转换报告

## 安装

```bash
cd d:\七牛云
pip install -e ".[dev]"
cp .env.example .env
# 编辑 .env：至少配置一个模型 Key + AUTH_SECRET
```

## 配置（V2 五模型）

| 变量 | 说明 |
|------|------|
| `DEFAULT_MODEL_ID` | 默认模型 ID |
| `OPENAI_API_KEY` | OpenAI（或 `LLM_API_KEY`） |
| `DASHSCOPE_API_KEY` | 通义千问 |
| `ZAI_API_KEY` | 智谱 GLM |
| `MOONSHOT_API_KEY` | Kimi |
| `DEEPSEEK_API_KEY` | DeepSeek |
| `AUTH_SECRET` | Web Session 签名密钥 |
| `AUTH_DEMO_USERS` | 可选预置账号 `email:password` |

| model_id | 模型 |
|----------|------|
| `openai-gpt-4o-mini` | GPT-4o Mini |
| `qwen-plus` | 通义千问 Plus |
| `zhipu-glm-5.1` | 智谱 GLM-5.1 |
| `kimi-moonshot-32k` | Kimi 32K |
| `deepseek-chat` | DeepSeek Chat |

完整配置见 [V2 技术方案](docs/V2-TECH-SPEC.md) 与 [用户指南 §4](docs/USER-GUIDE.md#4-web-ui-与模型配置)。

### Ollama 本地

```env
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:14b
LLM_BASE_URL=http://localhost:11434
```

## CLI 用法

```bash
# 转换小说（V2 推荐）
novel2script convert examples/sample-novel-chapters.txt -o screenplay.yaml --model-id deepseek-chat

# 校验 YAML
novel2script validate examples/sample-screenplay.yaml

# 启动 Web UI
novel2script serve --port 8000
```

## Web UI（V2）

```bash
novel2script serve
# 浏览器打开 http://127.0.0.1:8000
```

1. 注册或登录（Demo 账号见 `.env` 中 `AUTH_DEMO_USERS`）
2. 选择 AI 模型
3. 上传 TXT/MD，转换后预览、下载 YAML

UI 设计规范见 [DESIGN-SYSTEM.md](docs/DESIGN-SYSTEM.md)。

## 开发

```bash
pytest                    # Mock LLM，无需 API Key
pytest -m integration     # 集成测试（需 LLM Key）
ruff check src tests
```

## 项目结构

```
src/novel2script/
├── cli/          # Typer CLI
├── api/          # FastAPI Web UI
├── auth/         # V2：登录注册 Demo（待实现）
├── llm/          # LiteLLM + registry（待实现）
├── parser/       # 章节解析
├── extractor/    # 实体抽取
├── adapter/      # 场次改编
├── pipeline/     # 转换编排
├── emitter/      # YAML 输出
├── validator/    # Schema 校验
└── models/       # Pydantic 模型
```

## 文档

- [V2 技术方案](docs/V2-TECH-SPEC.md)
- [产品需求](docs/PRD.md)
- [YAML Schema 规范](docs/YAML-SCHEMA.md)
- [技术架构](docs/ARCHITECTURE.md)
- [设计系统](docs/DESIGN-SYSTEM.md)
- [用户指南](docs/USER-GUIDE.md)
- [变更记录](docs/CHANGELOG.md)
- [完整项目文档](PROJECT-DOCUMENT.md)

## 许可证

MIT
