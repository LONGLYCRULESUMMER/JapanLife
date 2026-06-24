"use client";

import { ArrowCounterClockwise, PaperPlaneTilt, WarningCircle } from "@phosphor-icons/react";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Panel } from "@/components/ui/panel";
import { SkeletonText } from "@/components/ui/skeleton";
import { streamChat } from "@/lib/api";
import type { ChatMessage, ChatStreamEvent, Domain } from "@/lib/types";

type ChatConsoleProps = {
  initialThreadId?: string | null;
};

type SubmitOptions = {
  retry?: boolean;
};

const domainLabels: Record<Domain, string> = {
  tax: "Tax",
  visa: "Visa",
  ward_office: "Ward office",
};

const emptyPrompts = [
  "When is the tax filing deadline?",
  "What documents support permanent residency?",
  "How do I update my address at city hall?",
];

function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

function shortThreadId(threadId: string): string {
  return threadId.length > 12 ? `${threadId.slice(0, 8)}...${threadId.slice(-4)}` : threadId;
}

function appendAssistantToken(messages: ChatMessage[], text: string): ChatMessage[] {
  const next = [...messages];
  const last = next[next.length - 1];
  if (!last || last.role !== "assistant") return next;
  next[next.length - 1] = { ...last, content: `${last.content}${text}` };
  return next;
}

function updateLastAssistant(messages: ChatMessage[], update: Partial<ChatMessage>): ChatMessage[] {
  const next = [...messages];
  const last = next[next.length - 1];
  if (!last || last.role !== "assistant") return next;
  next[next.length - 1] = { ...last, ...update };
  return next;
}

function removeEmptyPendingAssistant(messages: ChatMessage[]): ChatMessage[] {
  const last = messages[messages.length - 1];
  if (!last || last.role !== "assistant" || last.content || last.citations?.length || last.route) return messages;
  return messages.slice(0, -1);
}

function removeFailedTurn(messages: ChatMessage[], prompt: string): ChatMessage[] {
  const next = [...messages];
  const last = next[next.length - 1];

  if (last?.role === "assistant") {
    next.pop();
  }

  const prior = next[next.length - 1];
  if (prior?.role === "user" && prior.content === prompt) {
    next.pop();
  }

  return next;
}

function isAbortError(error: unknown): boolean {
  return typeof error === "object" && error !== null && "name" in error && error.name === "AbortError";
}

export function ChatConsole({ initialThreadId = null }: ChatConsoleProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [threadId, setThreadId] = useState<string | null>(initialThreadId);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [lastPrompt, setLastPrompt] = useState("");
  const [activeTool, setActiveTool] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages, pending, error, activeTool]);

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  async function submitMessage(message: string, options: SubmitOptions = {}) {
    const trimmed = message.trim();
    if (!trimmed || pending) return;

    const activeThreadId = threadId;
    const controller = new AbortController();
    abortControllerRef.current = controller;
    setInput("");
    setError("");
    setLastPrompt(trimmed);
    setActiveTool(null);
    setPending(true);
    setMessages((prev) => [
      ...(options.retry ? removeFailedTurn(prev, trimmed) : prev),
      { role: "user", content: trimmed },
      { role: "assistant", content: "" },
    ]);

    try {
      for await (const chunk of streamChat(trimmed, activeThreadId, controller.signal)) {
        handleStreamEvent(chunk);
      }
    } catch (exc) {
      if (isAbortError(exc)) return;
      setError(exc instanceof Error ? exc.message : "The assistant stream failed.");
      setMessages(removeEmptyPendingAssistant);
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
      }
      setActiveTool(null);
      setPending(false);
    }
  }

  function handleStreamEvent(chunk: ChatStreamEvent) {
    if (chunk.event === "token") {
      setActiveTool(null);
      setMessages((prev) => appendAssistantToken(prev, chunk.data.text));
      return;
    }

    if (chunk.event === "route") {
      setMessages((prev) => updateLastAssistant(prev, { route: chunk.data.route }));
      return;
    }

    if (chunk.event === "tool") {
      setActiveTool(chunk.data.name || "tool");
      setMessages((prev) => updateLastAssistant(prev, { content: "", citations: [] }));
      return;
    }

    if (chunk.event === "done") {
      if (chunk.data.thread_id) setThreadId(chunk.data.thread_id);
      setActiveTool(null);
      setMessages((prev) => updateLastAssistant(prev, { citations: chunk.data.citations }));
      return;
    }

    if (chunk.event === "error") {
      setActiveTool(null);
      setError(chunk.data.error);
      setMessages(removeEmptyPendingAssistant);
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submitMessage(input);
  }

  const hasMessages = messages.length > 0;
  const activeRoute = [...messages].reverse().find((message) => message.route)?.route ?? null;

  return (
    <Panel className="grid min-h-[68dvh] grid-rows-[auto_minmax(0,1fr)_auto] gap-5 p-4 sm:p-5 lg:min-h-[70dvh]" variant="elevated">
      <div className="flex flex-col gap-3 border-b border-white/10 pb-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold tracking-[-0.04em] text-[#eff8f3]">Assistant console</h2>
          <p className="mt-1 text-sm leading-6 text-[var(--text-muted)]">
            Streamed routing, answer text, and citations in one thread.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          {activeRoute ? <Badge variant="accent">Route: {domainLabels[activeRoute]}</Badge> : <Badge variant="neutral">No route yet</Badge>}
          {activeTool ? <Badge variant="accent">Checking sources</Badge> : null}
          {threadId ? <Badge variant="neutral">Thread {shortThreadId(threadId)}</Badge> : <Badge variant="neutral">New thread</Badge>}
        </div>
      </div>

      <div className="min-h-0 overflow-y-auto pr-1">
        {!hasMessages ? (
          <div className="grid min-h-full place-items-center py-10 text-center">
            <div className="max-w-xl">
              <p className="font-mono text-sm text-[var(--accent)]">empty thread</p>
              <h3 className="mt-3 text-3xl font-semibold tracking-[-0.05em] text-[#eff8f3]">Start with one Japan procedure.</h3>
              <p className="mt-3 text-sm leading-6 text-[var(--text-muted)]">
                Ask in English or Japanese. The assistant will pick a route and cite matching knowledge.
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {emptyPrompts.map((prompt) => (
                  <button
                    className="rounded-full bg-white/[0.06] px-4 py-2 text-left text-xs font-medium text-[#dce8e2] ring-1 ring-white/10 transition-colors hover:bg-white/[0.1] focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--background)]"
                    key={prompt}
                    onClick={() => setInput(prompt)}
                    type="button"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((message, index) => {
              const isUser = message.role === "user";
              const isPendingAssistant = pending && index === messages.length - 1 && message.role === "assistant" && !message.content;

              return (
                <article
                  className={cx(
                    "rounded-3xl p-4 ring-1",
                    isUser
                      ? "ml-auto max-w-2xl bg-[var(--accent)] text-[#07110f] ring-[var(--accent)]/40"
                      : "max-w-3xl bg-white/[0.055] text-[#eff8f3] ring-white/10",
                  )}
                  key={`${message.role}-${index}-${message.content.slice(0, 18)}`}
                >
                  <div className="mb-2 flex flex-wrap items-center gap-2">
                    <span className={cx("font-mono text-xs", isUser ? "text-[#123027]" : "text-[var(--text-muted)]")}>
                      {isUser ? "you" : "assistant"}
                    </span>
                    {!isUser && message.route ? <Badge variant="accent">Route: {domainLabels[message.route]}</Badge> : null}
                  </div>

                  {isPendingAssistant ? (
                    <div aria-label="Assistant response loading" role="status">
                      <p className="mb-3 font-mono text-xs text-[var(--accent)]">
                        {activeTool ? "Checking sources" : "Thinking"}
                      </p>
                      <SkeletonText lines={3} />
                    </div>
                  ) : (
                    <p className="whitespace-pre-wrap text-sm leading-7">{message.content}</p>
                  )}

                  {!isUser && message.citations?.length ? (
                    <div className="mt-4 border-t border-white/10 pt-3">
                      <p className="font-mono text-xs text-[var(--accent)]">Citations</p>
                      <ol className="mt-2 grid gap-2 text-xs leading-5 text-[var(--text-muted)]">
                        {message.citations.map((citation) => (
                          <li className="rounded-2xl bg-[#07110f]/45 px-3 py-2 ring-1 ring-white/10" key={citation}>
                            {citation}
                          </li>
                        ))}
                      </ol>
                    </div>
                  ) : null}
                </article>
              );
            })}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      <div className="grid gap-3">
        {error ? (
          <div className="flex flex-col gap-3 rounded-3xl bg-[var(--danger)]/[0.09] p-4 text-sm text-[#ffd8d8] ring-1 ring-[var(--danger)]/25 sm:flex-row sm:items-center sm:justify-between" role="alert">
            <div className="flex gap-3">
              <WarningCircle aria-hidden="true" className="mt-0.5 shrink-0 text-[#ffb3b3]" size={20} weight="duotone" />
              <p>{error}</p>
            </div>
            {lastPrompt ? (
              <Button disabled={pending} onClick={() => void submitMessage(lastPrompt, { retry: true })} size="sm" variant="secondary">
                <ArrowCounterClockwise aria-hidden="true" size={16} weight="bold" />
                Retry
              </Button>
            ) : null}
          </div>
        ) : null}

        <form className="grid gap-2" onSubmit={handleSubmit}>
          <label className="text-sm font-medium text-[#eff8f3]" htmlFor="chat-message">
            Message
          </label>
          <div className="flex flex-col gap-3 sm:flex-row">
            <input
              autoComplete="off"
              className="min-h-12 min-w-0 flex-1 rounded-full bg-white/[0.06] px-5 py-3 text-sm text-[#eff8f3] ring-1 ring-white/12 transition-[background-color,box-shadow] placeholder:text-[#789089] hover:bg-white/[0.08] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:ring-offset-2 focus:ring-offset-[var(--background)] disabled:cursor-not-allowed disabled:opacity-60"
              disabled={pending}
              id="chat-message"
              onChange={(event) => setInput(event.target.value)}
              placeholder="Ask about tax filing deadlines"
              value={input}
            />
            <Button className="sm:min-w-32" disabled={!input.trim()} isLoading={pending} loadingLabel="Sending" type="submit">
              <PaperPlaneTilt aria-hidden="true" size={18} weight="bold" />
              Send
            </Button>
          </div>
        </form>
      </div>
    </Panel>
  );
}
