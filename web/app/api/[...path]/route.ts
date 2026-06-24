import { NextRequest, NextResponse } from "next/server";

const backendBaseUrl = process.env.API_URL ?? "http://localhost:8000";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

async function proxyPublic(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  if (path[0] === "admin") {
    return new NextResponse("Not found", { status: 404 });
  }

  const targetUrl = new URL(`/${path.join("/")}`, backendBaseUrl.replace(/\/+$/, ""));
  targetUrl.search = request.nextUrl.search;

  const headers = new Headers(request.headers);
  headers.delete("host");

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

export async function GET(request: NextRequest, context: RouteContext) {
  return proxyPublic(request, context);
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxyPublic(request, context);
}

export async function PUT(request: NextRequest, context: RouteContext) {
  return proxyPublic(request, context);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxyPublic(request, context);
}
