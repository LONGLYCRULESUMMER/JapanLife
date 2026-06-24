import { NextRequest, NextResponse } from "next/server";

export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;
  if (!path.startsWith("/admin") && !path.startsWith("/api/admin")) {
    return NextResponse.next();
  }

  const adminToken = process.env.ADMIN_TOKEN;
  if (!adminToken) {
    return new NextResponse("Admin token is not configured.", { status: 503 });
  }

  const provided = request.headers.get("x-admin-token") ?? request.cookies.get("admin_token")?.value;
  if (provided !== adminToken) {
    return new NextResponse("Admin token required.", { status: 401 });
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*", "/api/admin/:path*"],
};
