# JapanLife Product Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. **Logic units (SSE parser, chat state machine) are unit-TDD.** UI/scaffolding tasks are verified by **building/booting** (`npm run build`, `npm run dev`, hitting the page) and by the dedicated test milestone (Task 14); they are not each unit-tested at creation time.

**Goal:** Build a usable, product-grade Next.js frontend (`web/`) for JapanLife — an assistant for foreigners in Japan — consuming the existing FastAPI backend through a same-origin proxy, with EN/JA/ZH i18n, streaming chat, dark mode, and PWA polish.

**Architecture:** A Next.js 15 (App Router) app in `web/` runs as its own service. The browser only calls same-origin `/api/*`; a catch-all Route Handler proxies to FastAPI (`BACKEND_URL`) and passes the SSE stream through byte-for-byte, so the backend's logic and API contract are untouched (no CORS needed). Chat streaming is parsed by a pure `lib/sse.ts` generator and reduced by a pure `lib/chat-machine.ts` state function (both unit-tested); a `useChat` hook wires them to React. Server state (`/conversations`, `/health`, `/search`) uses TanStack Query.

**Tech Stack:** Next.js 15, TypeScript (strict), Tailwind CSS, shadcn/ui, next-intl, next-themes, TanStack Query, react-markdown, Vitest + React Testing Library, @ducanh2912/next-pwa, Docker.

Reference spec: `docs/superpowers/specs/2026-06-19-japanlife-frontend-product-design.md`.

**Backend contract (do not change):**
- `POST /chat/stream` → SSE events: `route {route}`, `tool {name}`, `token {text}`, `error {error}`, `done {thread_id, citations[]}`.
- `GET /conversations?limit=` → `{conversations: [{thread_id, title, turns}]}`.
- `GET /conversations/{thread_id}` → `{thread_id, messages: [{role, content, citations[]}]}`.
- `DELETE /conversations/{thread_id}` → `{deleted}`.
- `GET /search?q=&domain=&top_k=` → `{query, domain, results: [{rank, citation, score, domain, snippet}]}`.
- `GET /health` → `{status, elasticsearch, qdrant}`.

---

## File Structure

| File | Responsibility |
|---|---|
| `web/package.json`, `web/tsconfig.json`, `web/next.config.ts` | project config + next-intl plugin |
| `web/tailwind.config.ts`, `web/postcss.config.mjs`, `web/app/globals.css` | Calm Trust tokens, light/dark CSS vars |
| `web/i18n/routing.ts`, `web/i18n/request.ts`, `web/middleware.ts` | locale routing (en/ja/zh) |
| `web/messages/{en,ja,zh}.json` | UI string catalog |
| `web/app/[locale]/layout.tsx` | root layout: fonts, providers, navbar/footer |
| `web/app/[locale]/page.tsx` | Home / landing |
| `web/app/[locale]/chat/page.tsx` | Assistant page |
| `web/app/[locale]/how-it-works/page.tsx` | architecture/RAG explainer |
| `web/app/[locale]/dev/retrieval/page.tsx` | retrieval inspector |
| `web/app/api/[...path]/route.ts` | same-origin proxy to FastAPI (SSE passthrough) |
| `web/lib/types.ts` | shared API types |
| `web/lib/sse.ts` (+ test) | SSE stream parser (pure) |
| `web/lib/chat-machine.ts` (+ test) | chat state reducer (pure) |
| `web/lib/api.ts` | typed fetchers for TanStack Query |
| `web/hooks/use-chat.ts` | streaming chat hook |
| `web/hooks/use-conversations.ts` | history queries/mutations |
| `web/components/providers.tsx` | Theme + Query providers (client) |
| `web/components/chat/*` | ChatWindow, MessageBubble, RoutingBadge, ToolStep, Citations, ChatInput, Disclaimer, SuggestedQuestions |
| `web/components/layout/*` | Navbar, Footer, LanguageSwitcher, ThemeToggle, HealthIndicator |
| `web/components/home/*` | Hero, CategoryChips |
| `web/components/history/HistoryDrawer.tsx` | list/resume/delete |
| `web/components/dev/RetrievalInspector.tsx` | search UI |
| `web/components/ui/*` | shadcn/ui primitives (generated) |
| `web/public/manifest.webmanifest`, `web/public/icons/*` | PWA |
| `web/vitest.config.ts`, `web/vitest.setup.ts` | test config |
| `docker-compose.yml`, `Makefile`, `.github/workflows/ci.yml` | add `web` service / targets / CI job |
| `streamlit_app.py` | fix missing `import json` |

---

## Task 1: Scaffold `web/` (Next.js + TS + Tailwind)

**Files:** Create `web/` via CLI, then trim boilerplate.

- [ ] **Step 1: Create the app**

Run from repo root:
```bash
npx create-next-app@latest web \
  --typescript --tailwind --eslint --app --src-dir=false \
  --import-alias "@/*" --use-npm --no-turbopack
```
Expected: `web/` created with `app/`, `package.json`, `tailwind.config.ts`, `tsconfig.json`.

- [ ] **Step 2: Install runtime + dev deps**

```bash
cd web
npm install next-intl next-themes @tanstack/react-query react-markdown remark-gfm lucide-react clsx tailwind-merge class-variance-authority @ducanh2912/next-pwa
npm install -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
```
Expected: deps added to `web/package.json`.

- [ ] **Step 3: Enable TypeScript strict mode**

Edit `web/tsconfig.json` — ensure `"strict": true` under `compilerOptions` (create-next-app sets it; confirm).

- [ ] **Step 4: Remove starter cruft**

```bash
rm -f web/app/page.tsx web/app/favicon.ico
```
(We rebuild routes under `app/[locale]/`. Keep `web/app/globals.css` — we overwrite it in Task 4.)

- [ ] **Step 5: Verify it builds**

Run: `cd web && npm run build`
Expected: build succeeds (no pages yet is fine; if it errors on missing root page, that's resolved in Task 3).

- [ ] **Step 6: Commit**

```bash
git add web/package.json web/package-lock.json web/tsconfig.json web/next.config.* web/tailwind.config.ts web/postcss.config.* web/.eslintrc* web/eslint.config.* web/.gitignore web/next-env.d.ts
git commit -m "feat(web): scaffold Next.js + TS + Tailwind app"
```

---

## Task 2: Same-origin proxy Route Handler (SSE passthrough)

**Files:**
- Create: `web/app/api/[...path]/route.ts`
- Create: `web/.env.local` (gitignored), document `BACKEND_URL`

- [ ] **Step 1: Write the proxy handler**

Create `web/app/api/[...path]/route.ts`:
```ts
import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

async function proxy(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  const search = req.nextUrl.search;
  const target = `${BACKEND_URL}/${path.join("/")}${search}`;

  const init: RequestInit & { duplex?: "half" } = {
    method: req.method,
    headers: { "content-type": req.headers.get("content-type") ?? "application/json" },
    cache: "no-store",
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.text();
    init.duplex = "half";
  }

  const upstream = await fetch(target, init);

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") ?? "application/json",
      "cache-control": "no-cache, no-transform",
    },
  });
}

export { proxy as GET, proxy as POST, proxy as DELETE };
```

- [ ] **Step 2: Add local env**

Create `web/.env.local`:
```
BACKEND_URL=http://localhost:8000
```
(`.env.local` is already in Next's default `.gitignore`.)

- [ ] **Step 3: Boot-verify against a running backend**

In one terminal: `make serve` (or `make up`). In another:
```bash
cd web && npm run dev
# then:
curl -s http://localhost:3000/api/health
```
Expected: JSON like `{"status": ...,"elasticsearch":...,"qdrant":...}` proxied from FastAPI.

- [ ] **Step 4: Commit**

```bash
git add web/app/api
git commit -m "feat(web): same-origin proxy route handler with SSE passthrough"
```

---

## Task 3: i18n routing (en/ja/zh) + locale layout

**Files:**
- Create: `web/i18n/routing.ts`, `web/i18n/request.ts`, `web/middleware.ts`
- Create: `web/messages/en.json`, `web/messages/ja.json`, `web/messages/zh.json`
- Modify: `web/next.config.ts`
- Create: `web/app/[locale]/layout.tsx`, `web/app/[locale]/page.tsx` (temporary stub, replaced in Task 8)

- [ ] **Step 1: Routing config**

Create `web/i18n/routing.ts`:
```ts
import { defineRouting } from "next-intl/routing";
import { createNavigation } from "next-intl/navigation";

export const routing = defineRouting({
  locales: ["en", "ja", "zh"],
  defaultLocale: "en",
});

export const { Link, redirect, usePathname, useRouter, getPathname } =
  createNavigation(routing);
```

- [ ] **Step 2: Request config**

Create `web/i18n/request.ts`:
```ts
import { getRequestConfig } from "next-intl/server";
import { routing } from "./routing";

export default getRequestConfig(async ({ requestLocale }) => {
  let locale = await requestLocale;
  if (!locale || !routing.locales.includes(locale as "en" | "ja" | "zh")) {
    locale = routing.defaultLocale;
  }
  return { locale, messages: (await import(`../messages/${locale}.json`)).default };
});
```

- [ ] **Step 3: Middleware**

Create `web/middleware.ts`:
```ts
import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  // Skip Next internals, the API proxy, and static files
  matcher: ["/((?!api|_next|.*\\..*).*)"],
};
```

- [ ] **Step 4: Wire the plugin**

Replace `web/next.config.ts` with:
```ts
import createNextIntlPlugin from "next-intl/plugin";
import type { NextConfig } from "next";

const withNextIntl = createNextIntlPlugin();

const nextConfig: NextConfig = {};

export default withNextIntl(nextConfig);
```

- [ ] **Step 5: Message catalog (EN)**

Create `web/messages/en.json`:
```json
{
  "app": { "name": "JapanLife", "tagline": "Navigate life in Japan, calmly." },
  "nav": { "home": "Home", "assistant": "Assistant", "howItWorks": "How it works", "language": "Language", "theme": "Theme" },
  "home": {
    "heroSubtitle": "Tax, visa & ward-office answers — cited, in your language.",
    "askPlaceholder": "Ask anything…",
    "ask": "Ask",
    "examplesTitle": "Try asking",
    "trust": "Informational only — not legal or tax advice."
  },
  "categories": { "tax": "Tax", "visa": "Visa", "wardOffice": "Ward office" },
  "chat": {
    "title": "Assistant",
    "placeholder": "Ask about tax, visa, or ward-office procedures…",
    "stop": "Stop",
    "send": "Send",
    "routedTo": "routed to {route}",
    "sources": "Sources ({count})",
    "empty": "Ask a question to get started.",
    "error": "The assistant is temporarily unavailable. Please try again.",
    "disclaimer": "Informational only — not legal or tax advice. Verify with official sources."
  },
  "history": { "title": "History", "new": "New chat", "empty": "No past conversations yet.", "delete": "Delete", "turns": "{count} turn(s)" },
  "health": { "ok": "Backend online", "degraded": "Backend degraded", "down": "Backend unreachable" },
  "dev": { "retrievalTitle": "Retrieval inspector", "query": "Query", "domain": "Domain", "topK": "Top K", "search": "Search", "all": "(all)", "noResults": "No results." },
  "examples": {
    "q1": "When is the income tax filing deadline?",
    "q2": "How many years for permanent residency?",
    "q3": "転入届はいつまでに出す必要がありますか？"
  }
}
```

- [ ] **Step 6: Message catalog (JA)**

Create `web/messages/ja.json`:
```json
{
  "app": { "name": "JapanLife", "tagline": "日本での暮らしを、落ち着いて。" },
  "nav": { "home": "ホーム", "assistant": "アシスタント", "howItWorks": "仕組み", "language": "言語", "theme": "テーマ" },
  "home": {
    "heroSubtitle": "税金・在留・区役所の手続きに、出典つきであなたの言語で回答。",
    "askPlaceholder": "質問を入力…",
    "ask": "質問する",
    "examplesTitle": "質問例",
    "trust": "情報提供のみ — 法律・税務上の助言ではありません。"
  },
  "categories": { "tax": "税金", "visa": "在留", "wardOffice": "区役所" },
  "chat": {
    "title": "アシスタント",
    "placeholder": "税金・在留・区役所の手続きについて質問…",
    "stop": "停止",
    "send": "送信",
    "routedTo": "{route} が担当",
    "sources": "出典 ({count})",
    "empty": "質問を入力して始めましょう。",
    "error": "アシスタントは現在利用できません。もう一度お試しください。",
    "disclaimer": "情報提供のみ — 法律・税務上の助言ではありません。公式情報をご確認ください。"
  },
  "history": { "title": "履歴", "new": "新しいチャット", "empty": "まだ会話がありません。", "delete": "削除", "turns": "{count} 往復" },
  "health": { "ok": "バックエンド稼働中", "degraded": "バックエンド低下", "down": "バックエンド接続不可" },
  "dev": { "retrievalTitle": "検索インスペクター", "query": "クエリ", "domain": "分野", "topK": "上位 K", "search": "検索", "all": "（すべて）", "noResults": "結果がありません。" },
  "examples": {
    "q1": "所得税の確定申告の期限はいつですか？",
    "q2": "永住権の取得には何年必要ですか？",
    "q3": "転入届はいつまでに出す必要がありますか？"
  }
}
```

- [ ] **Step 7: Message catalog (ZH)**

Create `web/messages/zh.json`:
```json
{
  "app": { "name": "JapanLife", "tagline": "从容地在日本生活。" },
  "nav": { "home": "首页", "assistant": "助手", "howItWorks": "原理", "language": "语言", "theme": "主题" },
  "home": {
    "heroSubtitle": "税务、在留与区役所事务 —— 附引用，用你的语言回答。",
    "askPlaceholder": "输入你的问题…",
    "ask": "提问",
    "examplesTitle": "试着问",
    "trust": "仅供参考 —— 非法律或税务意见。"
  },
  "categories": { "tax": "税务", "visa": "在留", "wardOffice": "区役所" },
  "chat": {
    "title": "助手",
    "placeholder": "询问税务、在留或区役所手续…",
    "stop": "停止",
    "send": "发送",
    "routedTo": "已转交 {route}",
    "sources": "来源 ({count})",
    "empty": "输入问题即可开始。",
    "error": "助手暂时不可用，请稍后再试。",
    "disclaimer": "仅供参考 —— 非法律或税务意见，请以官方信息为准。"
  },
  "history": { "title": "历史", "new": "新对话", "empty": "还没有历史对话。", "delete": "删除", "turns": "{count} 轮" },
  "health": { "ok": "后端在线", "degraded": "后端降级", "down": "后端不可达" },
  "dev": { "retrievalTitle": "检索探查器", "query": "查询", "domain": "领域", "topK": "Top K", "search": "搜索", "all": "（全部）", "noResults": "暂无结果。" },
  "examples": {
    "q1": "所得税申报的截止日期是什么时候？",
    "q2": "申请永住需要几年？",
    "q3": "转入申报需要在什么时候之前提交？"
  }
}
```

- [ ] **Step 8: Temporary locale layout + home stub**

Create `web/app/[locale]/layout.tsx`:
```tsx
import { NextIntlClientProvider, hasLocale } from "next-intl";
import { setRequestLocale } from "next-intl/server";
import { notFound } from "next/navigation";
import { routing } from "@/i18n/routing";
import "../globals.css";

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);
  return (
    <html lang={locale} suppressHydrationWarning>
      <body>
        <NextIntlClientProvider>{children}</NextIntlClientProvider>
      </body>
    </html>
  );
}
```

Create `web/app/[locale]/page.tsx` (stub, replaced in Task 8):
```tsx
import { useTranslations } from "next-intl";

export default function HomePage() {
  const t = useTranslations("app");
  return <main className="p-8"><h1>{t("name")}</h1><p>{t("tagline")}</p></main>;
}
```

- [ ] **Step 9: Boot-verify locales**

Run: `cd web && npm run dev`, then visit `/en`, `/ja`, `/zh` and `/` (should redirect to `/en`).
Expected: tagline renders in each language; `/` redirects to default locale.

- [ ] **Step 10: Commit**

```bash
git add web/i18n web/middleware.ts web/next.config.ts web/messages web/app/[locale]
git commit -m "feat(web): i18n routing (en/ja/zh) + locale layout"
```

## Task 4: Design system — Calm Trust tokens, fonts, providers, shadcn

**Files:**
- Modify: `web/app/globals.css`, `web/tailwind.config.ts`
- Create: `web/lib/utils.ts`, `web/components/providers.tsx`
- Modify: `web/app/[locale]/layout.tsx` (fonts + providers + nav/footer added in Task 9)
- Init: shadcn/ui

- [ ] **Step 1: Tokens in globals.css**

Replace `web/app/globals.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 210 40% 98%;      /* slate-50  */
    --foreground: 222 47% 11%;      /* slate-900 */
    --card: 0 0% 100%;
    --card-foreground: 222 47% 11%;
    --muted: 210 40% 96%;
    --muted-foreground: 215 16% 47%;
    --primary: 243 75% 59%;         /* indigo-600 */
    --primary-foreground: 0 0% 100%;
    --accent: 226 100% 97%;         /* indigo-50 */
    --accent-foreground: 243 75% 59%;
    --destructive: 0 84% 60%;
    --success: 160 84% 39%;
    --warning: 38 92% 50%;
    --border: 214 32% 91%;
    --input: 214 32% 91%;
    --ring: 243 75% 59%;
    --radius: 0.75rem;
  }
  .dark {
    --background: 222 47% 5%;        /* slate-950-ish #020617 */
    --foreground: 210 40% 96%;
    --card: 222 47% 11%;            /* slate-900 */
    --card-foreground: 210 40% 96%;
    --muted: 217 33% 17%;
    --muted-foreground: 215 20% 65%;
    --primary: 234 89% 74%;         /* indigo-400 #818CF8 */
    --primary-foreground: 222 47% 11%;
    --accent: 217 33% 17%;
    --accent-foreground: 234 89% 74%;
    --destructive: 0 72% 51%;
    --success: 160 84% 39%;
    --warning: 38 92% 50%;
    --border: 217 33% 17%;
    --input: 217 33% 17%;
    --ring: 234 89% 74%;
  }
  * { @apply border-border; }
  body { @apply bg-background text-foreground antialiased; }
}
```

- [ ] **Step 2: Tailwind theme**

Replace `web/tailwind.config.ts`:
```ts
import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
        muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
        primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
        accent: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
        destructive: "hsl(var(--destructive))",
        success: "hsl(var(--success))",
        warning: "hsl(var(--warning))",
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
      },
      borderRadius: { lg: "var(--radius)", md: "calc(var(--radius) - 2px)", sm: "calc(var(--radius) - 4px)" },
      fontFamily: { sans: ["var(--font-inter)", "var(--font-noto-jp)", "var(--font-noto-sc)", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
} satisfies Config;
```

- [ ] **Step 3: cn() util**

Create `web/lib/utils.ts`:
```ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 4: Init shadcn/ui + base components**

```bash
cd web
npx shadcn@latest init -d
npx shadcn@latest add button input textarea card sheet dropdown-menu tooltip skeleton badge
```
Expected: `web/components/ui/*` created, `components.json` written. If `init -d` prompts, accept defaults (style: default, base color: slate, CSS vars: yes). Our `globals.css`/`tailwind.config.ts` from Steps 1–2 take precedence — re-apply them if the CLI overwrote them.

- [ ] **Step 5: Providers (theme + query)**

Create `web/components/providers.tsx`:
```tsx
"use client";

import { ThemeProvider } from "next-themes";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient());
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </ThemeProvider>
  );
}
```

- [ ] **Step 6: Boot-verify dark mode tokens**

Add a temporary `<div className="bg-primary text-primary-foreground p-2">x</div>` to the home stub, run `npm run dev`, toggle `.dark` on `<html>` via devtools.
Expected: indigo swaps from `#4F46E5` (light) to `#818CF8` (dark). Remove the temp div.

- [ ] **Step 7: Commit**

```bash
git add web/app/globals.css web/tailwind.config.ts web/lib/utils.ts web/components/providers.tsx web/components/ui web/components.json
git commit -m "feat(web): Calm Trust design tokens, dark mode, shadcn/ui, providers"
```

---

## Task 5: SSE parser (TDD)

**Files:**
- Create: `web/lib/types.ts`, `web/lib/sse.ts`
- Test: `web/lib/sse.test.ts`
- Create: `web/vitest.config.ts`, `web/vitest.setup.ts`

- [ ] **Step 1: Vitest config**

Create `web/vitest.config.ts`:
```ts
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom", setupFiles: ["./vitest.setup.ts"], globals: true },
  resolve: { alias: { "@": path.resolve(__dirname, ".") } },
});
```

Create `web/vitest.setup.ts`:
```ts
import "@testing-library/jest-dom/vitest";
```

Add to `web/package.json` `"scripts"`: `"test": "vitest run"`, `"test:watch": "vitest"`.

- [ ] **Step 2: Shared types**

Create `web/lib/types.ts`:
```ts
export type Route = "tax" | "visa" | "ward_office";

export type ChatEvent =
  | { event: "route"; data: { route: Route } }
  | { event: "tool"; data: { name: string } }
  | { event: "token"; data: { text: string } }
  | { event: "error"; data: { error: string } }
  | { event: "done"; data: { thread_id: string; citations: string[] } };

export interface ConversationSummary { thread_id: string; title: string; turns: number; }
export interface ConversationMessage { role: "user" | "assistant"; content: string; citations: string[]; }
export interface SearchResult { rank: number; citation: string; score: number; domain: string | null; snippet: string; }
export interface Health { status: string; elasticsearch: boolean; qdrant: boolean; }
```

- [ ] **Step 3: Write the failing test**

Create `web/lib/sse.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { parseSSE } from "./sse";

function streamFrom(text: string): ReadableStream<Uint8Array> {
  const bytes = new TextEncoder().encode(text);
  return new ReadableStream({
    start(controller) {
      controller.enqueue(bytes.slice(0, 12));
      controller.enqueue(bytes.slice(12));
      controller.close();
    },
  });
}

describe("parseSSE", () => {
  it("parses event/data pairs across chunk boundaries", async () => {
    const raw =
      "event: route\ndata: {\"route\":\"tax\"}\n\n" +
      "event: token\ndata: {\"text\":\"Hi\"}\n\n" +
      ": keep-alive\n" +
      "event: done\ndata: {\"thread_id\":\"t1\",\"citations\":[]}\n\n";
    const events = [];
    for await (const e of parseSSE(streamFrom(raw))) events.push(e);
    expect(events).toEqual([
      { event: "route", data: { route: "tax" } },
      { event: "token", data: { text: "Hi" } },
      { event: "done", data: { thread_id: "t1", citations: [] } },
    ]);
  });
});
```

- [ ] **Step 4: Run it to verify failure**

Run: `cd web && npx vitest run lib/sse.test.ts`
Expected: FAIL — `parseSSE` is not defined.

- [ ] **Step 5: Implement parseSSE**

Create `web/lib/sse.ts`:
```ts
import type { ChatEvent } from "./types";

export async function* parseSSE(body: ReadableStream<Uint8Array>): AsyncGenerator<ChatEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let event = "message";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let nl: number;
    while ((nl = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, nl).replace(/\r$/, "");
      buffer = buffer.slice(nl + 1);
      if (line === "" || line.startsWith(":")) continue;
      if (line.startsWith("event:")) {
        event = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        const data = JSON.parse(line.slice(5).trim());
        yield { event, data } as ChatEvent;
        event = "message";
      }
    }
  }
}
```

- [ ] **Step 6: Run it to verify pass**

Run: `cd web && npx vitest run lib/sse.test.ts`
Expected: PASS (1 test).

- [ ] **Step 7: Commit**

```bash
git add web/vitest.config.ts web/vitest.setup.ts web/lib/types.ts web/lib/sse.ts web/lib/sse.test.ts web/package.json
git commit -m "test(web): SSE stream parser (TDD)"
```

---

## Task 6: Chat state machine (TDD)

**Files:**
- Create: `web/lib/chat-machine.ts`
- Test: `web/lib/chat-machine.test.ts`

- [ ] **Step 1: Write the failing test**

Create `web/lib/chat-machine.test.ts`:
```ts
import { describe, it, expect } from "vitest";
import { initialTurn, applyEvent, type TurnState } from "./chat-machine";

describe("chat-machine", () => {
  it("accumulates tokens", () => {
    let s: TurnState = initialTurn();
    s = applyEvent(s, { event: "token", data: { text: "Hel" } });
    s = applyEvent(s, { event: "token", data: { text: "lo" } });
    expect(s.answer).toBe("Hello");
  });

  it("records the route", () => {
    const s = applyEvent(initialTurn(), { event: "route", data: { route: "tax" } });
    expect(s.route).toBe("tax");
  });

  it("resets the in-progress preamble when a tool runs", () => {
    let s = applyEvent(initialTurn(), { event: "token", data: { text: "thinking..." } });
    s = applyEvent(s, { event: "tool", data: { name: "income_tax_estimator" } });
    expect(s.answer).toBe("");
    expect(s.tools).toEqual(["income_tax_estimator"]);
  });

  it("captures citations and thread id on done", () => {
    const s = applyEvent(initialTurn(), {
      event: "done",
      data: { thread_id: "t9", citations: ["[1] foo"] },
    });
    expect(s.threadId).toBe("t9");
    expect(s.citations).toEqual(["[1] foo"]);
    expect(s.done).toBe(true);
  });

  it("flags errors", () => {
    const s = applyEvent(initialTurn(), { event: "error", data: { error: "boom" } });
    expect(s.error).toBe(true);
  });
});
```

- [ ] **Step 2: Run it to verify failure**

Run: `cd web && npx vitest run lib/chat-machine.test.ts`
Expected: FAIL — module not found / `applyEvent` undefined.

- [ ] **Step 3: Implement the reducer**

Create `web/lib/chat-machine.ts`:
```ts
import type { ChatEvent, Route } from "./types";

export interface TurnState {
  answer: string;
  route: Route | null;
  tools: string[];
  citations: string[];
  threadId: string | null;
  done: boolean;
  error: boolean;
}

export function initialTurn(): TurnState {
  return { answer: "", route: null, tools: [], citations: [], threadId: null, done: false, error: false };
}

export function applyEvent(state: TurnState, ev: ChatEvent): TurnState {
  switch (ev.event) {
    case "route":
      return { ...state, route: ev.data.route };
    case "tool":
      // text streamed before a tool call was a preamble — drop it
      return { ...state, answer: "", tools: [...state.tools, ev.data.name] };
    case "token":
      return { ...state, answer: state.answer + ev.data.text };
    case "done":
      return { ...state, threadId: ev.data.thread_id, citations: ev.data.citations ?? [], done: true };
    case "error":
      return { ...state, error: true };
    default:
      return state;
  }
}
```

- [ ] **Step 4: Run it to verify pass**

Run: `cd web && npx vitest run lib/chat-machine.test.ts`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add web/lib/chat-machine.ts web/lib/chat-machine.test.ts
git commit -m "test(web): chat state machine reducer (TDD)"
```

---

## Task 7: useChat hook + API fetchers

**Files:**
- Create: `web/lib/api.ts`, `web/hooks/use-chat.ts`

- [ ] **Step 1: Typed fetchers**

Create `web/lib/api.ts`:
```ts
import type { ConversationSummary, ConversationMessage, SearchResult, Health } from "./types";

export async function fetchHealth(): Promise<Health> {
  const r = await fetch("/api/health", { cache: "no-store" });
  if (!r.ok) throw new Error("health failed");
  return r.json();
}

export async function fetchConversations(limit = 30): Promise<ConversationSummary[]> {
  const r = await fetch(`/api/conversations?limit=${limit}`);
  if (!r.ok) throw new Error("conversations failed");
  return (await r.json()).conversations ?? [];
}

export async function fetchConversation(threadId: string): Promise<ConversationMessage[]> {
  const r = await fetch(`/api/conversations/${threadId}`);
  if (!r.ok) throw new Error("conversation failed");
  return (await r.json()).messages ?? [];
}

export async function deleteConversation(threadId: string): Promise<void> {
  await fetch(`/api/conversations/${threadId}`, { method: "DELETE" });
}

export async function search(q: string, domain: string, topK: number): Promise<SearchResult[]> {
  const params = new URLSearchParams({ q, top_k: String(topK) });
  if (domain) params.set("domain", domain);
  const r = await fetch(`/api/search?${params.toString()}`);
  if (!r.ok) throw new Error("search failed");
  return (await r.json()).results ?? [];
}
```

- [ ] **Step 2: useChat hook**

Create `web/hooks/use-chat.ts`:
```ts
"use client";

import { useCallback, useRef, useState } from "react";
import { parseSSE } from "@/lib/sse";
import { applyEvent, initialTurn } from "@/lib/chat-machine";
import type { ConversationMessage, Route } from "@/lib/types";

const THREAD_KEY = "japanlife.threadId";

export interface ChatMessage extends ConversationMessage {
  route?: Route | null;
  tools?: string[];
}

export function useChat(initial: ChatMessage[] = []) {
  const [messages, setMessages] = useState<ChatMessage[]>(initial);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(
    typeof window !== "undefined" ? localStorage.getItem(THREAD_KEY) : null,
  );
  const abortRef = useRef<AbortController | null>(null);

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const reset = useCallback(() => {
    setMessages([]);
    setThreadId(null);
    if (typeof window !== "undefined") localStorage.removeItem(THREAD_KEY);
  }, []);

  const load = useCallback((tid: string, msgs: ChatMessage[]) => {
    setThreadId(tid);
    setMessages(msgs);
    if (typeof window !== "undefined") localStorage.setItem(THREAD_KEY, tid);
  }, []);

  const send = useCallback(async (text: string) => {
    if (!text.trim() || streaming) return;
    setError(false);
    setStreaming(true);
    setMessages((m) => [...m, { role: "user", content: text, citations: [] }, { role: "assistant", content: "", citations: [], route: null, tools: [] }]);

    const controller = new AbortController();
    abortRef.current = controller;
    let turn = initialTurn();

    try {
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message: text, thread_id: threadId }),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) throw new Error("stream failed");

      for await (const ev of parseSSE(res.body)) {
        turn = applyEvent(turn, ev);
        setMessages((m) => {
          const next = [...m];
          next[next.length - 1] = {
            role: "assistant",
            content: turn.answer,
            citations: turn.citations,
            route: turn.route,
            tools: turn.tools,
          };
          return next;
        });
      }
      if (turn.error) setError(true);
      if (turn.threadId) {
        setThreadId(turn.threadId);
        if (typeof window !== "undefined") localStorage.setItem(THREAD_KEY, turn.threadId);
      }
    } catch (e) {
      if ((e as Error).name !== "AbortError") setError(true);
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }, [streaming, threadId]);

  return { messages, streaming, error, threadId, send, stop, reset, load };
}
```

- [ ] **Step 3: Typecheck**

Run: `cd web && npx tsc --noEmit`
Expected: no type errors.

- [ ] **Step 4: Commit**

```bash
git add web/lib/api.ts web/hooks/use-chat.ts
git commit -m "feat(web): useChat streaming hook + typed API fetchers"
```

## Task 8: Chat components + Assistant page

**Files:**
- Create: `web/components/chat/RoutingBadge.tsx`, `ToolStep.tsx`, `Citations.tsx`, `Disclaimer.tsx`, `MessageBubble.tsx`, `ChatInput.tsx`, `SuggestedQuestions.tsx`, `ChatWindow.tsx`
- Create: `web/app/[locale]/chat/page.tsx`

- [ ] **Step 1: Routing badge + tool step**

Create `web/components/chat/RoutingBadge.tsx`:
```tsx
import { useTranslations } from "next-intl";
import type { Route } from "@/lib/types";

const EMOJI: Record<Route, string> = { tax: "🧾", visa: "🛂", ward_office: "🏛️" };

export function RoutingBadge({ route, tools }: { route?: Route | null; tools?: string[] }) {
  const t = useTranslations("chat");
  if (!route && !(tools && tools.length)) return null;
  return (
    <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
      {route && <span>{EMOJI[route]} {t("routedTo", { route })}</span>}
      {tools && tools.length > 0 && <span>🔧 {Array.from(new Set(tools)).join(", ")}</span>}
    </div>
  );
}
```

Create `web/components/chat/ToolStep.tsx`:
```tsx
export function ToolStep({ name }: { name: string }) {
  return <span className="rounded-md bg-muted px-2 py-0.5 text-xs text-muted-foreground">🔧 {name}</span>;
}
```

- [ ] **Step 2: Citations + disclaimer**

Create `web/components/chat/Citations.tsx`:
```tsx
"use client";
import { useTranslations } from "next-intl";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown } from "lucide-react";

export function Citations({ citations }: { citations: string[] }) {
  const t = useTranslations("chat");
  if (!citations.length) return null;
  return (
    <Collapsible className="mt-2 rounded-lg border bg-card p-2 text-sm">
      <CollapsibleTrigger className="flex items-center gap-1 text-muted-foreground">
        <ChevronDown className="h-4 w-4" /> {t("sources", { count: citations.length })}
      </CollapsibleTrigger>
      <CollapsibleContent className="mt-1 space-y-1">
        {citations.map((c, i) => <div key={i} className="text-muted-foreground">- {c}</div>)}
      </CollapsibleContent>
    </Collapsible>
  );
}
```
(If `collapsible` is not present, run `npx shadcn@latest add collapsible` in `web/`.)

Create `web/components/chat/Disclaimer.tsx`:
```tsx
import { useTranslations } from "next-intl";

export function Disclaimer() {
  const t = useTranslations("chat");
  return <p className="mt-1 text-[11px] text-muted-foreground">ⓘ {t("disclaimer")}</p>;
}
```

- [ ] **Step 3: Message bubble (Markdown)**

Create `web/components/chat/MessageBubble.tsx`:
```tsx
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/hooks/use-chat";
import { RoutingBadge } from "./RoutingBadge";
import { Citations } from "./Citations";

export function MessageBubble({ message, streaming }: { message: ChatMessage; streaming?: boolean }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("my-2 flex flex-col", isUser ? "items-end" : "items-start")}>
      {!isUser && <RoutingBadge route={message.route} tools={message.tools} />}
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-3 py-2 text-sm",
          isUser ? "rounded-br-md bg-primary text-primary-foreground" : "rounded-bl-md bg-muted text-foreground",
        )}
      >
        {isUser ? (
          message.content
        ) : (
          <div className="prose prose-sm max-w-none dark:prose-invert">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            {streaming && <span className="text-primary">▌</span>}
          </div>
        )}
      </div>
      {!isUser && <Citations citations={message.citations} />}
    </div>
  );
}
```
(Add the typography plugin: `cd web && npm install -D @tailwindcss/typography`, then add `import typography from "@tailwindcss/typography"` and `plugins: [typography]` to `tailwind.config.ts`.)

- [ ] **Step 4: Chat input (with stop)**

Create `web/components/chat/ChatInput.tsx`:
```tsx
"use client";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send, Square } from "lucide-react";

export function ChatInput({ onSend, onStop, streaming }: { onSend: (t: string) => void; onStop: () => void; streaming: boolean; }) {
  const t = useTranslations("chat");
  const [value, setValue] = useState("");
  const submit = () => { const v = value.trim(); if (v) { onSend(v); setValue(""); } };
  return (
    <div className="flex items-end gap-2 border-t bg-background p-3">
      <Textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
        placeholder={t("placeholder")}
        rows={1}
        className="min-h-[44px] resize-none"
        aria-label={t("placeholder")}
      />
      {streaming ? (
        <Button variant="destructive" size="icon" onClick={onStop} aria-label={t("stop")}><Square className="h-4 w-4" /></Button>
      ) : (
        <Button size="icon" onClick={submit} aria-label={t("send")}><Send className="h-4 w-4" /></Button>
      )}
    </div>
  );
}
```

- [ ] **Step 5: Suggested questions**

Create `web/components/chat/SuggestedQuestions.tsx`:
```tsx
"use client";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";

export function SuggestedQuestions({ onPick }: { onPick: (q: string) => void }) {
  const t = useTranslations();
  const qs = [t("examples.q1"), t("examples.q2"), t("examples.q3")];
  return (
    <div className="flex flex-col items-center gap-2 p-6 text-center">
      <p className="text-sm text-muted-foreground">{t("chat.empty")}</p>
      <div className="flex flex-wrap justify-center gap-2">
        {qs.map((q) => <Button key={q} variant="outline" size="sm" onClick={() => onPick(q)}>{q}</Button>)}
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Chat window**

Create `web/components/chat/ChatWindow.tsx`:
```tsx
"use client";
import { useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import { useChat } from "@/hooks/use-chat";
import { MessageBubble } from "./MessageBubble";
import { ChatInput } from "./ChatInput";
import { SuggestedQuestions } from "./SuggestedQuestions";
import { Disclaimer } from "./Disclaimer";

export function ChatWindow({ chat, initialQuery }: { chat: ReturnType<typeof useChat>; initialQuery?: string }) {
  const t = useTranslations("chat");
  const { messages, streaming, error, send, stop } = chat;
  const endRef = useRef<HTMLDivElement>(null);
  const sentInitial = useRef(false);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);
  useEffect(() => {
    if (initialQuery && !sentInitial.current) { sentInitial.current = true; send(initialQuery); }
  }, [initialQuery, send]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-3" aria-live="polite" aria-busy={streaming}>
        {messages.length === 0 ? (
          <SuggestedQuestions onPick={send} />
        ) : (
          messages.map((m, i) => (
            <MessageBubble key={i} message={m} streaming={streaming && i === messages.length - 1 && m.role === "assistant"} />
          ))
        )}
        {error && <p className="p-3 text-sm text-destructive">{t("error")}</p>}
        <div ref={endRef} />
      </div>
      <Disclaimer />
      <ChatInput onSend={send} onStop={stop} streaming={streaming} />
    </div>
  );
}
```

- [ ] **Step 7: Assistant page**

Create `web/app/[locale]/chat/page.tsx`:
```tsx
"use client";
import { useSearchParams } from "next/navigation";
import { useChat } from "@/hooks/use-chat";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { HistoryDrawer } from "@/components/history/HistoryDrawer";

export default function ChatPage() {
  const params = useSearchParams();
  const initialQuery = params.get("q") ?? undefined;
  const chat = useChat();
  return (
    <main className="mx-auto flex h-[calc(100dvh-3.5rem)] w-full max-w-3xl flex-col">
      <div className="flex items-center justify-end p-2"><HistoryDrawer chat={chat} /></div>
      <ChatWindow chat={chat} initialQuery={initialQuery} />
    </main>
  );
}
```
(`HistoryDrawer` is created in Task 11; until then, comment its import/usage to boot-test, or do Task 11 before booting `/chat`.)

- [ ] **Step 8: Commit**

```bash
git add web/components/chat web/app/[locale]/chat web/tailwind.config.ts web/package.json
git commit -m "feat(web): streaming chat UI (bubbles, citations, routing, input)"
```

---

## Task 9: Layout chrome — Navbar, Footer, Language, Theme, Health

**Files:**
- Create: `web/components/layout/{Navbar,Footer,LanguageSwitcher,ThemeToggle,HealthIndicator}.tsx`
- Modify: `web/app/[locale]/layout.tsx` (fonts + Providers + Navbar/Footer)

- [ ] **Step 1: Theme toggle**

Create `web/components/layout/ThemeToggle.tsx`:
```tsx
"use client";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Moon, Sun } from "lucide-react";
import { useTranslations } from "next-intl";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const t = useTranslations("nav");
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return (
    <Button variant="ghost" size="icon" aria-label={t("theme")}
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
      {mounted && theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </Button>
  );
}
```

- [ ] **Step 2: Language switcher**

Create `web/components/layout/LanguageSwitcher.tsx`:
```tsx
"use client";
import { useLocale, useTranslations } from "next-intl";
import { usePathname, useRouter } from "@/i18n/routing";
import { routing } from "@/i18n/routing";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Globe } from "lucide-react";

const LABEL: Record<string, string> = { en: "English", ja: "日本語", zh: "中文" };

export function LanguageSwitcher() {
  const locale = useLocale();
  const t = useTranslations("nav");
  const pathname = usePathname();
  const router = useRouter();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" aria-label={t("language")}><Globe className="mr-1 h-4 w-4" />{LABEL[locale]}</Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {routing.locales.map((l) => (
          <DropdownMenuItem key={l} onClick={() => router.replace(pathname, { locale: l })} disabled={l === locale}>
            {LABEL[l]}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

- [ ] **Step 3: Health indicator**

Create `web/components/layout/HealthIndicator.tsx`:
```tsx
"use client";
import { useQuery } from "@tanstack/react-query";
import { fetchHealth } from "@/lib/api";
import { useTranslations } from "next-intl";

export function HealthIndicator() {
  const t = useTranslations("health");
  const { data, isError } = useQuery({ queryKey: ["health"], queryFn: fetchHealth, refetchInterval: 30000 });
  const ok = data?.status === "ok";
  const label = isError ? t("down") : ok ? t("ok") : t("degraded");
  const color = isError ? "bg-destructive" : ok ? "bg-success" : "bg-warning";
  return <span className="flex items-center gap-1 text-xs text-muted-foreground"><span className={`h-2 w-2 rounded-full ${color}`} />{label}</span>;
}
```

- [ ] **Step 4: Navbar + Footer**

Create `web/components/layout/Navbar.tsx`:
```tsx
import { useTranslations } from "next-intl";
import { Link } from "@/i18n/routing";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { ThemeToggle } from "./ThemeToggle";

export function Navbar() {
  const t = useTranslations("nav");
  const app = useTranslations("app");
  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b bg-background/80 px-4 backdrop-blur">
      <Link href="/" className="font-bold text-primary">🗾 {app("name")}</Link>
      <nav className="hidden gap-4 text-sm text-muted-foreground sm:flex">
        <Link href="/">{t("home")}</Link>
        <Link href="/chat">{t("assistant")}</Link>
        <Link href="/how-it-works">{t("howItWorks")}</Link>
      </nav>
      <div className="flex items-center gap-1"><LanguageSwitcher /><ThemeToggle /></div>
    </header>
  );
}
```

Create `web/components/layout/Footer.tsx`:
```tsx
import { Link } from "@/i18n/routing";
import { HealthIndicator } from "./HealthIndicator";

export function Footer() {
  return (
    <footer className="flex items-center justify-between border-t px-4 py-3 text-xs text-muted-foreground">
      <span>LangGraph · DeepSeek · ElasticSearch · Qdrant · FastAPI</span>
      <div className="flex items-center gap-3">
        <Link href="/dev/retrieval">Retrieval inspector</Link>
        <HealthIndicator />
      </div>
    </footer>
  );
}
```

- [ ] **Step 5: Wire fonts + providers + chrome into layout**

Replace `web/app/[locale]/layout.tsx`:
```tsx
import type { Metadata } from "next";
import { Inter, Noto_Sans_JP, Noto_Sans_SC } from "next/font/google";
import { NextIntlClientProvider, hasLocale } from "next-intl";
import { setRequestLocale, getTranslations } from "next-intl/server";
import { notFound } from "next/navigation";
import { routing } from "@/i18n/routing";
import { Providers } from "@/components/providers";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";
import "../globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const notoJP = Noto_Sans_JP({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-noto-jp" });
const notoSC = Noto_Sans_SC({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-noto-sc" });

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "app" });
  return { title: `${t("name")} — ${t("tagline")}`, description: t("tagline") };
}

export function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({ children, params }: { children: React.ReactNode; params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);
  return (
    <html lang={locale} suppressHydrationWarning className={`${inter.variable} ${notoJP.variable} ${notoSC.variable}`}>
      <body className="flex min-h-dvh flex-col font-sans">
        <NextIntlClientProvider>
          <Providers>
            <Navbar />
            <div className="flex-1">{children}</div>
            <Footer />
          </Providers>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
```

- [ ] **Step 6: Boot-verify**

Run: `cd web && npm run dev`. Visit `/en` — navbar, footer, language switch (try /ja, /zh), theme toggle, and health dot all work (backend running).
Expected: locale persists across navigation; theme toggles; health shows online.

- [ ] **Step 7: Commit**

```bash
git add web/components/layout web/app/[locale]/layout.tsx
git commit -m "feat(web): app chrome — navbar, footer, language + theme toggles, health"
```

## Task 10: Home / landing page

**Files:**
- Create: `web/components/home/Hero.tsx`, `web/components/home/CategoryChips.tsx`
- Replace: `web/app/[locale]/page.tsx`

- [ ] **Step 1: Category chips**

Create `web/components/home/CategoryChips.tsx`:
```tsx
"use client";
import { useRouter } from "@/i18n/routing";
import { useTranslations } from "next-intl";
import { Button } from "@/components/ui/button";

const CATS = [
  { key: "tax", emoji: "🧾", q: "examples.q1" },
  { key: "visa", emoji: "🛂", q: "examples.q2" },
  { key: "wardOffice", emoji: "🏛️", q: "examples.q3" },
] as const;

export function CategoryChips() {
  const t = useTranslations();
  const router = useRouter();
  return (
    <div className="flex flex-wrap justify-center gap-2">
      {CATS.map((c) => (
        <Button key={c.key} variant="outline"
          onClick={() => router.push(`/chat?q=${encodeURIComponent(t(c.q))}`)}>
          {c.emoji} {t(`categories.${c.key}`)}
        </Button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Hero (ask box → /chat?q=)**

Create `web/components/home/Hero.tsx`:
```tsx
"use client";
import { useState } from "react";
import { useRouter } from "@/i18n/routing";
import { useTranslations } from "next-intl";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { CategoryChips } from "./CategoryChips";

export function Hero() {
  const t = useTranslations();
  const router = useRouter();
  const [q, setQ] = useState("");
  const go = () => { const v = q.trim(); if (v) router.push(`/chat?q=${encodeURIComponent(v)}`); };
  return (
    <section className="mx-auto flex max-w-2xl flex-col items-center gap-6 px-4 py-16 text-center">
      <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">{t("app.tagline")}</h1>
      <p className="text-muted-foreground">{t("home.heroSubtitle")}</p>
      <div className="flex w-full gap-2">
        <Input value={q} onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && go()}
          placeholder={t("home.askPlaceholder")} aria-label={t("home.askPlaceholder")} />
        <Button onClick={go}>{t("home.ask")}</Button>
      </div>
      <CategoryChips />
      <p className="text-xs text-muted-foreground">{t("home.trust")}</p>
    </section>
  );
}
```

- [ ] **Step 3: Home page**

Replace `web/app/[locale]/page.tsx`:
```tsx
import { setRequestLocale } from "next-intl/server";
import { Hero } from "@/components/home/Hero";

export default async function HomePage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  return <main><Hero /></main>;
}
```

- [ ] **Step 4: Boot-verify**

Visit `/en`. Type a question → routes to `/en/chat?q=...` and auto-sends. Category chips deep-link a starter prompt.
Expected: full home → chat flow works.

- [ ] **Step 5: Commit**

```bash
git add web/components/home web/app/[locale]/page.tsx
git commit -m "feat(web): home landing with hero ask box + category quick-actions"
```

---

## Task 11: History drawer (list / resume / delete)

**Files:**
- Create: `web/hooks/use-conversations.ts`, `web/components/history/HistoryDrawer.tsx`

- [ ] **Step 1: Conversation queries/mutations**

Create `web/hooks/use-conversations.ts`:
```ts
"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchConversations, fetchConversation, deleteConversation } from "@/lib/api";

export function useConversations() {
  return useQuery({ queryKey: ["conversations"], queryFn: () => fetchConversations(30) });
}

export function useDeleteConversation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteConversation,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["conversations"] }),
  });
}

export { fetchConversation };
```

- [ ] **Step 2: History drawer (Sheet)**

Create `web/components/history/HistoryDrawer.tsx`:
```tsx
"use client";
import { useTranslations } from "next-intl";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { History, Plus, Trash2 } from "lucide-react";
import { useConversations, useDeleteConversation, fetchConversation } from "@/hooks/use-conversations";
import type { useChat } from "@/hooks/use-chat";

export function HistoryDrawer({ chat }: { chat: ReturnType<typeof useChat> }) {
  const t = useTranslations("history");
  const { data: conversations = [] } = useConversations();
  const del = useDeleteConversation();

  const open = async (tid: string) => {
    const msgs = await fetchConversation(tid);
    chat.load(tid, msgs);
  };

  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="ghost" size="sm"><History className="mr-1 h-4 w-4" />{t("title")}</Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-80">
        <SheetHeader><SheetTitle>{t("title")}</SheetTitle></SheetHeader>
        <Button variant="outline" className="my-3 w-full" onClick={chat.reset}><Plus className="mr-1 h-4 w-4" />{t("new")}</Button>
        {conversations.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("empty")}</p>
        ) : (
          <ul className="space-y-1">
            {conversations.map((c) => (
              <li key={c.thread_id} className="flex items-center gap-1">
                <button onClick={() => open(c.thread_id)} title={t("turns", { count: c.turns })}
                  className="flex-1 truncate rounded-md px-2 py-1.5 text-left text-sm hover:bg-muted">
                  {c.title || "(untitled)"}
                </button>
                <Button variant="ghost" size="icon" aria-label={t("delete")} onClick={() => del.mutate(c.thread_id)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </SheetContent>
    </Sheet>
  );
}
```

- [ ] **Step 3: Boot-verify**

With backend running and at least one past conversation: open `/chat`, click History → list shows; click an item → it loads into the chat; New chat clears; trash deletes and the list refreshes.
Expected: list/resume/delete all work; uncomment the `HistoryDrawer` usage in `chat/page.tsx` if it was commented in Task 8.

- [ ] **Step 4: Commit**

```bash
git add web/hooks/use-conversations.ts web/components/history
git commit -m "feat(web): conversation history drawer (list/resume/delete)"
```

---

## Task 12: How-it-works + Retrieval inspector

**Files:**
- Create: `web/app/[locale]/how-it-works/page.tsx`
- Create: `web/components/dev/RetrievalInspector.tsx`, `web/app/[locale]/dev/retrieval/page.tsx`

- [ ] **Step 1: How-it-works page**

Create `web/app/[locale]/how-it-works/page.tsx`:
```tsx
import { setRequestLocale } from "next-intl/server";
import { Card } from "@/components/ui/card";

const STACK: [string, string][] = [
  ["Orchestration", "LangGraph supervisor + ReAct specialists + handoff"],
  ["LLM", "DeepSeek (swappable)"],
  ["Sparse retrieval", "ElasticSearch BM25 + kuromoji"],
  ["Dense retrieval", "Qdrant + BGE-m3"],
  ["Fusion / rerank", "RRF + bge-reranker-v2-m3"],
  ["API", "FastAPI (/chat, /chat/stream SSE, /search, /health)"],
];
const EVAL: [string, string, string][] = [
  ["es_only (BM25 + kuromoji)", "1.000", "0.833"],
  ["qdrant_only (BGE-m3)", "1.000", "1.000"],
  ["hybrid (RRF + rerank)", "1.000", "0.929"],
];

export default async function HowItWorksPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  return (
    <main className="mx-auto max-w-3xl space-y-8 px-4 py-12">
      <section>
        <h1 className="text-2xl font-bold">How it works</h1>
        <p className="mt-2 text-muted-foreground">
          A LangGraph supervisor routes your question to a tax / visa / ward-office specialist, which
          answers with deterministic tools and cited hybrid retrieval. The ward-office agent can hand off
          to the visa/tax agents for cross-cutting procedures.
        </p>
      </section>
      <section>
        <h2 className="mb-3 text-lg font-semibold">Hybrid retrieval</h2>
        <p className="text-sm text-muted-foreground">Query → (BM25 + kuromoji) ∥ (BGE-m3 dense) → RRF fuse → cross-encoder rerank → cited chunks.</p>
      </section>
      <section>
        <h2 className="mb-3 text-lg font-semibold">Tech stack</h2>
        <div className="grid gap-2 sm:grid-cols-2">
          {STACK.map(([k, v]) => <Card key={k} className="p-3"><div className="text-xs font-semibold text-primary">{k}</div><div className="text-sm">{v}</div></Card>)}
        </div>
      </section>
      <section>
        <h2 className="mb-3 text-lg font-semibold">Retrieval evaluation</h2>
        <table className="w-full text-sm">
          <thead><tr className="text-left text-muted-foreground"><th className="py-1">Method</th><th>Recall@5</th><th>MRR</th></tr></thead>
          <tbody>{EVAL.map(([m, r, mrr]) => <tr key={m} className="border-t"><td className="py-1">{m}</td><td>{r}</td><td>{mrr}</td></tr>)}</tbody>
        </table>
        <p className="mt-2 text-xs text-muted-foreground">On this small corpus dense retrieval saturates rank-1; hybrid's edge shows at scale and on rare-term / exact-match queries.</p>
      </section>
    </main>
  );
}
```

- [ ] **Step 2: Retrieval inspector component**

Create `web/components/dev/RetrievalInspector.tsx`:
```tsx
"use client";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { useQuery } from "@tanstack/react-query";
import { search } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

const DOMAINS = ["", "tax", "visa", "ward_office"];

export function RetrievalInspector() {
  const t = useTranslations("dev");
  const [q, setQ] = useState("");
  const [domain, setDomain] = useState("");
  const [topK, setTopK] = useState(5);
  const [submitted, setSubmitted] = useState<{ q: string; domain: string; topK: number } | null>(null);

  const { data: results = [], isFetching } = useQuery({
    queryKey: ["search", submitted],
    queryFn: () => search(submitted!.q, submitted!.domain, submitted!.topK),
    enabled: !!submitted?.q,
  });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <Input className="flex-1" value={q} onChange={(e) => setQ(e.target.value)} placeholder="ふるさと納税 / permanent residency …" aria-label={t("query")} />
        <select className="rounded-md border bg-background px-2 text-sm" value={domain} onChange={(e) => setDomain(e.target.value)} aria-label={t("domain")}>
          {DOMAINS.map((d) => <option key={d} value={d}>{d || t("all")}</option>)}
        </select>
        <Input type="number" min={1} max={10} className="w-20" value={topK} onChange={(e) => setTopK(Number(e.target.value))} aria-label={t("topK")} />
        <Button onClick={() => setSubmitted({ q, domain, topK })} disabled={!q.trim()}>{t("search")}</Button>
      </div>
      {isFetching && <p className="text-sm text-muted-foreground">…</p>}
      {submitted && !isFetching && results.length === 0 && <p className="text-sm text-muted-foreground">{t("noResults")}</p>}
      <ul className="space-y-3">
        {results.map((r) => (
          <li key={r.rank} className="border-b pb-2">
            <div className="text-sm font-medium">#{r.rank} · <code>{r.domain}</code> · score {r.score}</div>
            <div className="text-xs italic text-muted-foreground">{r.citation}</div>
            <p className="mt-1 text-sm text-muted-foreground">{r.snippet}…</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 3: Dev page**

Create `web/app/[locale]/dev/retrieval/page.tsx`:
```tsx
import { setRequestLocale, getTranslations } from "next-intl/server";
import { RetrievalInspector } from "@/components/dev/RetrievalInspector";

export default async function RetrievalPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: "dev" });
  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="mb-4 text-2xl font-bold">{t("retrievalTitle")}</h1>
      <RetrievalInspector />
    </main>
  );
}
```

- [ ] **Step 4: Boot-verify**

Visit `/en/how-it-works` (renders stack + eval table) and `/en/dev/retrieval` (search returns ranked chunks; requires ingested KB).
Expected: both pages render and the inspector returns results.

- [ ] **Step 5: Commit**

```bash
git add web/app/[locale]/how-it-works web/app/[locale]/dev web/components/dev
git commit -m "feat(web): how-it-works page + retrieval inspector"
```

## Task 13: PWA + SEO + accessibility polish

**Files:**
- Modify: `web/next.config.ts` (wrap with PWA)
- Create: `web/public/manifest.webmanifest`, `web/public/icons/icon-192.png`, `web/public/icons/icon-512.png`
- Modify: `web/app/[locale]/layout.tsx` (manifest link + lang metadata)

- [ ] **Step 1: PWA manifest**

Create `web/public/manifest.webmanifest`:
```json
{
  "name": "JapanLife",
  "short_name": "JapanLife",
  "description": "Assistant for foreigners living in Japan — tax, visa & ward-office help.",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#f8fafc",
  "theme_color": "#4f46e5",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

- [ ] **Step 2: Generate placeholder icons**

```bash
cd web/public && mkdir -p icons
# Minimal solid-indigo PNGs (replace with branded art later):
python3 - <<'PY'
import struct, zlib
def png(path, size, rgb=(79,70,229)):
    w=h=size
    raw=b"".join(b"\x00"+bytes(rgb)*w for _ in range(h))
    def chunk(t,d): return struct.pack(">I",len(d))+t+d+struct.pack(">I",zlib.crc32(t+d)&0xffffffff)
    ihdr=struct.pack(">IIBBBBB",w,h,8,2,0,0,0)
    with open(path,"wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",ihdr)+chunk(b"IDAT",zlib.compress(raw,9))+chunk(b"IEND",b""))
png("icons/icon-192.png",192); png("icons/icon-512.png",512)
print("icons written")
PY
```
Expected: `icons/icon-192.png` and `icon-512.png` created.

- [ ] **Step 3: Wrap next.config with PWA**

Replace `web/next.config.ts`:
```ts
import createNextIntlPlugin from "next-intl/plugin";
import withPWAInit from "@ducanh2912/next-pwa";
import type { NextConfig } from "next";

const withNextIntl = createNextIntlPlugin();
const withPWA = withPWAInit({ dest: "public", disable: process.env.NODE_ENV === "development" });

const nextConfig: NextConfig = {};

export default withPWA(withNextIntl(nextConfig) as never) as NextConfig;
```

- [ ] **Step 4: Link the manifest + theme color**

In `web/app/[locale]/layout.tsx`, extend `generateMetadata`'s return with:
```ts
  return {
    title: `${t("name")} — ${t("tagline")}`,
    description: t("tagline"),
    manifest: "/manifest.webmanifest",
    themeColor: "#4f46e5",
    appleWebApp: { capable: true, title: t("name") },
  };
```

- [ ] **Step 5: Reduced-motion + focus base styles**

Append to `web/app/globals.css`:
```css
@layer base {
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
  }
  :focus-visible { @apply outline-none ring-2 ring-ring ring-offset-2 ring-offset-background; }
}
```

- [ ] **Step 6: Boot + production verify**

Run: `cd web && npm run build && npm run start`. In the browser devtools → Application: manifest detected, service worker registered. Run Lighthouse → PWA installable; Accessibility ≥ 95.
Expected: installable PWA; no critical a11y violations.

- [ ] **Step 7: Commit**

```bash
git add web/next.config.ts web/public/manifest.webmanifest web/public/icons web/app/[locale]/layout.tsx web/app/globals.css
git commit -m "feat(web): PWA (manifest + SW), SEO metadata, a11y base styles"
```

---

## Task 14: Component tests

**Files:**
- Create: `web/components/chat/MessageBubble.test.tsx`, `web/components/chat/RoutingBadge.test.tsx`

Tests render with a minimal `NextIntlClientProvider` so `useTranslations` resolves.

- [ ] **Step 1: Test helper-wrapped render for MessageBubble**

Create `web/components/chat/MessageBubble.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import messages from "@/messages/en.json";
import { MessageBubble } from "./MessageBubble";

function wrap(ui: React.ReactNode) {
  return render(<NextIntlClientProvider locale="en" messages={messages}>{ui}</NextIntlClientProvider>);
}

describe("MessageBubble", () => {
  it("renders user text", () => {
    wrap(<MessageBubble message={{ role: "user", content: "Hello tax", citations: [] }} />);
    expect(screen.getByText("Hello tax")).toBeInTheDocument();
  });

  it("renders assistant markdown and citations", () => {
    wrap(<MessageBubble message={{ role: "assistant", content: "**Filing** runs Feb–Mar", citations: ["[1] guide"] }} />);
    expect(screen.getByText("Filing")).toBeInTheDocument();
    expect(screen.getByText(/Sources \(1\)/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Test RoutingBadge**

Create `web/components/chat/RoutingBadge.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import messages from "@/messages/en.json";
import { RoutingBadge } from "./RoutingBadge";

function wrap(ui: React.ReactNode) {
  return render(<NextIntlClientProvider locale="en" messages={messages}>{ui}</NextIntlClientProvider>);
}

describe("RoutingBadge", () => {
  it("shows the route and tools", () => {
    wrap(<RoutingBadge route="tax" tools={["income_tax_estimator"]} />);
    expect(screen.getByText(/routed to tax/)).toBeInTheDocument();
    expect(screen.getByText(/income_tax_estimator/)).toBeInTheDocument();
  });

  it("renders nothing when empty", () => {
    const { container } = wrap(<RoutingBadge route={null} tools={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
```

- [ ] **Step 3: Run the full suite**

Run: `cd web && npm run test`
Expected: PASS — sse (1), chat-machine (5), MessageBubble (2), RoutingBadge (2).

- [ ] **Step 4: Commit**

```bash
git add web/components/chat/MessageBubble.test.tsx web/components/chat/RoutingBadge.test.tsx
git commit -m "test(web): MessageBubble + RoutingBadge component tests"
```

---

## Task 15: Deploy (Docker, compose, Makefile, CI, README) + Streamlit fix

**Files:**
- Create: `web/Dockerfile`, `web/.dockerignore`
- Modify: `web/next.config.ts` (standalone output), `docker-compose.yml`, `Makefile`, `.github/workflows/ci.yml`, `README.md`
- Fix: `streamlit_app.py`

- [ ] **Step 1: Standalone output**

In `web/next.config.ts`, set `const nextConfig: NextConfig = { output: "standalone" };`.

- [ ] **Step 2: web Dockerfile**

Create `web/Dockerfile`:
```dockerfile
FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
```

Create `web/.dockerignore`:
```
node_modules
.next
.git
```

- [ ] **Step 3: compose `web` service**

Add to `docker-compose.yml` under `services:` (after `api`):
```yaml
  web:
    build: ./web
    container_name: japanlife-web
    environment:
      - BACKEND_URL=http://api:8000
    ports:
      - "3000:3000"
    depends_on:
      - api
```

- [ ] **Step 4: Makefile targets**

Add to `Makefile` (and append `web web-build web-test` to the `.PHONY` line):
```makefile
web:
	cd web && npm run dev

web-build:
	cd web && npm run build

web-test:
	cd web && npm run test
```

- [ ] **Step 5: CI job for web**

Add a `web` job to `.github/workflows/ci.yml`:
```yaml
  web:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: web
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: "npm"
          cache-dependency-path: web/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npx tsc --noEmit
      - run: npm run test
      - run: npm run build
        env:
          BACKEND_URL: http://localhost:8000
```

- [ ] **Step 6: Fix the Streamlit bug**

In `streamlit_app.py`, add `import json` to the imports block (it is used at line ~52 but never imported, which crashes streaming chat):
```python
import json
import os

import httpx
import streamlit as st
```

- [ ] **Step 7: README**

Add a "Frontend (web/)" section to `README.md`: dev (`make web`), build (`make web-build`), Docker (`docker compose up` now also serves the product UI at `:3000`), the EN/JA/ZH note, and that the browser talks to FastAPI via a same-origin proxy. Note Streamlit remains as a dev/demo tool.

- [ ] **Step 8: Verify full stack**

Run: `docker compose build web && docker compose up -d`. Visit `http://localhost:3000` → home loads, chat streams from the API in the compose network, history works.
Also confirm `cd web && npm run lint && npx tsc --noEmit && npm run test && npm run build` all pass, and `python -c "import ast; ast.parse(open('streamlit_app.py').read())"` is clean.
Expected: product UI works end-to-end in compose; CI commands green locally.

- [ ] **Step 9: Commit**

```bash
git add web/Dockerfile web/.dockerignore web/next.config.ts docker-compose.yml Makefile .github/workflows/ci.yml README.md streamlit_app.py
git commit -m "feat(web): containerize + compose service + Makefile + CI; fix(streamlit): import json"
```

---

## Self-Review (completed)

**Spec coverage** — every spec section maps to a task:
- §3 Architecture/proxy/structure → Tasks 1, 2, 15 (compose/Dockerfile).
- §4 Pages/routing/i18n → Tasks 3, 8, 10, 12.
- §5 Chat integration/components → Tasks 5, 6, 7, 8.
- §6 Design system / dark mode / PWA / a11y → Tasks 4, 13.
- §7 Testing/tooling → Tasks 5, 6, 14, 15 (CI).
- §8 Deploy → Task 15.
- §3.3 Streamlit `import json` fix → Task 15 Step 6.

**Placeholder scan** — no "TBD/TODO/implement later"; every code step contains complete code. README prose (Task 15 Step 7) is descriptive but bounded to an additive section.

**Type consistency** — `ChatEvent`, `Route`, `TurnState`, `ChatMessage`, `ConversationSummary/Message`, `SearchResult`, `Health` are defined once in `lib/types.ts`/`lib/chat-machine.ts`/`hooks/use-chat.ts` and used consistently. `parseSSE` → `applyEvent` → `useChat` form one typed pipeline. `useChat` exposes `{messages, streaming, error, threadId, send, stop, reset, load}`; consumers (`ChatWindow`, `HistoryDrawer`, `chat/page.tsx`) use exactly those.

**Known sequencing note:** `chat/page.tsx` (Task 8) imports `HistoryDrawer` (Task 11). Either implement Task 11 before booting `/chat`, or temporarily comment the import as noted in Task 8 Step 7.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-19-japanlife-frontend-product.md`.




