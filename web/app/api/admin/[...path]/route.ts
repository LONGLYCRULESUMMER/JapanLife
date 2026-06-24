import { NextRequest, NextResponse } from "next/server";
import { proxyToBackend, safeBackendUrl } from "@/lib/server/proxy";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

async function proxyAdmin(request: NextRequest, context: RouteContext) {
  const adminToken = process.env.ADMIN_API_KEY;
  const uiAdminToken = process.env.ADMIN_TOKEN;
  if (!adminToken) {
    return new NextResponse("Admin API key is not configured.", { status: 503 });
  }
  if (!uiAdminToken) {
    return new NextResponse("Admin token is not configured.", { status: 503 });
  }
  const provided = request.headers.get("x-admin-token") ?? request.cookies.get("admin_token")?.value;
  if (provided !== uiAdminToken) {
    return new NextResponse("Admin token required.", { status: 401 });
  }

  const { path } = await context.params;
  const targetUrl = safeBackendUrl("/admin", path, request.nextUrl.search);
  if (!targetUrl) {
    return new NextResponse("Invalid proxy path.", { status: 400 });
  }

  return proxyToBackend(request, targetUrl, { "x-admin-token": adminToken });
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxyAdmin(request, context);
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxyAdmin(request, context);
}

export async function PUT(request: NextRequest, context: RouteContext) {
  return proxyAdmin(request, context);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxyAdmin(request, context);
}
