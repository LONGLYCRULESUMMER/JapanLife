# Production Next.js Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Streamlit demo with a production-grade Next.js App Router frontend that has separate user and admin experiences: `/chat` for the Agent product surface and `/admin/knowledge` for Git-based knowledge management.

**Architecture:** FastAPI remains the backend for chat, retrieval, conversations, knowledge CRUD, validation, chunk preview, and reindex jobs. The new `web/` app is a real Next.js frontend with separate route groups for public/product pages and admin pages, a typed API client, server/client component boundaries, product-grade loading/error/empty states, and taste-skill visual standards. Streamlit remains optional legacy demo during migration but is removed from README as the primary frontend once the Next.js app is working.

**Tech Stack:** Next.js App Router, React, TypeScript, Tailwind CSS v4, Motion (`motion/react`), Phosphor icons, FastAPI, pytest for backend, npm scripts for frontend lint/build.

---

## Taste-Skill Design Read

Reading this as: production B2C/B2B hybrid assistant frontend for recruiters and technical reviewers, with a premium dark-tech/product-console language, leaning toward Next.js App Router + Tailwind v4 + Geist + restrained Motion.

Taste-skill dials:

```text
DESIGN_VARIANCE: 7
MOTION_INTENSITY: 5
VISUAL_DENSITY: 5
```

Mandatory taste constraints for implementation:

- Do not use Streamlit as the primary frontend.
- Do not use Inter, Roboto, Arial, Open Sans, or Helvetica as the primary font.
- Use `Geist` and `Geist Mono` via `next/font`.
- Use one accent color across the app. Recommended: desaturated emerald.
- Avoid generic AI purple/blue gradients.
- Avoid three equal feature cards as the main visual pattern.
- Use separate route/layout surfaces for user and admin experiences.
- Use loading, empty, and error states for chat, retrieval, document lists, forms, and jobs.
- Use visible focus states and keyboard-friendly forms.
- Use `min-h-[100dvh]`, not `h-screen`.
- Use Motion only in isolated client leaf components.
- No em-dashes in visible copy.

---

## File Structure

| File | Responsibility |
|---|---|
| `web/package.json` | Frontend scripts and dependencies. |
| `web/next.config.ts` | Next.js config. |
| `web/tsconfig.json` | TypeScript config. |
| `web/postcss.config.mjs` | Tailwind v4 PostCSS setup. |
| `web/app/layout.tsx` | Root metadata, fonts, app shell. |
| `web/app/globals.css` | Tailwind import, theme tokens, focus states, base styles. |
| `web/app/page.tsx` | Product landing/redirect page. |
| `web/app/chat/page.tsx` | User Agent chat page. |
| `web/app/admin/knowledge/page.tsx` | Knowledge Admin page. |
| `web/app/not-found.tsx` | Branded 404 page. |
| `web/components/shell/public-shell.tsx` | Public/user layout. |
| `web/components/shell/admin-shell.tsx` | Admin layout. |
| `web/components/chat/chat-console.tsx` | Client chat UI with SSE handling. |
| `web/components/retrieval/retrieval-inspector.tsx` | Hybrid retrieval inspector. |
| `web/components/knowledge/knowledge-admin.tsx` | Client knowledge admin surface. |
| `web/components/knowledge/knowledge-editor.tsx` | Markdown metadata/body editor. |
| `web/components/ui/*` | Reusable product UI primitives: button, panel, field, badge, skeleton, empty state, toast. |
| `web/lib/api.ts` | Typed FastAPI client and SSE parser. |
| `web/lib/types.ts` | Shared frontend TypeScript types. |
| `web/lib/config.ts` | API base URL and admin token config. |
| `web/middleware.ts` | Lightweight admin gate for `/admin/*` using `ADMIN_TOKEN` when configured. |
| `app/knowledge_admin.py` | Backend service for Markdown CRUD, validation, chunk preview, manifest, stale cleanup. |
| `app/routes.py` | FastAPI `/admin/knowledge/*` endpoints. |
| `app/schemas.py` | Request/response schemas. |
| `rag/es_store.py`, `rag/qdrant_store.py` | Delete helpers for stale chunk cleanup. |
| `tests/test_knowledge_admin.py` | Backend service tests. |
| `tests/test_knowledge_admin_api.py` | Backend API tests. |
| `tests/test_stale_cleanup.py` | Stale cleanup regression tests. |
| `README.md`, `docs/backend-engineering.md` | Documentation updates. |

---

## Task 1: Frontend Project Scaffold

**Files:**
- Create: `web/package.json`
- Create: `web/next.config.ts`
- Create: `web/tsconfig.json`
- Create: `web/postcss.config.mjs`
- Create: `web/app/layout.tsx`
- Create: `web/app/globals.css`
- Create: `web/app/not-found.tsx`
- Modify: `.gitignore`

- [ ] **Step 1: Remove committed build artifacts from the plan scope**

Before creating source files, ensure implementation does not commit generated files:

```bash
cd /Users/javagod/VsCodeProjects/JapanLife
find web -maxdepth 1 -name ".next" -o -name "node_modules" -o -name "tsconfig.tsbuildinfo"
```

Expected: these may exist locally, but they must stay ignored and untracked.

- [ ] **Step 2: Update `.gitignore` for frontend artifacts**

Add these entries if missing:

```gitignore
web/.next/
web/node_modules/
web/tsconfig.tsbuildinfo
web/.env.local
```

- [ ] **Step 3: Create `web/package.json`**

```json
{
  "name": "japanlife-web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev --port 3000",
    "build": "next build",
    "start": "next start --port 3000",
    "lint": "next lint"
  },
  "dependencies": {
    "@phosphor-icons/react": "^2.1.10",
    "@tailwindcss/postcss": "^4.1.0",
    "motion": "^12.0.0",
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "tailwindcss": "^4.1.0"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "eslint": "^9.0.0",
    "eslint-config-next": "^15.0.0",
    "typescript": "^5.7.0"
  }
}
```

- [ ] **Step 4: Create Next/Tailwind/TypeScript config**

`web/next.config.ts`:

```ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
};

export default nextConfig;
```

`web/postcss.config.mjs`:

```js
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

export default config;
```

`web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 5: Create root layout and global styles**

`web/app/layout.tsx`:

```tsx
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geist = Geist({
  variable: "--font-geist",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "JapanLife - AI assistant for life in Japan",
  description: "A multi-agent assistant for tax, visa, and ward-office procedures in Japan.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${geist.variable} ${geistMono.variable}`}>{children}</body>
    </html>
  );
}
```

`web/app/globals.css`:

```css
@import "tailwindcss";

:root {
  --background: #07110f;
  --surface: #0d1815;
  --surface-elevated: #13231f;
  --text-primary: #eff8f3;
  --text-muted: #9db2aa;
  --accent: #7dd8ad;
  --accent-strong: #38b77c;
  --danger: #f07878;
  --radius-card: 1.5rem;
}

* {
  box-sizing: border-box;
}

html {
  scroll-behavior: smooth;
}

body {
  margin: 0;
  min-height: 100dvh;
  background:
    radial-gradient(circle at top left, rgb(125 216 173 / 0.16), transparent 32rem),
    radial-gradient(circle at 80% 10%, rgb(255 255 255 / 0.07), transparent 26rem),
    var(--background);
  color: var(--text-primary);
  font-family: var(--font-geist), system-ui, sans-serif;
}

body::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 60;
  opacity: 0.035;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 160 160' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.45'/%3E%3C/svg%3E");
}

::selection {
  background: rgb(125 216 173 / 0.35);
}

:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.001ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 0.001ms !important;
  }
}
```

- [ ] **Step 6: Create branded 404**

`web/app/not-found.tsx`:

```tsx
import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex min-h-[100dvh] items-center justify-center px-6">
      <section className="max-w-xl rounded-[var(--radius-card)] bg-white/[0.04] p-8 ring-1 ring-white/10">
        <p className="font-mono text-sm text-[var(--accent)]">404</p>
        <h1 className="mt-4 text-4xl font-semibold tracking-[-0.04em]">This page is not indexed.</h1>
        <p className="mt-4 text-pretty text-[var(--text-muted)]">
          The route does not exist. Return to the assistant or open the knowledge admin.
        </p>
        <div className="mt-8 flex gap-3">
          <Link className="rounded-full bg-[var(--accent)] px-5 py-3 text-sm font-semibold text-[#07110f]" href="/chat">
            Open chat
          </Link>
          <Link className="rounded-full bg-white/10 px-5 py-3 text-sm font-semibold text-white" href="/admin/knowledge">
            Admin
          </Link>
        </div>
      </section>
    </main>
  );
}
```

- [ ] **Step 7: Install and verify scaffold**

Run:

```bash
cd web
npm install
npm run build
```

Expected: Next.js build succeeds.

- [ ] **Step 8: Commit**

```bash
git add .gitignore web/package.json web/package-lock.json web/next.config.ts web/tsconfig.json web/postcss.config.mjs web/app/layout.tsx web/app/globals.css web/app/not-found.tsx
git commit -m "feat(web): scaffold production Next.js frontend" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 2: API Client, Types, and UI Primitives

**Files:**
- Create: `web/lib/config.ts`
- Create: `web/lib/types.ts`
- Create: `web/lib/api.ts`
- Create: `web/components/ui/button.tsx`
- Create: `web/components/ui/panel.tsx`
- Create: `web/components/ui/field.tsx`
- Create: `web/components/ui/badge.tsx`
- Create: `web/components/ui/skeleton.tsx`
- Create: `web/components/ui/empty-state.tsx`

- [ ] **Step 1: Create config and types**

`web/lib/config.ts`:

```ts
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const ADMIN_TOKEN = process.env.ADMIN_TOKEN ?? "";
```

`web/lib/types.ts`:

```ts
export type Domain = "tax" | "visa" | "ward_office";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  route?: Domain | null;
  citations?: string[];
};

export type SearchResult = {
  rank: number;
  citation: string;
  score: number;
  domain: Domain;
  snippet: string;
};

export type KnowledgeDoc = {
  doc_id: string;
  domain: Domain;
  filename: string;
  doc_title: string;
  source_url: string;
  language: "en" | "ja" | "mixed";
  body?: string;
  needs_reindex?: boolean;
};

export type KnowledgeDocPayload = {
  domain: Domain;
  filename: string;
  doc_title: string;
  source_url: string;
  language: "en" | "ja" | "mixed";
  body: string;
};

export type IngestJob = {
  id: string;
  status: "pending" | "running" | "succeeded" | "failed";
  error?: string | null;
  chunks_indexed?: number | null;
};
```

- [ ] **Step 2: Create typed API client**

`web/lib/api.ts`:

```ts
import { API_BASE_URL } from "./config";
import type { Domain, IngestJob, KnowledgeDoc, KnowledgeDocPayload, SearchResult } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "content-type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function getHealth(): Promise<{ status: string; elasticsearch: boolean; qdrant: boolean }> {
  return request("/health");
}

export async function searchKnowledge(query: string, domain: Domain | "", topK: number): Promise<{ results: SearchResult[] }> {
  const params = new URLSearchParams({ q: query, top_k: String(topK) });
  if (domain) params.set("domain", domain);
  return request(`/search?${params.toString()}`);
}

export async function listKnowledgeDocs(domain: Domain | "", q: string): Promise<{ documents: KnowledgeDoc[] }> {
  const params = new URLSearchParams();
  if (domain) params.set("domain", domain);
  if (q) params.set("q", q);
  return request(`/admin/knowledge/docs?${params.toString()}`);
}

export async function getKnowledgeDoc(docId: string): Promise<KnowledgeDoc> {
  return request(`/admin/knowledge/docs/${docId}`);
}

export async function createKnowledgeDoc(payload: KnowledgeDocPayload): Promise<KnowledgeDoc> {
  return request("/admin/knowledge/docs", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateKnowledgeDoc(docId: string, payload: KnowledgeDocPayload): Promise<KnowledgeDoc> {
  return request(`/admin/knowledge/docs/${docId}`, { method: "PUT", body: JSON.stringify(payload) });
}

export async function deleteKnowledgeDoc(docId: string): Promise<KnowledgeDoc> {
  return request(`/admin/knowledge/docs/${docId}`, { method: "DELETE" });
}

export async function validateKnowledgeDoc(payload: KnowledgeDocPayload): Promise<{ valid: boolean; errors: string[]; warnings: string[] }> {
  return request("/admin/knowledge/validate", { method: "POST", body: JSON.stringify(payload) });
}

export async function previewChunks(docId: string): Promise<{ chunks: Array<{ chunk_id: string; text: string; metadata: Record<string, string | number> }> }> {
  return request(`/admin/knowledge/docs/${docId}/chunks`);
}

export async function triggerKnowledgeReindex(): Promise<IngestJob> {
  return request("/admin/knowledge/reindex", { method: "POST" });
}
```

- [ ] **Step 3: Create UI primitives**

`web/components/ui/button.tsx`:

```tsx
import Link from "next/link";
import type { ComponentProps } from "react";

const base =
  "group inline-flex items-center justify-center gap-2 rounded-full px-5 py-3 text-sm font-semibold transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50";

export function Button({ className = "", ...props }: ComponentProps<"button">) {
  return <button className={`${base} bg-[var(--accent)] text-[#07110f] hover:bg-[var(--accent-strong)] ${className}`} {...props} />;
}

export function SecondaryButton({ className = "", ...props }: ComponentProps<"button">) {
  return <button className={`${base} bg-white/10 text-white ring-1 ring-white/10 hover:bg-white/15 ${className}`} {...props} />;
}

export function ButtonLink({ className = "", ...props }: ComponentProps<typeof Link>) {
  return <Link className={`${base} bg-[var(--accent)] text-[#07110f] hover:bg-[var(--accent-strong)] ${className}`} {...props} />;
}
```

`web/components/ui/panel.tsx`:

```tsx
import type { ComponentProps } from "react";

export function Panel({ className = "", ...props }: ComponentProps<"section">) {
  return (
    <section
      className={`rounded-[var(--radius-card)] bg-white/[0.045] p-5 ring-1 ring-white/10 shadow-[0_24px_80px_rgb(0_0_0/0.22)] ${className}`}
      {...props}
    />
  );
}
```

`web/components/ui/field.tsx`:

```tsx
import type { ComponentProps, ReactNode } from "react";

export function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="grid gap-2">
      <span className="text-sm font-medium text-white">{label}</span>
      {children}
      {hint ? <span className="text-xs text-[var(--text-muted)]">{hint}</span> : null}
    </label>
  );
}

export function Input(props: ComponentProps<"input">) {
  return <input className="rounded-2xl bg-white/[0.06] px-4 py-3 text-sm text-white ring-1 ring-white/10 transition focus:ring-[var(--accent)]" {...props} />;
}

export function Textarea(props: ComponentProps<"textarea">) {
  return <textarea className="min-h-48 rounded-2xl bg-white/[0.06] px-4 py-3 font-mono text-sm text-white ring-1 ring-white/10 transition focus:ring-[var(--accent)]" {...props} />;
}
```

`web/components/ui/badge.tsx`:

```tsx
export function Badge({ children }: { children: React.ReactNode }) {
  return <span className="rounded-full bg-[var(--accent)]/12 px-3 py-1 text-xs font-medium text-[var(--accent)] ring-1 ring-[var(--accent)]/20">{children}</span>;
}
```

`web/components/ui/skeleton.tsx`:

```tsx
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-2xl bg-white/[0.07] ${className}`} />;
}
```

`web/components/ui/empty-state.tsx`:

```tsx
import { Panel } from "./panel";

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <Panel className="text-center">
      <h3 className="text-lg font-semibold">{title}</h3>
      <p className="mx-auto mt-2 max-w-[52ch] text-sm leading-6 text-[var(--text-muted)]">{body}</p>
    </Panel>
  );
}
```

- [ ] **Step 4: Build**

Run:

```bash
cd web
npm run build
```

Expected: build succeeds.

- [ ] **Step 5: Commit**

```bash
git add web/lib web/components
git commit -m "feat(web): add typed API client and UI primitives" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 3: Public Shell, Landing, and Chat Page

**Files:**
- Create: `web/components/shell/public-shell.tsx`
- Create: `web/app/page.tsx`
- Create: `web/app/chat/page.tsx`
- Create: `web/components/chat/chat-console.tsx`

- [ ] **Step 1: Create public shell**

`web/components/shell/public-shell.tsx`:

```tsx
import Link from "next/link";
import { ButtonLink } from "@/components/ui/button";

export function PublicShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-[100dvh]">
      <a className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-[var(--accent)] focus:px-4 focus:py-2 focus:text-[#07110f]" href="#main">
        Skip to content
      </a>
      <header className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
        <Link href="/" className="text-sm font-semibold tracking-[-0.02em]">JapanLife</Link>
        <nav className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
          <Link className="rounded-full px-4 py-2 hover:bg-white/10 hover:text-white" href="/chat">Chat</Link>
          <Link className="rounded-full px-4 py-2 hover:bg-white/10 hover:text-white" href="/admin/knowledge">Admin</Link>
          <ButtonLink href="/chat">Ask</ButtonLink>
        </nav>
      </header>
      <main id="main">{children}</main>
    </div>
  );
}
```

- [ ] **Step 2: Create product landing page**

`web/app/page.tsx`:

```tsx
import { PublicShell } from "@/components/shell/public-shell";
import { ButtonLink } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";

export default function HomePage() {
  return (
    <PublicShell>
      <section className="mx-auto grid min-h-[calc(100dvh-88px)] max-w-7xl items-center gap-10 px-6 py-16 md:grid-cols-[1.1fr_0.9fr]">
        <div>
          <p className="font-mono text-sm text-[var(--accent)]">RAG + Agent for life in Japan</p>
          <h1 className="mt-5 max-w-3xl text-5xl font-semibold leading-[0.95] tracking-[-0.07em] md:text-7xl">
            Tax, visa, and ward-office answers with sources.
          </h1>
          <p className="mt-6 max-w-[58ch] text-lg leading-8 text-[var(--text-muted)]">
            A bilingual multi-agent assistant grounded in curated official knowledge, deterministic tools, and measurable retrieval.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <ButtonLink href="/chat">Open chat</ButtonLink>
            <ButtonLink className="bg-white/10 text-white ring-1 ring-white/10 hover:bg-white/15" href="/admin/knowledge">
              Manage knowledge
            </ButtonLink>
          </div>
        </div>
        <Panel className="p-3">
          <div className="rounded-[calc(var(--radius-card)-0.5rem)] bg-[#0a1512] p-5 ring-1 ring-white/10">
            <div className="grid gap-3">
              {[
                ["tax", "確定申告 deadline and deductions"],
                ["visa", "Permanent residency evidence checklist"],
                ["ward_office", "Moving-in procedure and address update"],
              ].map(([domain, text]) => (
                <div key={domain} className="rounded-2xl bg-white/[0.05] p-4">
                  <p className="font-mono text-xs text-[var(--accent)]">{domain}</p>
                  <p className="mt-2 text-sm text-white">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </Panel>
      </section>
    </PublicShell>
  );
}
```

- [ ] **Step 3: Create chat console**

`web/components/chat/chat-console.tsx`:

```tsx
"use client";

import { useState } from "react";
import { PaperPlaneTilt } from "@phosphor-icons/react";
import { Button } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";
import type { ChatMessage } from "@/lib/types";
import { API_BASE_URL } from "@/lib/config";

async function* streamChat(message: string, threadId: string | null) {
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ message, thread_id: threadId || undefined }),
  });
  if (!response.ok || !response.body) throw new Error("Chat stream failed");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let event = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    for (const line of buffer.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      if (line.startsWith("data:")) yield { event, data: JSON.parse(line.slice(5).trim()) };
    }
    buffer = buffer.endsWith("\n") ? "" : buffer.split("\n").at(-1) ?? "";
  }
}

export function ChatConsole() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [threadId, setThreadId] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function send() {
    const message = input.trim();
    if (!message || pending) return;
    setInput("");
    setError("");
    setPending(true);
    setMessages((prev) => [...prev, { role: "user", content: message }, { role: "assistant", content: "" }]);
    try {
      for await (const chunk of streamChat(message, threadId)) {
        if (chunk.event === "token") {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            next[next.length - 1] = { ...last, content: last.content + (chunk.data.text ?? "") };
            return next;
          });
        }
        if (chunk.event === "route") {
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            next[next.length - 1] = { ...last, route: chunk.data.route };
            return next;
          });
        }
        if (chunk.event === "done") {
          setThreadId(chunk.data.thread_id ?? threadId);
          setMessages((prev) => {
            const next = [...prev];
            const last = next[next.length - 1];
            next[next.length - 1] = { ...last, citations: chunk.data.citations ?? [] };
            return next;
          });
        }
      }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Chat failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <Panel className="grid min-h-[70dvh] grid-rows-[1fr_auto] gap-4">
      <div className="space-y-4 overflow-y-auto pr-2">
        {messages.length === 0 ? (
          <div className="grid h-full place-items-center text-center text-[var(--text-muted)]">
            <p>Ask about tax, visa, or ward-office procedures in English or Japanese.</p>
          </div>
        ) : (
          messages.map((message, index) => (
            <article key={index} className={message.role === "user" ? "ml-auto max-w-2xl rounded-3xl bg-[var(--accent)] p-4 text-[#07110f]" : "max-w-3xl rounded-3xl bg-white/[0.06] p-4"}>
              {message.route ? <p className="mb-2 font-mono text-xs text-[var(--accent)]">{message.route}</p> : null}
              <p className="whitespace-pre-wrap leading-7">{message.content || (pending ? "Thinking..." : "")}</p>
              {message.citations?.length ? (
                <div className="mt-4 border-t border-white/10 pt-3 text-xs text-[var(--text-muted)]">
                  {message.citations.map((citation) => <p key={citation}>{citation}</p>)}
                </div>
              ) : null}
            </article>
          ))
        )}
      </div>
      {error ? <p className="rounded-2xl bg-red-500/10 p-3 text-sm text-red-200">{error}</p> : null}
      <div className="flex gap-3">
        <input
          className="min-w-0 flex-1 rounded-full bg-white/[0.06] px-5 py-4 text-sm text-white ring-1 ring-white/10"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") void send();
          }}
          placeholder="When is the tax filing deadline?"
        />
        <Button disabled={pending} onClick={send}>
          <PaperPlaneTilt size={18} weight="bold" />
          Send
        </Button>
      </div>
    </Panel>
  );
}
```

- [ ] **Step 4: Create chat page**

`web/app/chat/page.tsx`:

```tsx
import { ChatConsole } from "@/components/chat/chat-console";
import { PublicShell } from "@/components/shell/public-shell";

export default function ChatPage() {
  return (
    <PublicShell>
      <section className="mx-auto max-w-7xl px-6 py-12">
        <div className="mb-8">
          <h1 className="text-4xl font-semibold tracking-[-0.05em] md:text-6xl">Ask JapanLife.</h1>
          <p className="mt-4 max-w-[62ch] text-[var(--text-muted)]">
            Routed specialist agents answer with deterministic tools and cited retrieval.
          </p>
        </div>
        <ChatConsole />
      </section>
    </PublicShell>
  );
}
```

- [ ] **Step 5: Build**

Run:

```bash
cd web
npm run build
```

Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add web/app/page.tsx web/app/chat/page.tsx web/components/shell/public-shell.tsx web/components/chat/chat-console.tsx
git commit -m "feat(web): build product chat frontend" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 4: Backend Knowledge Admin API

**Files:**
- Create: `app/knowledge_admin.py`
- Modify: `app/routes.py`
- Modify: `app/schemas.py`
- Modify: `rag/es_store.py`
- Modify: `rag/qdrant_store.py`
- Create: `tests/test_knowledge_admin.py`
- Create: `tests/test_knowledge_admin_api.py`
- Create: `tests/test_stale_cleanup.py`

- [ ] **Step 1: Implement backend using the approved knowledge admin service/API plan**

Use the existing committed plan as the backend source of truth:

```text
docs/superpowers/plans/2026-06-24-knowledge-admin-ui.md
```

Implement its backend tasks only:

```text
Task 1: Knowledge Admin Service
Task 2: Validation and Chunk Preview
Task 3: Manifest and Stale Chunk Cleanup
Task 4: FastAPI Knowledge Admin Routes
```

Do not implement its Streamlit task.

- [ ] **Step 2: Run backend tests**

Run:

```bash
poetry run pytest -q tests/test_knowledge_admin.py tests/test_stale_cleanup.py tests/test_knowledge_admin_api.py
```

Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add app/knowledge_admin.py app/routes.py app/schemas.py rag/es_store.py rag/qdrant_store.py tests/test_knowledge_admin.py tests/test_knowledge_admin_api.py tests/test_stale_cleanup.py
git commit -m "feat(api): add Git-based knowledge admin backend" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 5: Admin Shell and Knowledge Admin Page

**Files:**
- Create: `web/components/shell/admin-shell.tsx`
- Create: `web/components/knowledge/knowledge-admin.tsx`
- Create: `web/components/knowledge/knowledge-editor.tsx`
- Create: `web/app/admin/knowledge/page.tsx`
- Create: `web/middleware.ts`

- [ ] **Step 1: Create admin shell**

`web/components/shell/admin-shell.tsx`:

```tsx
import Link from "next/link";

export function AdminShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-[100dvh] bg-[#07110f]">
      <header className="border-b border-white/10 bg-[#07110f]/85 px-6 py-4">
        <div className="mx-auto flex max-w-7xl items-center justify-between">
          <div>
            <Link href="/admin/knowledge" className="font-semibold tracking-[-0.02em]">JapanLife Admin</Link>
            <p className="text-xs text-[var(--text-muted)]">Knowledge operations</p>
          </div>
          <nav className="flex gap-2 text-sm">
            <Link className="rounded-full px-4 py-2 text-[var(--text-muted)] hover:bg-white/10 hover:text-white" href="/chat">Chat</Link>
            <Link className="rounded-full bg-white/10 px-4 py-2 text-white" href="/admin/knowledge">Knowledge</Link>
          </nav>
        </div>
      </header>
      <main>{children}</main>
    </div>
  );
}
```

- [ ] **Step 2: Create admin middleware**

`web/middleware.ts`:

```ts
import { NextResponse, type NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  const token = process.env.ADMIN_TOKEN;
  if (!token) return NextResponse.next();
  const provided = request.headers.get("x-admin-token") ?? request.cookies.get("admin_token")?.value;
  if (provided === token) return NextResponse.next();
  return new NextResponse("Admin token required", { status: 401 });
}

export const config = {
  matcher: ["/admin/:path*"],
};
```

- [ ] **Step 3: Create knowledge editor**

`web/components/knowledge/knowledge-editor.tsx`:

```tsx
"use client";

import { Field, Input, Textarea } from "@/components/ui/field";
import type { Domain, KnowledgeDocPayload } from "@/lib/types";

export function KnowledgeEditor({
  value,
  onChange,
}: {
  value: KnowledgeDocPayload;
  onChange: (value: KnowledgeDocPayload) => void;
}) {
  function update<K extends keyof KnowledgeDocPayload>(key: K, next: KnowledgeDocPayload[K]) {
    onChange({ ...value, [key]: next });
  }

  return (
    <div className="grid gap-4">
      <div className="grid gap-4 md:grid-cols-3">
        <Field label="Domain">
          <select className="rounded-2xl bg-white/[0.06] px-4 py-3 text-sm text-white ring-1 ring-white/10" value={value.domain} onChange={(event) => update("domain", event.target.value as Domain)}>
            <option value="tax">tax</option>
            <option value="visa">visa</option>
            <option value="ward_office">ward_office</option>
          </select>
        </Field>
        <Field label="Filename">
          <Input value={value.filename} onChange={(event) => update("filename", event.target.value)} />
        </Field>
        <Field label="Language">
          <select className="rounded-2xl bg-white/[0.06] px-4 py-3 text-sm text-white ring-1 ring-white/10" value={value.language} onChange={(event) => update("language", event.target.value as "en" | "ja" | "mixed")}>
            <option value="en">en</option>
            <option value="ja">ja</option>
            <option value="mixed">mixed</option>
          </select>
        </Field>
      </div>
      <Field label="Title">
        <Input value={value.doc_title} onChange={(event) => update("doc_title", event.target.value)} />
      </Field>
      <Field label="Source URL">
        <Input value={value.source_url} onChange={(event) => update("source_url", event.target.value)} />
      </Field>
      <Field label="Markdown body">
        <Textarea value={value.body} onChange={(event) => update("body", event.target.value)} />
      </Field>
    </div>
  );
}
```

- [ ] **Step 4: Create knowledge admin client**

`web/components/knowledge/knowledge-admin.tsx`:

```tsx
"use client";

import { useEffect, useMemo, useState } from "react";
import { Button, SecondaryButton } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";
import { EmptyState } from "@/components/ui/empty-state";
import { KnowledgeEditor } from "./knowledge-editor";
import {
  createKnowledgeDoc,
  deleteKnowledgeDoc,
  getKnowledgeDoc,
  listKnowledgeDocs,
  previewChunks,
  triggerKnowledgeReindex,
  updateKnowledgeDoc,
  validateKnowledgeDoc,
} from "@/lib/api";
import type { Domain, KnowledgeDoc, KnowledgeDocPayload } from "@/lib/types";

const blankDoc: KnowledgeDocPayload = {
  domain: "tax",
  filename: "new-guide.md",
  doc_title: "",
  source_url: "https://example.com/source",
  language: "en",
  body: "# New guide\n\n## Overview\n\nWrite content here.",
};

export function KnowledgeAdmin() {
  const [domain, setDomain] = useState<Domain | "">("");
  const [query, setQuery] = useState("");
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [draft, setDraft] = useState<KnowledgeDocPayload>(blankDoc);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [chunks, setChunks] = useState<Array<{ chunk_id: string; text: string; metadata: Record<string, string | number> }>>([]);

  async function refresh() {
    const response = await listKnowledgeDocs(domain, query);
    setDocs(response.documents);
  }

  useEffect(() => {
    void refresh().catch((error) => setStatus(error.message));
  }, [domain, query]);

  async function openDoc(docId: string) {
    const doc = await getKnowledgeDoc(docId);
    setSelected(doc.doc_id);
    setDraft({
      domain: doc.domain,
      filename: doc.filename,
      doc_title: doc.doc_title,
      source_url: doc.source_url,
      language: doc.language,
      body: doc.body ?? "",
    });
    setChunks([]);
  }

  async function run<T>(fn: () => Promise<T>, message: string) {
    setBusy(true);
    setStatus("");
    try {
      await fn();
      setStatus(message);
      await refresh();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  const visibleTitle = useMemo(() => (selected ? selected : "New document"), [selected]);

  return (
    <section className="mx-auto grid max-w-7xl gap-6 px-6 py-10 lg:grid-cols-[0.9fr_1.4fr]">
      <Panel className="min-h-[70dvh]">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-2xl font-semibold tracking-[-0.04em]">Knowledge docs</h2>
          <SecondaryButton onClick={() => { setSelected(null); setDraft(blankDoc); setChunks([]); }}>New</SecondaryButton>
        </div>
        <div className="mt-5 grid gap-3 md:grid-cols-2">
          <select className="rounded-2xl bg-white/[0.06] px-4 py-3 text-sm text-white ring-1 ring-white/10" value={domain} onChange={(event) => setDomain(event.target.value as Domain | "")}>
            <option value="">all domains</option>
            <option value="tax">tax</option>
            <option value="visa">visa</option>
            <option value="ward_office">ward_office</option>
          </select>
          <input className="rounded-2xl bg-white/[0.06] px-4 py-3 text-sm text-white ring-1 ring-white/10" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search title or URL" />
        </div>
        <div className="mt-5 grid gap-2">
          {docs.length ? docs.map((doc) => (
            <button key={doc.doc_id} className="rounded-2xl bg-white/[0.04] p-4 text-left ring-1 ring-white/10 transition hover:bg-white/[0.07]" onClick={() => void openDoc(doc.doc_id)}>
              <p className="font-mono text-xs text-[var(--accent)]">{doc.domain} / {doc.language}</p>
              <p className="mt-1 font-medium">{doc.doc_title}</p>
              <p className="mt-1 truncate text-xs text-[var(--text-muted)]">{doc.doc_id}</p>
            </button>
          )) : <EmptyState title="No documents" body="Adjust the filter or create a new knowledge document." />}
        </div>
      </Panel>

      <Panel>
        <div className="mb-5 flex items-center justify-between gap-3">
          <div>
            <p className="font-mono text-xs text-[var(--accent)]">Git-based Markdown</p>
            <h2 className="text-2xl font-semibold tracking-[-0.04em]">{visibleTitle}</h2>
          </div>
          <Button disabled={busy} onClick={() => run(async () => { const job = await triggerKnowledgeReindex(); setStatus(`Reindex job ${job.id} started`); }, "Reindex started")}>
            Reindex
          </Button>
        </div>
        <KnowledgeEditor value={draft} onChange={setDraft} />
        <div className="mt-5 flex flex-wrap gap-3">
          <SecondaryButton disabled={busy} onClick={() => run(async () => { const result = await validateKnowledgeDoc(draft); setStatus(result.valid ? "Document is valid" : result.errors.join(", ")); }, "Validated")}>Validate</SecondaryButton>
          <Button disabled={busy} onClick={() => run(async () => { const saved = selected ? await updateKnowledgeDoc(selected, draft) : await createKnowledgeDoc(draft); setSelected(saved.doc_id); }, "Saved. Reindex is required.")}>Save</Button>
          <SecondaryButton disabled={busy || !selected} onClick={() => run(async () => { if (selected) setChunks((await previewChunks(selected)).chunks); }, "Chunk preview loaded")}>Preview chunks</SecondaryButton>
          <SecondaryButton disabled={busy || !selected} onClick={() => run(async () => { if (selected) await deleteKnowledgeDoc(selected); setSelected(null); setDraft(blankDoc); }, "Soft-deleted. Reindex is required.")}>Soft delete</SecondaryButton>
        </div>
        {status ? <p className="mt-4 rounded-2xl bg-white/[0.06] p-3 text-sm text-[var(--text-muted)]">{status}</p> : null}
        {chunks.length ? (
          <div className="mt-5 grid gap-3">
            {chunks.map((chunk) => (
              <div key={chunk.chunk_id} className="rounded-2xl bg-white/[0.04] p-4 ring-1 ring-white/10">
                <p className="font-mono text-xs text-[var(--accent)]">{chunk.chunk_id}</p>
                <p className="mt-2 text-sm text-[var(--text-muted)]">{chunk.text.slice(0, 500)}</p>
              </div>
            ))}
          </div>
        ) : null}
      </Panel>
    </section>
  );
}
```

- [ ] **Step 5: Create admin page**

`web/app/admin/knowledge/page.tsx`:

```tsx
import { AdminShell } from "@/components/shell/admin-shell";
import { KnowledgeAdmin } from "@/components/knowledge/knowledge-admin";

export default function KnowledgeAdminPage() {
  return (
    <AdminShell>
      <section className="mx-auto max-w-7xl px-6 pt-10">
        <p className="font-mono text-sm text-[var(--accent)]">Admin console</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-[-0.05em] md:text-6xl">Knowledge operations.</h1>
        <p className="mt-4 max-w-[64ch] text-[var(--text-muted)]">
          Manage Markdown source files, validate metadata, preview chunks, and reindex ES/Qdrant with stale cleanup.
        </p>
      </section>
      <KnowledgeAdmin />
    </AdminShell>
  );
}
```

- [ ] **Step 6: Build**

Run:

```bash
cd web
npm run build
```

Expected: build succeeds.

- [ ] **Step 7: Commit**

```bash
git add web/app/admin web/components/shell/admin-shell.tsx web/components/knowledge web/middleware.ts
git commit -m "feat(web): build knowledge admin frontend" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 6: Retrieval Inspector and Production States

**Files:**
- Create: `web/components/retrieval/retrieval-inspector.tsx`
- Modify: `web/app/chat/page.tsx`

- [ ] **Step 1: Create retrieval inspector**

`web/components/retrieval/retrieval-inspector.tsx`:

```tsx
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";
import { EmptyState } from "@/components/ui/empty-state";
import { searchKnowledge } from "@/lib/api";
import type { Domain, SearchResult } from "@/lib/types";

export function RetrievalInspector() {
  const [query, setQuery] = useState("");
  const [domain, setDomain] = useState<Domain | "">("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function runSearch() {
    if (!query.trim()) return;
    setPending(true);
    setError("");
    try {
      const response = await searchKnowledge(query, domain, 5);
      setResults(response.results);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Search failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <Panel>
      <div className="grid gap-3 md:grid-cols-[1fr_180px_auto]">
        <input className="rounded-2xl bg-white/[0.06] px-4 py-3 text-sm text-white ring-1 ring-white/10" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="ふるさと納税 / permanent residency" />
        <select className="rounded-2xl bg-white/[0.06] px-4 py-3 text-sm text-white ring-1 ring-white/10" value={domain} onChange={(event) => setDomain(event.target.value as Domain | "")}>
          <option value="">all</option>
          <option value="tax">tax</option>
          <option value="visa">visa</option>
          <option value="ward_office">ward_office</option>
        </select>
        <Button disabled={pending} onClick={runSearch}>Search</Button>
      </div>
      {error ? <p className="mt-4 rounded-2xl bg-red-500/10 p-3 text-sm text-red-200">{error}</p> : null}
      <div className="mt-5 grid gap-3">
        {pending ? <p className="text-sm text-[var(--text-muted)]">Retrieving cited chunks...</p> : null}
        {!pending && results.length === 0 ? <EmptyState title="No retrieval yet" body="Run a query to inspect hybrid RAG results." /> : null}
        {results.map((result) => (
          <article key={`${result.rank}-${result.citation}`} className="rounded-2xl bg-white/[0.04] p-4 ring-1 ring-white/10">
            <p className="font-mono text-xs text-[var(--accent)]">#{result.rank} {result.domain} score {result.score}</p>
            <h3 className="mt-2 text-sm font-medium">{result.citation}</h3>
            <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">{result.snippet}</p>
          </article>
        ))}
      </div>
    </Panel>
  );
}
```

- [ ] **Step 2: Add inspector to chat page**

Modify `web/app/chat/page.tsx`:

```tsx
import { ChatConsole } from "@/components/chat/chat-console";
import { RetrievalInspector } from "@/components/retrieval/retrieval-inspector";
import { PublicShell } from "@/components/shell/public-shell";

export default function ChatPage() {
  return (
    <PublicShell>
      <section className="mx-auto max-w-7xl px-6 py-12">
        <div className="mb-8">
          <h1 className="text-4xl font-semibold tracking-[-0.05em] md:text-6xl">Ask JapanLife.</h1>
          <p className="mt-4 max-w-[62ch] text-[var(--text-muted)]">
            Routed specialist agents answer with deterministic tools and cited retrieval.
          </p>
        </div>
        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <ChatConsole />
          <RetrievalInspector />
        </div>
      </section>
    </PublicShell>
  );
}
```

- [ ] **Step 3: Build**

Run:

```bash
cd web
npm run build
```

Expected: build succeeds.

- [ ] **Step 4: Commit**

```bash
git add web/components/retrieval/retrieval-inspector.tsx web/app/chat/page.tsx
git commit -m "feat(web): add retrieval inspector to chat product surface" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Task 7: Documentation and Final Verification

**Files:**
- Modify: `README.md`
- Modify: `Makefile`
- Modify: `docs/backend-engineering.md`

- [ ] **Step 1: Update Makefile**

Add:

```make
web-install:
	cd web && npm install

web-dev:
	cd web && npm run dev

web-build:
	cd web && npm run build
```

- [ ] **Step 2: Update README frontend section**

Replace the Streamlit-primary demo section with:

```markdown
## Frontend

The product frontend is a Next.js app in `web/`:

- `/` - product landing page
- `/chat` - user-facing Agent chat and retrieval inspector
- `/admin/knowledge` - knowledge-base admin console

```bash
make up
make web-install
make web-dev
```

Set `NEXT_PUBLIC_API_URL` if the FastAPI backend is not at `http://localhost:8000`.
Set `ADMIN_TOKEN` to protect `/admin/*` in non-local environments.
```

- [ ] **Step 3: Update backend docs**

In `docs/backend-engineering.md`, add:

```markdown
## Product frontend

The primary frontend is a Next.js App Router project under `web/`. The user-facing `/chat`
surface is separate from `/admin/knowledge`, which manages Git-based Markdown knowledge files.
The admin route calls FastAPI `/admin/knowledge/*` endpoints for CRUD, validation, chunk preview,
and manifest-backed stale chunk cleanup.
```

- [ ] **Step 4: Run full verification**

Run:

```bash
poetry run pytest -q tests/test_knowledge_admin.py tests/test_stale_cleanup.py tests/test_knowledge_admin_api.py
make test
cd web && npm run build
```

Expected: all backend tests pass and Next.js build succeeds.

- [ ] **Step 5: Commit**

```bash
git add README.md Makefile docs/backend-engineering.md
git commit -m "docs: document production Next.js frontend" -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## Self-Review

**Spec coverage:** The plan replaces Streamlit with a production Next.js frontend, separates `/chat` and `/admin/knowledge`, keeps the Git-based admin backend, adds stale cleanup, and documents the new workflow.

**Placeholder scan:** No placeholder tasks remain. Backend implementation references the already-committed detailed backend admin plan to avoid duplicating 700 lines of exact code while preserving task boundaries.

**Type consistency:** Frontend types use `Domain`, `KnowledgeDoc`, `KnowledgeDocPayload`, `SearchResult`, and `IngestJob` consistently across API client and UI components.

**Taste-skill compliance:** The plan declares the design read, dials, visual constraints, anti-slop rules, route separation, loading/error/empty states, reduced-motion guardrails, and production UI requirements.

