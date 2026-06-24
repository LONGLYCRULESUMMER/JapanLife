"use client";

import { MagnifyingGlass } from "@phosphor-icons/react";
import { useState } from "react";
import type { FormEvent } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Panel, PanelDescription, PanelHeader, PanelTitle } from "@/components/ui/panel";
import { SkeletonText } from "@/components/ui/skeleton";
import { searchKnowledge } from "@/lib/api";
import type { Domain, SearchResult } from "@/lib/types";

type SearchPhase = "idle" | "searched";

const domains: Array<{ label: string; value: Domain | "" }> = [
  { label: "all", value: "" },
  { label: "tax", value: "tax" },
  { label: "visa", value: "visa" },
  { label: "ward_office", value: "ward_office" },
];

function scoreLabel(score: number): string {
  return Number.isFinite(score) ? score.toFixed(3) : "n/a";
}

export function RetrievalInspector() {
  const [query, setQuery] = useState("");
  const [domain, setDomain] = useState<Domain | "">("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [phase, setPhase] = useState<SearchPhase>("idle");

  async function runSearch(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery || pending) return;

    setPending(true);
    setError("");
    setResults([]);

    try {
      const response = await searchKnowledge(trimmedQuery, domain, 5);
      setResults(response.results);
      setPhase("searched");
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Search failed.");
      setPhase("searched");
    } finally {
      setPending(false);
    }
  }

  const emptyTitle = phase === "idle" ? "No retrieval yet" : "No matching chunks";
  const emptyBody =
    phase === "idle"
      ? "Run a query to inspect the top cited chunks before sending a chat prompt."
      : "Try another query or widen the domain filter to all.";

  return (
    <Panel className="grid min-h-[68dvh] grid-rows-[auto_auto_minmax(0,1fr)] gap-5 p-4 sm:p-5 lg:min-h-[70dvh]" variant="elevated">
      <PanelHeader className="mb-0 border-b border-white/10 pb-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <PanelTitle>Retrieval inspector</PanelTitle>
            <PanelDescription className="mt-1">
              Query the same knowledge layer the assistant uses and inspect the top 5 cited chunks.
            </PanelDescription>
          </div>
          <Badge variant="accent">Hybrid search</Badge>
        </div>
      </PanelHeader>

      <form className="grid gap-4" onSubmit={runSearch}>
        <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_180px]">
          <div className="grid gap-2">
            <label className="text-sm font-medium text-[#eff8f3]" htmlFor="retrieval-query">
              Query
            </label>
            <input
              aria-describedby="retrieval-query-help"
              autoComplete="off"
              className="min-h-12 w-full rounded-2xl bg-white/[0.06] px-4 py-3 text-sm text-[#eff8f3] ring-1 ring-white/12 transition-[background-color,box-shadow] placeholder:text-[#789089] hover:bg-white/[0.08] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:ring-offset-2 focus:ring-offset-[var(--background)] disabled:cursor-not-allowed disabled:opacity-60"
              disabled={pending}
              id="retrieval-query"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Permanent residency documents"
              type="search"
              value={query}
            />
            <p className="text-xs leading-5 text-[var(--text-muted)]" id="retrieval-query-help">
              Search English or Japanese policy text.
            </p>
          </div>

          <div className="grid gap-2">
            <label className="text-sm font-medium text-[#eff8f3]" htmlFor="retrieval-domain">
              Domain
            </label>
            <select
              aria-describedby="retrieval-domain-help"
              className="min-h-12 w-full rounded-2xl bg-white/[0.06] px-4 py-3 text-sm text-[#eff8f3] ring-1 ring-white/12 transition-[background-color,box-shadow] hover:bg-white/[0.08] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:ring-offset-2 focus:ring-offset-[var(--background)] disabled:cursor-not-allowed disabled:opacity-60"
              disabled={pending}
              id="retrieval-domain"
              onChange={(event) => setDomain(event.target.value as Domain | "")}
              value={domain}
            >
              {domains.map((item) => (
                <option className="bg-[#0d1815] text-[#eff8f3]" key={item.label} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
            <p className="text-xs leading-5 text-[var(--text-muted)]" id="retrieval-domain-help">
              Filter results by source category.
            </p>
          </div>
        </div>

        <Button className="w-full sm:w-fit sm:min-w-32" disabled={!query.trim()} isLoading={pending} loadingLabel="Searching" type="submit">
          <MagnifyingGlass aria-hidden="true" size={18} weight="bold" />
          Search
        </Button>
      </form>

      <div className="min-h-0 overflow-y-auto pr-1" aria-live="polite">
        {error ? (
          <div className="rounded-3xl bg-[var(--danger)]/[0.09] p-4 text-sm text-[#ffd8d8] ring-1 ring-[var(--danger)]/25" role="alert">
            <p className="font-semibold text-[#ffe0e0]">Retrieval failed</p>
            <p className="mt-1 leading-6">{error}</p>
          </div>
        ) : null}

        {pending ? (
          <div className="rounded-3xl bg-white/[0.045] p-4 ring-1 ring-white/10" role="status">
            <p className="mb-3 font-mono text-xs text-[var(--accent)]">Retrieving cited chunks</p>
            <SkeletonText lines={5} />
          </div>
        ) : null}

        {!pending && !error && results.length === 0 ? <EmptyState title={emptyTitle} body={emptyBody} /> : null}

        {!pending && !error && results.length > 0 ? (
          <div className="grid gap-3">
            {results.map((result) => (
              <article className="rounded-3xl bg-white/[0.045] p-4 ring-1 ring-white/10" key={`${result.rank}-${result.citation}`}>
                <dl className="grid grid-cols-3 gap-2 text-xs sm:grid-cols-[72px_1fr_96px]">
                  <div>
                    <dt className="font-mono text-[var(--text-muted)]">rank</dt>
                    <dd className="mt-1 font-semibold text-[var(--accent)]">#{result.rank}</dd>
                  </div>
                  <div>
                    <dt className="font-mono text-[var(--text-muted)]">domain</dt>
                    <dd className="mt-1 font-semibold text-[#eff8f3]">{result.domain}</dd>
                  </div>
                  <div>
                    <dt className="font-mono text-[var(--text-muted)]">score</dt>
                    <dd className="mt-1 font-semibold text-[#eff8f3]">{scoreLabel(result.score)}</dd>
                  </div>
                </dl>
                <h3 className="mt-4 text-sm font-semibold leading-6 text-[#eff8f3]">{result.citation}</h3>
                <p className="mt-2 text-sm leading-6 text-[var(--text-muted)]">{result.snippet}</p>
              </article>
            ))}
          </div>
        ) : null}
      </div>
    </Panel>
  );
}
