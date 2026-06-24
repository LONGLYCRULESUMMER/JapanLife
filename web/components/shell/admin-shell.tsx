import Link from "next/link";
import type { ReactNode } from "react";

const navLinks = [
  { href: "/chat", label: "Chat" },
  { href: "/admin/knowledge", label: "Knowledge" },
];

export function AdminShell({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-[100dvh] overflow-x-clip">
      <a
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-[var(--accent)] focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-[#07110f] focus:shadow-[0_18px_50px_rgb(0_0_0/0.28)]"
        href="#main"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-40 border-b border-white/10 bg-[#07110f]/92 backdrop-blur-xl" style={{ maxHeight: 80 }}>
        <div className="mx-auto flex min-h-14 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
          <div className="inline-flex items-center gap-2.5">
            <span className="grid size-7 place-items-center rounded-md bg-[var(--accent)] text-[10px] font-bold text-[#07110f] shadow-[inset_0_1px_0_rgb(255_255_255/0.35)]">
              JL
            </span>
            <span className="text-sm font-semibold tracking-[-0.02em] text-[#eff8f3]">Admin</span>
            <span className="rounded-full bg-[var(--accent)]/10 px-2 py-0.5 text-xs font-medium text-[var(--accent)] ring-1 ring-[var(--accent)]/20">
              Console
            </span>
          </div>
          <nav
            aria-label="Admin navigation"
            className="flex min-w-0 flex-1 items-center justify-end gap-1 overflow-x-auto text-sm text-[var(--text-muted)] sm:gap-2"
          >
            {navLinks.map((link) => (
              <Link
                className="whitespace-nowrap rounded-full px-3 py-2 font-medium outline-none transition-[background-color,color] hover:bg-white/[0.08] hover:text-[#eff8f3] focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--background)] sm:px-4"
                href={link.href}
                key={link.href}
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main id="main" tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}
