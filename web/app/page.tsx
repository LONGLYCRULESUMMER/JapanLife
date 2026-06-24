import { ArrowUpRight, Database, GitBranch, ShieldCheck } from "@phosphor-icons/react/dist/ssr";
import { PublicShell } from "@/components/shell/public-shell";
import { ButtonLink } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";

const consoleRows = [
  {
    label: "tax",
    text: "Resident tax, deductions, and filing deadlines",
  },
  {
    label: "visa",
    text: "Permanent residency evidence and renewal timing",
  },
  {
    label: "ward office",
    text: "Moving-in forms, address updates, and local steps",
  },
];

const proofPoints = [
  {
    icon: GitBranch,
    title: "Routed answers",
    body: "Questions move to the right specialist before retrieval starts.",
  },
  {
    icon: Database,
    title: "Curated sources",
    body: "Knowledge admins keep Markdown files reviewable and ready to reindex.",
  },
  {
    icon: ShieldCheck,
    title: "Cited output",
    body: "Responses show the source trail instead of hiding the retrieval path.",
  },
];

export default function HomePage() {
  return (
    <PublicShell>
      <section className="mx-auto grid min-h-[calc(100dvh-65px)] max-w-7xl items-center gap-8 px-4 py-10 sm:px-6 lg:grid-cols-[minmax(0,1.04fr)_minmax(360px,0.96fr)] lg:gap-14 lg:py-12">
        <div className="max-w-3xl">
          <p className="font-mono text-sm text-[var(--accent)]">RAG assistant for Japan life</p>
          <h1 className="mt-4 text-5xl font-semibold leading-[0.95] tracking-[-0.07em] text-[#eff8f3] text-balance md:text-6xl lg:text-7xl">
            Japan paperwork, answered with sources.
          </h1>
          <p className="mt-6 max-w-[56ch] text-lg leading-8 text-[var(--text-muted)]">
            Ask tax, visa, and ward-office questions with routed agents, curated knowledge, and citations.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <ButtonLink href="/chat" size="lg">
              Open chat
              <ArrowUpRight aria-hidden="true" size={18} weight="bold" />
            </ButtonLink>
            <ButtonLink href="/admin/knowledge" size="lg" variant="secondary">
              Manage knowledge
            </ButtonLink>
          </div>
        </div>

        <Panel className="relative overflow-hidden p-3 shadow-[0_40px_120px_rgb(0_0_0/0.34)]" variant="elevated">
          <div className="absolute -right-20 -top-20 size-48 rounded-full bg-[var(--accent)]/12 blur-3xl" aria-hidden="true" />
          <div className="relative rounded-[calc(var(--radius-card)-0.5rem)] border border-white/10 bg-[#091411] p-4 shadow-[inset_0_1px_0_rgb(255_255_255/0.06)] sm:p-5">
            <div className="flex items-center justify-between gap-4 border-b border-white/10 pb-4">
              <div>
                <p className="font-mono text-xs text-[var(--accent)]">live route console</p>
                <p className="mt-1 text-sm font-medium text-[#eff8f3]">Question intake and source trace</p>
              </div>
              <div className="rounded-full bg-[var(--accent)]/12 px-3 py-1 font-mono text-xs text-[var(--accent)] ring-1 ring-[var(--accent)]/25">
                ready
              </div>
            </div>

            <div className="mt-5 grid gap-3">
              {consoleRows.map((row, index) => (
                <div
                  className={
                    index === 1
                      ? "ml-7 rounded-3xl bg-[var(--accent)]/[0.09] p-4 ring-1 ring-[var(--accent)]/20"
                      : "rounded-3xl bg-white/[0.045] p-4 ring-1 ring-white/10"
                  }
                  key={row.label}
                >
                  <div className="flex items-center justify-between gap-4">
                    <p className="font-mono text-xs text-[var(--accent)]">{row.label}</p>
                    <p className="font-mono text-[11px] text-[var(--text-muted)]">source trace</p>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-[#eff8f3]">{row.text}</p>
                </div>
              ))}
            </div>

            <div className="mt-5 grid gap-3 rounded-3xl bg-[#0f201b] p-4 ring-1 ring-white/10 sm:grid-cols-[0.8fr_1.2fr]">
              <div>
                <p className="font-mono text-xs text-[var(--accent)]">thread</p>
                <p className="mt-2 text-2xl font-semibold tracking-[-0.04em] text-[#eff8f3]">Cited reply</p>
              </div>
              <p className="text-sm leading-6 text-[var(--text-muted)]">
                The assistant streams route, answer text, and citations so users can see how the response was assembled.
              </p>
            </div>
          </div>
        </Panel>
      </section>

      <section className="mx-auto max-w-7xl px-4 pb-16 sm:px-6 lg:pb-20">
        <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <Panel className="grid gap-4 sm:grid-cols-3" variant="accent">
            {proofPoints.map((item) => {
              const Icon = item.icon;
              return (
                <div className="rounded-3xl bg-[#07110f]/45 p-4 ring-1 ring-white/10" key={item.title}>
                  <Icon aria-hidden="true" className="text-[var(--accent)]" size={24} weight="duotone" />
                  <h2 className="mt-4 text-lg font-semibold tracking-[-0.03em] text-[#eff8f3]">{item.title}</h2>
                  <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">{item.body}</p>
                </div>
              );
            })}
          </Panel>
          <Panel className="flex flex-col justify-between gap-6">
            <div>
              <h2 className="text-3xl font-semibold leading-tight tracking-[-0.05em] text-[#eff8f3]">
                Admin tools stay close to the assistant.
              </h2>
              <p className="mt-4 text-sm leading-6 text-[var(--text-muted)]">
                Review source files, update knowledge, and reindex without leaving the product surface.
              </p>
            </div>
            <ButtonLink className="w-fit" href="/admin/knowledge" variant="secondary">
              Open admin
            </ButtonLink>
          </Panel>
        </div>
      </section>
    </PublicShell>
  );
}
