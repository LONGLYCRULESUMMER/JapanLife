import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Not found | JapanLife",
};

export default function NotFound() {
  return (
    <main className="flex min-h-[100dvh] items-center justify-center px-6 py-16">
      <section className="max-w-xl rounded-[var(--radius-card)] bg-white/[0.04] p-8 ring-1 ring-white/10 shadow-[0_24px_80px_rgb(0_0_0_/_0.22)]">
        <p className="font-mono text-sm text-[var(--accent)]">404</p>
        <h1 className="mt-4 text-4xl font-semibold tracking-[-0.04em] text-balance">
          This page is not indexed.
        </h1>
        <p className="mt-4 text-pretty leading-7 text-[var(--text-muted)]">
          The route does not exist. Return to the assistant or open the knowledge admin.
        </p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Link
            className="rounded-full bg-[var(--accent)] px-5 py-3 text-center text-sm font-semibold text-[#07110f] transition-transform hover:-translate-y-0.5 active:translate-y-px"
            href="/chat"
          >
            Open chat
          </Link>
          <Link
            className="rounded-full bg-white/10 px-5 py-3 text-center text-sm font-semibold text-white ring-1 ring-white/10 transition-transform hover:-translate-y-0.5 active:translate-y-px"
            href="/admin/knowledge"
          >
            Admin
          </Link>
        </div>
      </section>
    </main>
  );
}
