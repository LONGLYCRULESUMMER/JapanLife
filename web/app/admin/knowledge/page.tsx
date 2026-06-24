import { PublicShell } from "@/components/shell/public-shell";
import { ButtonLink } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";

export default function KnowledgeAdminPlaceholderPage() {
  return (
    <PublicShell>
      <section className="mx-auto flex min-h-[calc(100dvh-65px)] max-w-5xl items-center px-4 py-16 sm:px-6">
        <Panel className="w-full">
          <p className="font-mono text-sm text-[var(--accent)]">Admin console</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-[-0.05em] md:text-6xl">
            Knowledge admin is being assembled.
          </h1>
          <p className="mt-5 max-w-[64ch] text-[var(--text-muted)]">
            The production admin route is reserved now. The next task replaces this page with document CRUD, validation, chunk preview, and reindex controls.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <ButtonLink href="/chat">Open chat</ButtonLink>
            <ButtonLink href="/" variant="secondary">
              Back home
            </ButtonLink>
          </div>
        </Panel>
      </section>
    </PublicShell>
  );
}
