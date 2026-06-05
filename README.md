# Novel2Script

AI 辅助小说转剧本工具：将 3 章以上的小说文本自动转换为结构化 YAML 剧本初稿。

## 功能

- 自动识别章节（中文 / 英文 / Markdown）
- LLM 抽取角色、地点，按章改编为场次
- 输出符合 [YAML Schema v1.0](docs/YAML-SCHEMA.md) 的剧本
- CLI 与 Web UI 双入口
- Schema 校验与转换报告

## 安装

```bash
cd d:\七牛云
pip install -e ".[dev]"
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY
```

## 配置

| 变量 | 说明 | 默认 |
|------|------|------|
| `LLM_PROVIDER` | 提供商 | `openai` |
| `LLM_MODEL` | 模型 | `gpt-4o-mini` |
| `LLM_API_KEY` | API 密钥 | — |
| `LLM_BASE_URL` | 自定义 API 地址 | — |
| `MAX_CHAPTERS` | 最大章节数 | 20 |
| `MAX_WORDS` | 最大字数 | 100000 |

### 通义千问

```env
LLM_PROVIDER=dashscope
LLM_MODEL=qwen-plus
LLM_API_KEY=your-dashscope-key
```

### DeepSeek（云端 API）

在 [DeepSeek 开放平台](https://platform.deepseek.com/) 创建 API Key，无需本地部署：

```env
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-v4-pro
LLM_API_KEY=your-deepseek-api-key
# 也可使用官方变量名：DEEPSEEK_API_KEY=your-deepseek-api-key
LLM_BASE_URL=https://api.deepseek.com
```

也支持 `deepseek-chat`、`deepseek-reasoner` 等模型名；项目会自动补全为 `deepseek/<model>` 供 LiteLLM 调用。

### Ollama 本地

```env
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:14b
LLM_BASE_URL=http://localhost:11434
```

## CLI 用法

```bash
# 转换小说
novel2script convert examples/sample-novel-chapters.txt -o screenplay.yaml

# 校验 YAML
novel2script validate examples/sample-screenplay.yaml

# 启动 Web UI
novel2script serve --port 8000
```

## Web UI

```bash
novel2script serve
# 浏览器打开 http://127.0.0.1:8000
```

上传 TXT/MD 文件，转换完成后可预览、下载 YAML。

## 开发

```bash
pytest                    # 运行测试（使用 Mock LLM，无需 API Key）
pytest -m integration     # 集成测试（需 LLM_API_KEY）
ruff check src tests      # 代码检查
```

## 项目结构

```
src/novel2script/
├── cli/          # Typer CLI
├── api/          # FastAPI Web UI
├── parser/       # 章节解析
├── llm/          # LiteLLM 客户端
├── extractor/    # 实体抽取
├── adapter/      # 场次改编
├── pipeline/     # 转换编排
├── emitter/      # YAML 输出
├── validator/    # Schema 校验
└── models/       # Pydantic 模型
```

## 文档

- [产品需求](docs/PRD.md)
- [YAML Schema 规范](docs/YAML-SCHEMA.md)
- [技术架构](docs/ARCHITECTURE.md)
- [用户指南](docs/USER-GUIDE.md)

## 许可证

MIT
