import { API_BASE_URL } from "./config";
import type {
  ChatRequest,
  ChatResponse,
  ChatStreamEvent,
  ChunkPreview,
  ConversationDetail,
  ConversationSummary,
  Domain,
  HealthResponse,
  IngestJob,
  KnowledgeDoc,
  KnowledgeDocPayload,
  KnowledgeValidation,
  SearchResponse,
} from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail || `Request failed with status ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

function apiUrl(path: string): string {
  if (/^https?:\/\//.test(path)) return path;
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

function hasJsonBody(init?: RequestInit): boolean {
  if (!init?.body) return false;
  return !(typeof FormData !== "undefined" && init.body instanceof FormData);
}

function withDefaultHeaders(init?: RequestInit): RequestInit {
  const headers = new Headers(init?.headers);

  if (hasJsonBody(init) && !headers.has("content-type")) {
    headers.set("content-type", "application/json");
  }

  return {
    cache: "no-store",
    ...init,
    headers,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringValue(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function stringArrayValue(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function domainValue(value: unknown): Domain | null {
  return value === "tax" || value === "visa" || value === "ward_office" ? value : null;
}

async function responseDetail(response: Response): Promise<string> {
  const contentType = response.headers.get("content-type") ?? "";

  if (contentType.includes("application/json")) {
    try {
      const payload: unknown = await response.json();
      if (isRecord(payload)) {
        const detail = payload.detail;
        if (typeof detail === "string") return detail;
        if (Array.isArray(detail)) return detail.map((item) => JSON.stringify(item)).join(", ");
        const message = payload.message;
        if (typeof message === "string") return message;
      }
    } catch {
      return response.statusText;
    }
  }

  const text = await response.text();
  return text || response.statusText;
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), withDefaultHeaders(init));

  if (!response.ok) {
    throw new ApiError(response.status, await responseDetail(response));
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function jsonRequestInit(method: "POST" | "PUT" | "PATCH" | "DELETE", payload?: unknown): RequestInit {
  return {
    method,
    body: payload === undefined ? undefined : JSON.stringify(payload),
  };
}

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export async function sendChat(message: string, threadId?: string | null): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", jsonRequestInit("POST", { message, thread_id: threadId || undefined }));
}

export async function listConversations(limit = 30): Promise<{ conversations: ConversationSummary[] }> {
  const params = new URLSearchParams({ limit: String(limit) });
  return request<{ conversations: ConversationSummary[] }>(`/conversations?${params.toString()}`);
}

export async function getConversation(threadId: string): Promise<ConversationDetail> {
  return request<ConversationDetail>(`/conversations/${encodeURIComponent(threadId)}`);
}

export async function deleteConversation(threadId: string): Promise<{ deleted: string }> {
  return request<{ deleted: string }>(`/conversations/${encodeURIComponent(threadId)}`, jsonRequestInit("DELETE"));
}

export async function searchKnowledge(query: string, domain: Domain | "", topK: number): Promise<SearchResponse> {
  const params = new URLSearchParams({ q: query, top_k: String(topK) });
  if (domain) params.set("domain", domain);
  return request<SearchResponse>(`/search?${params.toString()}`);
}

export async function listKnowledgeDocs(domain: Domain | "", q: string): Promise<{ documents: KnowledgeDoc[] }> {
  const params = new URLSearchParams();
  if (domain) params.set("domain", domain);
  if (q) params.set("q", q);
  const query = params.toString();
  return request<{ documents: KnowledgeDoc[] }>(`/admin/knowledge/docs${query ? `?${query}` : ""}`);
}

function docPath(docId: string): string {
  const [domain, filename, ...rest] = docId.split("/");
  if (!domain || !filename || rest.length > 0) {
    throw new Error("Document id must be domain/filename.");
  }
  return `${encodeURIComponent(domain)}/${encodeURIComponent(filename)}`;
}

export async function getKnowledgeDoc(docId: string): Promise<KnowledgeDoc> {
  return request<KnowledgeDoc>(`/admin/knowledge/docs/${docPath(docId)}`);
}

export async function createKnowledgeDoc(payload: KnowledgeDocPayload): Promise<KnowledgeDoc> {
  return request<KnowledgeDoc>("/admin/knowledge/docs", jsonRequestInit("POST", payload));
}

export async function updateKnowledgeDoc(docId: string, payload: KnowledgeDocPayload): Promise<KnowledgeDoc> {
  return request<KnowledgeDoc>(`/admin/knowledge/docs/${docPath(docId)}`, jsonRequestInit("PUT", payload));
}

export async function deleteKnowledgeDoc(docId: string): Promise<KnowledgeDoc | undefined> {
  return request<KnowledgeDoc | undefined>(`/admin/knowledge/docs/${docPath(docId)}`, jsonRequestInit("DELETE"));
}

export async function validateKnowledgeDoc(payload: KnowledgeDocPayload): Promise<KnowledgeValidation> {
  return request<KnowledgeValidation>("/admin/knowledge/validate", jsonRequestInit("POST", payload));
}

export async function previewChunks(docId: string): Promise<{ chunks: ChunkPreview[] }> {
  return request<{ chunks: ChunkPreview[] }>(`/admin/knowledge/docs/${docPath(docId)}/chunks`);
}

export async function triggerKnowledgeReindex(): Promise<IngestJob> {
  return request<IngestJob>("/admin/knowledge/reindex", jsonRequestInit("POST"));
}

function parseJsonRecord(data: string): Record<string, unknown> {
  try {
    const parsed: unknown = JSON.parse(data);
    return isRecord(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

function toChatStreamEvent(event: string, data: string): ChatStreamEvent | null {
  const payload = parseJsonRecord(data);

  switch (event) {
    case "route": {
      const route = domainValue(payload.route);
      return route ? { event: "route", data: { route } } : null;
    }
    case "tool":
      return { event: "tool", data: { name: stringValue(payload.name, "tool") } };
    case "token":
      return { event: "token", data: { text: stringValue(payload.text) } };
    case "done":
      return {
        event: "done",
        data: {
          thread_id: stringValue(payload.thread_id),
          citations: stringArrayValue(payload.citations),
        },
      };
    case "error":
      return { event: "error", data: { error: stringValue(payload.error, "The assistant stream failed.") } };
    default:
      return null;
  }
}

function parseSseBlock(block: string): ChatStreamEvent | null {
  let event = "message";
  const dataLines: string[] = [];

  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }

  if (dataLines.length === 0) return null;
  return toChatStreamEvent(event, dataLines.join("\n"));
}

async function* readSseEvents(response: Response): AsyncGenerator<ChatStreamEvent> {
  if (!response.body) throw new ApiError(response.status, "Stream body is unavailable.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });

    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      const event = parseSseBlock(block.trim());
      if (event) yield event;
    }

    if (done) break;
  }

  const finalEvent = parseSseBlock(buffer.trim());
  if (finalEvent) yield finalEvent;
}

export async function* streamChat(
  messageOrRequest: string | ChatRequest,
  threadId?: string | null,
  signal?: AbortSignal,
): AsyncGenerator<ChatStreamEvent> {
  const payload: ChatRequest =
    typeof messageOrRequest === "string"
      ? { message: messageOrRequest, thread_id: threadId || undefined }
      : messageOrRequest;

  const response = await fetch(
    apiUrl("/chat/stream"),
    withDefaultHeaders({
      method: "POST",
      body: JSON.stringify(payload),
      signal,
    }),
  );

  if (!response.ok) {
    throw new ApiError(response.status, await responseDetail(response));
  }

  yield* readSseEvents(response);
}
