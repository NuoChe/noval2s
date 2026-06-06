# Novel2Script 设计系统 — 纸墨 V2 Studio

> 版本：2.0  
> 最后更新：2026-06-06  
> 关联：[V2-TECH-SPEC.md](./V2-TECH-SPEC.md)、[frontend-design 设计原则](../.cursor/skills/frontend-design/SKILL.md)

---

## 1. 设计方向

**概念：** 纸墨 Editorial Studio — 文学编辑室的克制美学 + 现代 AI 工具的功能清晰度。

**差异化：** 避免 generic AI 产品的紫色渐变与 Inter 字体；以暖色纸纹、朱红点缀、宋体标题营造「剧本工坊」氛围，模型选择区则以 subtle 色带区分厂商而不破坏整体和谐。

**约束：** Jinja2 服务端渲染 + 原生 CSS/JS，无 React 构建链。

---

## 2. 设计令牌（CSS Variables）

在现有 [app.css](../src/novel2script/api/static/app.css) `:root` 基础上扩展：

### 2.1 色彩

| 令牌 | 值 | 用途 |
|------|-----|------|
| `--paper` | `#f7f3eb` | 页面背景 |
| `--paper-deep` | `#efe8dc` | 深纸色、禁用区 |
| `--ink` | `#1a1a1a` | 主文字 |
| `--ink-muted` | `#4a4a4a` | 次要文字 |
| `--ink-faint` | `#8a8278` | 占位符、hint |
| `--vermilion` | `#c23b3b` | 主 CTA、错误 |
| `--vermilion-hover` | `#a83232` | CTA hover |
| `--gold` | `#b8956a` | 装饰线、focus |
| `--gold-light` | `#e8dcc8` | 选中背景 |
| `--surface` | `#fffcf7` | 卡片、面板 |
| `--border` | `#d4c9b8` | 边框 |
| `--success` | `#2d6a4f` | 成功态 |

**模型 accent（仅用于卡片左边框 / 徽标）：**

| 模型 | 令牌 | 值 |
|------|------|-----|
| OpenAI | `--accent-openai` | `#6b7280` |
| 通义千问 | `--accent-qwen` | `#4a6fa5` |
| 智谱 | `--accent-zhipu` | `#3d6b59` |
| Kimi | `--accent-kimi` | `#7a8b99` |
| DeepSeek | `--accent-deepseek` | `#1e6b8c` |

### 2.2 字体

| 令牌 | 字体栈 | 用途 |
|------|--------|------|
| `--font-serif` | `"Noto Serif SC", "Songti SC", serif` | 标题、Hero |
| `--font-sans` | `"Noto Sans SC", "PingFang SC", sans-serif` | 正文、表单 |
| `--font-mono` | `"Cascadia Code", "Fira Code", "Consolas", monospace` | 模型 ID、YAML 输出 |

Google Fonts 加载：

```html
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;600&family=Noto+Serif+SC:wght@500;600&display=swap" rel="stylesheet">
```

### 2.3 间距与布局

| 令牌 | 值 |
|------|-----|
| `--space-xs` | `0.35rem` |
| `--space-sm` | `0.65rem` |
| `--space-md` | `1rem` |
| `--space-lg` | `1.5rem` |
| `--space-xl` | `2.5rem` |
| `--max-width` | `960px`（V2 由 720px 扩展） |
| `--radius` | `10px` |
| `--radius-sm` | `6px` |
| `--shadow` | `0 2px 12px rgba(26,26,26,0.06)` |
| `--shadow-lg` | `0 8px 32px rgba(26,26,26,0.08)` |

### 2.4 背景纹理

- 保留 24px 网格纸纹（现有 `body` background-image）
- Hero 区追加 grain overlay：

```css
.hero::before {
  content: "";
  position: absolute;
  inset: 0;
  opacity: 0.03;
  pointer-events: none;
  background-image: url("data:image/svg+xml,..."); /* feTurbulence noise */
}
```

---

## 3. 页面布局

```
┌──────────────────────────────────────────────────────────┐
│ TopBar                                                    │
├──────────────────────────────────────────────────────────┤
│ Hero（左金线 + 三步流程）                                  │
├──────────────────────────────────────────────────────────┤
│ Panel: 选择 AI 模型                                        │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐                  │
│ │GPT-4o Mini│ │通义千问Plus│ │智谱GLM-5.1│                  │
│ └──────────┘ └──────────┘ └──────────┘                  │
│ ┌──────────┐ ┌──────────┐                               │
│ │ Kimi 32K │ │DeepSeek Chat│                            │
│ └──────────┘ └──────────┘                               │
├──────────────────────────────────────────────────────────┤
│ Panel: 开始转换（未登录 disabled）                         │
├──────────────────────────────────────────────────────────┤
│ Panel: 转换结果（条件显示）                                │
├──────────────────────────────────────────────────────────┤
│ Footer                                                    │
└──────────────────────────────────────────────────────────┘

              ┌─────────────────────┐
              │ AuthModal (overlay)  │
              └─────────────────────┘
```

**响应式断点：**

| 断点 | 行为 |
|------|------|
| `≥ 768px` | 模型网格 3 列（上排 3 + 下排 2） |
| `≥ 640px` 且 `< 768px` | 模型网格 2 列 |
| `< 640px` | 模型网格 1 列；TopBar 折叠用户邮箱为图标 |

---

## 4. 组件规范

### 4.1 TopBar

**结构：**

```html
<header class="topbar">
  <a href="/" class="topbar__brand">Novel2Script</a>
  <div class="topbar__actions" id="auth-area">
    <!-- 未登录 -->
    <button class="btn btn-ghost btn-sm" data-auth-open="login">登录</button>
    <!-- 已登录 -->
    <span class="topbar__user">user@example.com</span>
    <button class="btn btn-ghost btn-sm" id="logout-btn">退出</button>
  </div>
</header>
```

**样式要点：**

- `position: sticky; top: 0; z-index: 100`
- 背景 `var(--surface)` + 底边 `1px solid var(--border)`
- 品牌字用 `--font-serif`

### 4.2 ModelCard

**结构：**

```html
<label class="model-card model-card--qwen" data-model-id="qwen-plus">
  <input type="radio" name="model_id" value="qwen-plus" class="model-card__input">
  <span class="model-card__accent"></span>
  <span class="model-card__name">通义千问 Plus</span>
  <span class="model-card__id">qwen-plus</span>
  <span class="model-card__desc">国内部署、中文理解</span>
</label>
```

**状态：**

| 状态 | 样式 |
|------|------|
| 默认 | `border: 1px solid var(--border)` |
| hover | `transform: translateY(-2px); box-shadow: var(--shadow-lg)` |
| selected | `border-color: var(--gold); background: var(--gold-light)` |
| unavailable | `opacity: 0.45; pointer-events: none; cursor: not-allowed` |
| disabled (未登录) | 同 unavailable，tooltip「请先登录」 |

**accent 条：** 卡片左侧 `4px` 宽色带，颜色取自 `--accent-*`。

### 4.3 AuthModal

**结构：**

```html
<div class="modal-overlay" id="auth-modal" hidden>
  <div class="modal" role="dialog" aria-labelledby="auth-title">
    <div class="modal__tabs">
      <button class="modal__tab modal__tab--active" data-tab="login">登录</button>
      <button class="modal__tab" data-tab="register">注册</button>
    </div>
    <form id="auth-form" class="modal__body">
      <div class="field">
        <label for="auth-email">邮箱</label>
        <input type="email" id="auth-email" required>
      </div>
      <div class="field">
        <label for="auth-password">密码</label>
        <input type="password" id="auth-password" required minlength="6">
      </div>
      <p class="modal__error" id="auth-error" hidden></p>
      <button type="submit" class="btn btn-primary btn-block">提交</button>
    </form>
    <button class="modal__close" aria-label="关闭">&times;</button>
  </div>
</div>
```

**动效：**

```css
.modal-overlay[hidden] { display: none; }
.modal-overlay { animation: fadeIn 0.2s ease; }
.modal { animation: slideUp 0.3s ease; }

@keyframes slideUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
```

### 4.4 ConvertPanel（禁用态）

未登录时父容器添加 `.panel--locked`：

```css
.panel--locked {
  opacity: 0.5;
  pointer-events: none;
  position: relative;
}
.panel--locked::after {
  content: "登录后即可开始转换";
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-serif);
  color: var(--ink-muted);
  pointer-events: none;
}
```

### 4.5 继承组件（V1）

以下组件保持 V1 样式，仅微调间距以适配 960px 宽度：

- `.hero` / `.hero__steps`
- `.panel` / `.field` / `.upload-zone`
- `.btn` / `.btn-primary` / `.btn-ghost`
- `.stats-bar` / `.yaml-panel`
- `.footer-meta`

---

## 5. 动效与微交互

| 场景 | 效果 | 实现 |
|------|------|------|
| 页面加载 | 区块依次淡入 | `.page > * { animation: fadeIn 0.6s ease-out; animation-fill-mode: both; }` + `animation-delay` 递增 |
| 模型卡片 hover | 微抬升 | `transition: transform 0.2s, box-shadow 0.2s` |
| Modal 打开 | 遮罩淡入 + 内容上滑 | 见 §4.3 |
| 转换中 | 按钮 pulse + 表单锁定 | `.btn-primary:disabled { opacity: 0.7; }` |
| 登录成功 | Modal 关闭 + 转换区解锁 | JS 移除 `.panel--locked` |

---

## 6. 无障碍

- Modal 打开时 `focus-trap` 于表单首字段
- `Esc` 关闭 Modal
- 模型卡片 radio 组支持键盘方向键切换
- 错误信息关联 `aria-live="polite"` 区域
- 色彩对比：正文 `#1a1a1a` on `#f7f3eb` ≥ WCAG AA

---

## 7. 文件清单

| 文件 | 变更 |
|------|------|
| `api/static/app.css` | 扩展令牌、TopBar、ModelCard、Modal、locked 态 |
| `api/templates/index.html` | 引入 partials、调整布局结构 |
| `api/templates/partials/topbar.html` | 新建 |
| `api/templates/partials/model-selector.html` | 新建 |
| `api/templates/partials/auth-modal.html` | 新建 |
| `api/static/auth.js` | 新建：会话、Modal、logout |
| `api/static/models.js` | 新建：拉取模型、渲染卡片、localStorage |

---

## 8. 禁止事项

- 不使用 Inter、Roboto、Space Grotesk 等 generic AI 字体
- 不使用紫色渐变 hero 背景
- 不在 UI 中展示 API Key 或完整 Session token
- 不使用 emoji 作为唯一图标语言（可保留 📄 上传区装饰）
