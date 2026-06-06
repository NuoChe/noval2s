# Changelog

本文件记录 Novel2Script 产品文档与应用的主要版本变更。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

---

## [2.0.0] - 2026-06-06

### 新增

- **五模型切换模块**：Web UI 与 CLI 支持在 OpenAI GPT-4o Mini、通义千问 Plus、智谱 GLM-5.1、Kimi 32K、DeepSeek Chat 间切换
- **ModelRegistry**：`llm/registry.py` 统一管理 model_id、LiteLLM 映射与各厂商 API Key
- **`GET /api/models`**：返回可用模型目录
- **用户认证 Demo**：注册、登录、退出；SQLite 存储；签名 Session Cookie
- **`/api/convert` 鉴权**：未登录返回 401
- **Web UI 改版（纸墨 V2 Studio）**：TopBar、模型卡片网格、登录/注册 Modal
- **设计系统文档**：[DESIGN-SYSTEM.md](./DESIGN-SYSTEM.md)
- **V2 技术方案**：[V2-TECH-SPEC.md](./V2-TECH-SPEC.md)

### 变更

- 环境变量：按提供商独立 Key（`DASHSCOPE_API_KEY`、`ZAI_API_KEY`、`MOONSHOT_API_KEY`、`DEEPSEEK_API_KEY`）
- 新增 `DEFAULT_MODEL_ID`、`AUTH_SECRET`、`AUTH_DEMO_USERS`
- CLI 新增 `--model-id`；Web convert 表单新增 `model_id`
- 请求级 `Settings` 副本，避免污染全局配置缓存
- 产品文档版本升至 2.0；[PROJECT-DOCUMENT.md](../PROJECT-DOCUMENT.md) 更新路线图

### 不变

- YAML 输出 Schema 仍为 **v1.0**
- Prompt 版本仍为 **v1.0**
- CLI 无需登录；Ollama 仍可通过 `--provider ollama` 使用

### 文档

- [ARCHITECTURE.md](./ARCHITECTURE.md) 更新至 v2.0
- [PRD.md](./PRD.md) 新增 US-08~10、F-06~08
- [USER-GUIDE.md](./USER-GUIDE.md) 新增 Web 登录与模型配置章节

### 安全说明

- API Key 必须通过 `.env` 配置，禁止硬编码
- Auth 模块标注为 Demo，非生产就绪

### 文档补丁（2026-06-06）

- 预置模型由四款扩展为五款，新增 **DeepSeek Chat**（`deepseek-chat` / `DEEPSEEK_API_KEY`）

---

## [1.0.0] - 2026-06-05

### 新增

- CLI 转换命令：小说 TXT/MD → YAML 剧本
- 章节解析、实体抽取、场次改编流水线
- LiteLLM 统一客户端（OpenAI / DashScope / DeepSeek / Ollama）
- YAML Schema v1.0 与 Pydantic 校验
- 转换报告（`*.report.json`）
- Web UI 基础版：上传、转换、预览、下载
- 完整项目文档（PRD、架构、Schema、用户指南、MVP 计划）

[2.0.0]: ./V2-TECH-SPEC.md
[1.0.0]: ./ARCHITECTURE.md
