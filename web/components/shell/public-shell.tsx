import Link from "next/link";
import type { ReactNode } from "react";
import { ButtonLink } from "@/components/ui/button";

const navLinks = [
  { href: "/chat", label: "Chat" },
  { href: "/admin/knowledge", label: "Knowledge admin" },
];

export function PublicShell({ children }: { children: ReactNode }) {
  return (
    <div className="relative min-h-[100dvh] overflow-x-clip">
      <a
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-[var(--accent)] focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-[#07110f] focus:shadow-[0_18px_50px_rgb(0_0_0/0.28)]"
        href="#main"
      >
        Skip to content
      </a>
      <header className="sticky top-0 z-40 border-b border-white/10 bg-[#07110f]/82 backdrop-blur-xl">
        <div className="mx-auto flex min-h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link
            aria-label="JapanLife home"
            className="group inline-flex items-center gap-2 whitespace-nowrap rounded-full py-2 pr-2 text-sm font-semibold tracking-[-0.02em] text-[#eff8f3] outline-none transition-colors hover:text-[var(--accent)] focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--background)]"
            href="/"
          >
            <span className="grid size-8 place-items-center rounded-full bg-[var(--accent)] text-xs font-bold text-[#07110f] shadow-[inset_0_1px_0_rgb(255_255_255/0.35)]">
              JL
            </span>
            <span>JapanLife</span>
          </Link>

          <nav
            aria-label="Primary"
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
            <ButtonLink className="ml-1" href="/chat" size="sm">
              Ask now
            </ButtonLink>
          </nav>
        </div>
      </header>
      <main id="main" tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}
