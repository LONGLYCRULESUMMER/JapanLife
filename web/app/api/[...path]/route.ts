import { NextRequest, NextResponse } from "next/server";
import { proxyToBackend, safeBackendUrl } from "@/lib/server/proxy";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

async function proxyPublic(request: NextRequest, context: RouteContext) {
  const { path } = await context.params;
  if (path[0] === "admin") {
    return new NextResponse("Not found", { status: 404 });
  }

  const targetUrl = safeBackendUrl("", path, request.nextUrl.search);
  if (!targetUrl) {
    return new NextResponse("Invalid proxy path.", { status: 400 });
  }

  return proxyToBackend(request, targetUrl);
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
