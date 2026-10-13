import { NextResponse, type NextRequest } from "next/server";

// Optimistic check only: without a session cookie, protected pages redirect to the login page.
// The real authentication and authorization happen in the API on every request.
const PROTECTED = ["/dashboard", "/onboarding", "/profile", "/cv", "/saved", "/applications", "/assistant", "/notifications",
  "/settings", "/privacy/data", "/employer", "/admin"];

export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  if (PROTECTED.some((p) => pathname === p || pathname.startsWith(`${p}/`)) && !request.cookies.has("tf_session")) {
    const url = new URL("/login", request.url);
    url.searchParams.set("next", pathname + search);
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
