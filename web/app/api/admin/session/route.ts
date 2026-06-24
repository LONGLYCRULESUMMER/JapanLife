import { NextRequest, NextResponse } from "next/server";

function tokenMatches(provided: string, expected: string): boolean {
  let mismatch = provided.length ^ expected.length;
  for (let index = 0; index < expected.length; index += 1) {
    mismatch |= expected.charCodeAt(index) ^ (provided.charCodeAt(index) || 0);
  }
  return mismatch === 0;
}

export async function POST(request: NextRequest) {
  const adminToken = process.env.ADMIN_TOKEN;
  if (!adminToken) {
    return new NextResponse("Admin authentication is not configured.", { status: 503 });
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return new NextResponse("Invalid JSON body.", { status: 400 });
  }

  if (
    typeof body !== "object" ||
    body === null ||
    typeof (body as Record<string, unknown>).token !== "string"
  ) {
    return new NextResponse("Missing token field.", { status: 400 });
  }

  const provided = (body as Record<string, string>).token;
  if (!tokenMatches(provided, adminToken)) {
    return new NextResponse("Invalid token.", { status: 401 });
  }

  const isProduction = process.env.NODE_ENV === "production";
  const maxAge = 8 * 60 * 60; // 8 hours

  const response = new NextResponse(null, { status: 204 });
  response.cookies.set("admin_token", adminToken, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: isProduction,
    maxAge,
  });
  return response;
}
