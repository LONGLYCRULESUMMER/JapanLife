import { NextRequest, NextResponse } from "next/server";

const PUBLIC_PATHS = ["/admin/login", "/api/admin/session"];

function tokenMatches(provided: string | undefined, expected: string): boolean {
  if (!provided) return false;
  let mismatch = provided.length ^ expected.length;
  for (let index = 0; index < expected.length; index += 1) {
    mismatch |= expected.charCodeAt(index) ^ (provided.charCodeAt(index) || 0);
  }
  return mismatch === 0;
}

export function middleware(request: NextRequest) {
  const path = request.nextUrl.pathname;
  if (!path.startsWith("/admin") && !path.startsWith("/api/admin")) {
    return NextResponse.next();
  }

  // Allow public admin paths without a token
  if (PUBLIC_PATHS.some((p) => path === p || path.startsWith(`${p}/`))) {
    return NextResponse.next();
  }

  const adminToken = process.env.ADMIN_TOKEN;
  if (!adminToken) {
    return new NextResponse("Admin token is not configured.", { status: 503 });
  }

  const provided = request.headers.get("x-admin-token") ?? request.cookies.get("admin_token")?.value;
  if (!tokenMatches(provided, adminToken)) {
    // Redirect browser requests to login page; return 401 for API requests
    if (path.startsWith("/api/")) {
      return new NextResponse("Admin token required.", { status: 401 });
    }
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/admin/login";
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*", "/api/admin/:path*"],
};
