export const DOMAINS = ["tax", "visa", "ward_office"] as const;
export const LANGUAGES = ["en", "ja", "mixed"] as const;

export type Domain = (typeof DOMAINS)[number];
export type KnowledgeLanguage = (typeof LANGUAGES)[number];

export type ChatRole = "user" | "assistant";

export type ChatMessage = {
  role: ChatRole;
  content: string;
  route?: Domain | null;
  citations?: string[];
};

export type ChatRequest = {
  message: string;
  thread_id?: string | null;
};

export type ChatResponse = {
  reply: string;
  citations: string[];
  thread_id: string;
  route?: Domain | null;
};

export type ConversationSummary = {
  thread_id: string;
  title: string;
  turns: number;
};

export type ConversationDetail = {
  thread_id: string;
  messages: ChatMessage[];
};

export type HealthResponse = {
  status: "ok" | "degraded" | string;
  elasticsearch: boolean;
  qdrant: boolean;
};

export type SearchResult = {
  rank: number;
  citation: string;
  score: number;
  domain: Domain;
  snippet: string;
};

export type SearchResponse = {
  query: string;
  domain: Domain | null;
  results: SearchResult[];
};

export type KnowledgeDoc = {
  doc_id: string;
  domain: Domain;
  filename: string;
  doc_title: string;
  source_url: string;
  language: KnowledgeLanguage;
  body?: string;
  needs_reindex?: boolean;
};

export type KnowledgeDocPayload = {
  domain: Domain;
  filename: string;
  doc_title: string;
  source_url: string;
  language: KnowledgeLanguage;
  body: string;
};

export type KnowledgeValidation = {
  valid: boolean;
  errors: string[];
  warnings: string[];
};

export type ChunkMetadata = Record<string, string | number | boolean | null>;

export type ChunkPreview = {
  chunk_id: string;
  text: string;
  metadata: ChunkMetadata;
};

export type IngestJobStatus = "pending" | "running" | "succeeded" | "failed";

export type IngestJob = {
  id: string;
  status: IngestJobStatus;
  created_at?: string;
  started_at?: string | null;
  finished_at?: string | null;
  error?: string | null;
  chunks_indexed?: number | null;
};

export type ChatStreamEvent =
  | { event: "route"; data: { route: Domain } }
  | { event: "tool"; data: { name: string } }
  | { event: "token"; data: { text: string } }
  | { event: "done"; data: { thread_id: string; citations: string[] } }
  | { event: "error"; data: { error: string } };
