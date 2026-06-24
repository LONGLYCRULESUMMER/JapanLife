import { ChatConsole } from "@/components/chat/chat-console";
import { RetrievalInspector } from "@/components/retrieval/retrieval-inspector";
import { PublicShell } from "@/components/shell/public-shell";

export default function ChatPage() {
  return (
    <PublicShell>
      <section className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:py-12">
        <div className="mb-8 max-w-3xl">
          <p className="font-mono text-sm text-[var(--accent)]">specialist agent chat</p>
          <h1 className="mt-3 text-4xl font-semibold tracking-[-0.05em] text-[#eff8f3] text-balance md:text-6xl">
            Ask JapanLife.
          </h1>
          <p className="mt-4 max-w-[58ch] text-base leading-7 text-[var(--text-muted)]">
            Routed specialist agents answer with deterministic tools, curated retrieval, and citations.
          </p>
        </div>
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
          <ChatConsole />
          <RetrievalInspector />
        </div>
      </section>
    </PublicShell>
  );
}
