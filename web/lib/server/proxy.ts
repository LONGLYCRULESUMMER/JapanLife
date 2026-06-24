import { NextRequest, NextResponse } from "next/server";

export const BACKEND_BASE_URL = process.env.API_URL ?? "http://localhost:8000";

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

const SENSITIVE_HEADERS = new Set(["authorization", "cookie", "host", "x-admin-token"]);

export function safeBackendUrl(prefix: string, path: string[], search: string): URL | null {
  if (path.some((segment) => segment.includes("/") || segment.includes("\\"))) {
    return null;
  }

  const backend = new URL(BACKEND_BASE_URL);
  const encoded = path.map((segment) => encodeURIComponent(segment)).join("/");
  const prefixPath = prefix.replace(/^\/+|\/+$/g, "");
  const pathname = ["", prefixPath, encoded].filter(Boolean).join("/");
  const target = new URL(pathname, backend);
  target.search = search;

  if (target.origin !== backend.origin) {
    return null;
  }

  return target;
}

export async function proxyToBackend(
  request: NextRequest,
  targetUrl: URL,
  extraHeaders: Record<string, string> = {},
) {
  const headers = new Headers();
  for (const [key, value] of request.headers.entries()) {
    const lower = key.toLowerCase();
    if (HOP_BY_HOP_HEADERS.has(lower) || SENSITIVE_HEADERS.has(lower)) {
      continue;
    }
    headers.set(key, value);
  }
  for (const [key, value] of Object.entries(extraHeaders)) {
    headers.set(key, value);
  }

  const response = await fetch(targetUrl, {
    method: request.method,
    headers,
    body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.text(),
    cache: "no-store",
  });

  return new NextResponse(response.body, {
    status: response.status,
    headers: response.headers,
  });
}
