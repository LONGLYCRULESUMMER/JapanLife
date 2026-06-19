# JapanLife 前端设计文档 — 产品级 Next.js 前端

- **日期**: 2026-06-19
- **状态**: 待用户评审
- **作者**: @coda1997 + Copilot
- **定位**: 简历级 Agent 项目的「可用产品级前端」（面向在日外国人真实使用 + GitHub/面试展示）

---

## 1. 背景与目标

现有 `JapanLife` 已具备扎实的后端：FastAPI + LangGraph 多智能体（supervisor + tax/visa/ward_office 专家 + handoff）+ 混合检索 RAG（ElasticSearch BM25 + Qdrant 向量 + RRF + 重排），并提供 `/chat`、`/chat/stream`（SSE）、`/search`、`/conversations`、`/health` 等接口。

当前前端是单文件 `streamlit_app.py`（约 320 行），以「架构图 + 技术栈表 + 聊天 + 检索探查」三个 tab 形式存在，本质是**面向开发者/作品集的演示 UI**，而非面向终端用户的产品。

**本次目标**：为该项目交付一个**产品级前端**，让「在日外国人」可以真正用它来查询税务 / 在留 / 区役所事务。前端以「助手对话」为核心，移动端优先，三语界面，视觉专业可信。

### 成功标准

1. 终端用户在手机或桌面上都能流畅完成「提问 → 流式作答 → 查看引用来源」的核心闭环。
2. 界面支持 **English / 日本語 / 中文** 三语切换。
3. 视觉达到现代 SaaS 产品水准（Calm Trust 设计方向，含暗色模式），可作为简历中的前端能力证明。
4. **不改动后端业务逻辑**：前端通过同源代理消费现有 FastAPI 接口。
5. `docker-compose up` 可同时拉起 es + qdrant + api + **web**，一键演示。

### 非目标（Out of Scope）

- 用户账号 / 登录 / 鉴权（对话以本地 `threadId` 匿名保存）。
- 后端业务逻辑改动、支付、推送通知。
- 继续扩展 Streamlit（仅作为开发/演示工具保留，并修复其现有 bug）。

---

## 2. 关键决策汇总

| 维度 | 决策 |
| --- | --- |
| 主要目标 | 面向终端用户的**可用产品**（兼顾简历展示） |
| 框架 | **Next.js 15（App Router）+ TypeScript** |
| 样式 | **Tailwind CSS + shadcn/ui** |
| 国际化 | **next-intl**，三语 `en / ja / zh` |
| 服务端状态 | **TanStack Query**（`/conversations`、`/health`、`/search`） |
| 流式对话 | 自研 `useChat` hook + `lib/sse.ts` 解析 SSE |
| Markdown | `react-markdown` + `remark-gfm` |
| 设计方向 | **Calm Trust**：靛蓝(indigo) 主色 + 冷中性灰，现代专业、可信 |
| 主题 | 亮 / 暗双主题，跟随系统，持久化 |
| PWA | manifest + 图标 + service worker，可安装、离线外壳 |
| 后端 | **零业务改动**；前端经 Next.js 代理同源访问 FastAPI |

---

## 3. 架构与项目结构

### 3.1 Monorepo 布局（新增 `web/`）

```
JapanLife/
├── app/                 FastAPI 后端（不改业务逻辑）
├── agents/ rag/ core/   LangGraph + 混合检索
├── streamlit_app.py     保留为开发/演示工具（修复 bug）
├── web/                 ← 新增 Next.js 前端
│   ├── app/[locale]/    App Router + i18n 路由
│   │   ├── page.tsx               Home / 落地页
│   │   ├── chat/page.tsx          助手对话
│   │   ├── how-it-works/page.tsx  原理/架构展示
│   │   └── dev/retrieval/page.tsx 检索探查器
│   ├── app/api/[...path]/route.ts 代理到 FastAPI（含 SSE 透传）
│   ├── components/      UI 组件（chat / cards / nav…）
│   ├── lib/             api client + sse parser + utils
│   ├── messages/        en.json · ja.json · zh.json
│   ├── public/          PWA manifest + icons
│   ├── middleware.ts    locale 检测/重定向
│   ├── tailwind.config.ts / next.config.ts / tsconfig.json
│   └── package.json
├── docker-compose.yml   + "web" 服务
└── Makefile             + web / web-build 目标
```

### 3.2 请求 / 数据流

```
浏览器 (Next.js, EN/JA/ZH, 移动优先)
   │  同源 /api/*
   ▼
Next.js 代理 (app/api/[...path]/route.ts 或 rewrites)
   │  转发到 BACKEND_URL
   ▼
FastAPI :8000  →  /chat/stream(SSE) · /search · /conversations · /health
   ▼
LangGraph supervisor + 专家子图  ·  ElasticSearch + Qdrant
```

### 3.3 关键设计

- **零后端业务改动 / 免 CORS**：浏览器只访问同源 `/api/*`；由 Next.js 的 Route Handler（或 `rewrites`）代理到 FastAPI，并**逐字节透传 SSE 流**。这样既不动 API 契约，也不需要在 FastAPI 上加 CORS 中间件。
  - SSE 透传以 Route Handler 实现（`fetch(backend, {duplex})` → 直接返回上游 `Response.body` 流），对流式控制最稳妥；`rewrites` 作为备选。
- **前端独立服务**：在 `docker-compose` 中新增 `web` 服务（Node 运行时），与 es / qdrant / api 并列；新增 `make web`（本地 dev）与 `make web-build`。
- **配置**：单一环境变量 `BACKEND_URL`（compose 内默认 `http://api:8000`，本地默认 `http://localhost:8000`）。
- **Streamlit 保留**：作为快速开发/演示工具保留，但**修复其 `import json` 缺失 bug**（当前 `streamlit_app.py:52` 使用 `json.loads` 但未 import，导致流式聊天必崩）。

---

## 4. 页面、路由与国际化

### 4.1 路由树（next-intl，`[locale] = en | ja | zh`）

| 路由 | 页面 | 说明 |
| --- | --- | --- |
| `/[locale]` | 🏠 Home / 落地页 | Hero 价值主张 + 醒目提问框 + 分类快捷入口（税务/在留/区役所）+ 示例问题 + 信任条 |
| `/[locale]/chat` | 💬 助手对话 | 流式作答、路由徽标、引用来源、建议追问、历史抽屉 |
| `/[locale]/how-it-works` | 📐 原理 | 混合检索 + 多智能体讲解、架构图、评测数据（信任 + 简历价值） |
| `/[locale]/dev/retrieval` | 🔎 检索探查器 | BM25 ∥ 向量 → RRF → 重排（开发者工具，置于次级入口） |

- `middleware.ts`：locale 检测与重定向；默认 locale `en`，locale 写入 URL（利于分享与 SEO）。
- 每路由含 `not-found` 与 `error` 边界。

### 4.2 导航

- **桌面**：顶部栏（Logo · Home · Assistant · How it works · 语言切换 · 主题切换）。
- **移动**：精简顶栏 + 汉堡菜单；语言与主题切换始终可达。
- How-it-works 与 `/dev/retrieval` 放在菜单/页脚，不占据主流程。

### 4.3 国际化模型

- **UI 文案**：`messages/{en,ja,zh}.json`，经 next-intl 注入。
- **助手回答**：由后端按用户语言返回（LLM）；前端将当前 locale 作为提示传入。由于知识库为 EN/JA 双语，引用来源可能为 EN/JA。
- **流转**：Home 提问框输入 → 跳转 `/[locale]/chat` 并自动发送该问题；分类快捷入口深链一个起始 prompt。

---

## 5. 对话集成与核心组件

### 5.1 SSE 流式集成

- `useChat` hook：`POST /api/chat/stream` → 读取 `ReadableStream` → 由 `lib/sse.ts` 解析。
- 事件处理：`route`（路由到哪个专家）· `tool`（工具调用）· `token`（增量文本）· `error` · `done`（含 `thread_id` 与 `citations`）。
- **工具语义对齐**：收到 `tool` 事件时，重置当前正在累积的「前导文本」（与后端 `routes.py` 中 preamble 重置语义一致）。
- `threadId` 持久化到 `localStorage`，使「历史/续聊」无需登录即可工作。
- 暴露：`messages`、`isStreaming`、`currentRoute`、`currentTools`、`citations`、`error`、`stop()`。

### 5.2 服务端状态

- **TanStack Query** 管理 `/conversations`（列表/续聊/删除）、`/health`（后端健康）、`/search`（检索探查）的缓存与重新校验。
- 助手回答用 **react-markdown + remark-gfm** 安全渲染。

### 5.3 组件清单

`ChatWindow` · `MessageBubble` · `RoutingBadge` · `ToolStep` · `Citations` · `ChatInput`（含 Stop）· `SuggestedQuestions` · `CategoryChips` · `HistoryDrawer` · `Disclaimer` · `HealthIndicator` · `LanguageSwitcher` · `ThemeToggle` · `Navbar` / `Footer` · `RetrievalInspector`。

### 5.4 行为细节

- **路由徽标**：显示由哪个专家作答（税务 🧾 / 在留 🛂 / 区役所 🏛️）及所用工具，把多智能体系统呈现给用户。
- **引用来源**：存在即展示，可折叠，映射到知识库文档标题。
- **信任 / 安全**：本领域敏感，常驻「仅供参考，非法律/税务意见，请以官方为准」免责声明。
- **状态**：空态（示例问题）、流式态（光标 + Stop）、错误态（「助手暂不可用」）、离线态（health 红点）。

---

## 6. 设计系统与打磨（Calm Trust）

### 6.1 设计令牌（Design Tokens）

- **主色**：indigo `#4F46E5`（hover `#4338CA`，primary-50 `#EEF2FF`）。
- **中性**：slate（页面 `#F8FAFC`、表面 `#FFFFFF`、正文 `#0F172A`、次要 `#64748B`）。
- **语义色**：success `#10B981` / warn `#F59E0B` / error `#EF4444`。
- **暗色**：页面 `#020617`、表面 `#0F172A`、主色 `#818CF8`、边框 `#1E293B`。
- **字体**：Inter + Noto Sans JP + Noto Sans SC（单一字体栈覆盖三语）。
- **形状/间距**：rounded-xl 卡片、柔和阴影、8px 间距刻度、慷慨留白。

### 6.2 组件 kit

- **shadcn/ui**（按 indigo 主题定制）：Button / Input / Textarea / Card / Sheet(Drawer) / DropdownMenu(语言) / Tooltip / Skeleton / Badge / Tabs / Collapsible。

### 6.3 打磨清单

- **暗色模式**：Tailwind class 策略，持久化，跟随系统。
- **PWA**：manifest + 图标 + service worker，可安装、离线外壳。
- **响应式**：移动优先，安全区域适配。
- **动效**：克制的过渡与消息淡入，尊重 `prefers-reduced-motion`。
- **可访问性（A11y）**：AA 对比度、焦点环、键盘导航、流式回答 `aria-live`。
- **SEO**：每 locale 的 metadata + Open Graph。

---

## 7. 测试与工具链

- **代码质量**：ESLint + Prettier + TypeScript strict。
- **组件测试**：Vitest + React Testing Library（`useChat`/SSE 解析、MessageBubble、Citations、路由徽标等）。
- **冒烟 E2E（可选）**：Playwright（首页加载、发起一次对话、语言切换）。
- **SSE 解析单测**：对 `lib/sse.ts` 用固定事件流断言增量状态机（含 tool 重置语义）。
- **CI**：在现有 GitHub Actions 中新增 `web` 的 lint + typecheck + 单测 job。

---

## 8. 部署

- `docker-compose.yml` 新增 `web` 服务：基于 Node 镜像，多阶段构建 `next build` → `next start`，依赖 `api`，注入 `BACKEND_URL=http://api:8000`，对外暴露端口（如 `3000`）。
- `Makefile` 新增：`web`（`cd web && npm run dev`）、`web-build`（`npm run build`）。
- README 增补：本地起前端、三语演示、移动端截图位。

---

## 9. 风险与权衡

- **新增 Node/TS 技术栈**：与 Python 共存，带来一定维护面；通过把 web 限定为「消费现有 API 的瘦前端」控制复杂度。
- **SSE 经代理透传**：需确保不被缓冲（Route Handler 直接返回上游流、关闭 buffering）；以 `lib/sse.ts` 单测与本地真实联调验证。
- **三语文案维护**：UI 文案集中在 `messages/*.json`，初期英文为基准，日/中翻译随之；助手回答语言由后端负责。
- **Streamlit 与 web 并存**：明确 web 为产品、Streamlit 为开发工具，不做双向特性同步，避免重复维护。

---

## 10. 交付里程碑（供实现计划参考）

1. `web/` 脚手架：Next.js 15 + TS + Tailwind + shadcn/ui + next-intl + 代理 Route Handler + `/health` 打通。
2. 设计系统落地：tokens、暗色模式、字体、基础组件。
3. 助手对话：`useChat` + `lib/sse.ts` + ChatWindow/MessageBubble/Citations/RoutingBadge + 信任声明与各状态。
4. Home 落地页 + 分类快捷入口 + 示例问题 + 提问跳转。
5. 历史抽屉（list/resume/delete，TanStack Query）。
6. How-it-works + `/dev/retrieval` 检索探查器。
7. PWA + A11y + SEO + 响应式打磨。
8. 测试（Vitest/RTL，SSE 单测，可选 Playwright）+ CI job。
9. docker-compose `web` 服务 + Makefile + README + 修复 Streamlit `import json` bug。

---

*本设计文档经四个小节逐段评审通过后成稿，等待用户最终评审，随后进入实现计划（writing-plans）。*
