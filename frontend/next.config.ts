import type { NextConfig } from "next";

// The browser only talks to this Next.js server; /api/* is forwarded to the FastAPI backend.
// Same origin means first-party HttpOnly cookies and no CORS in the browser.
const backend = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8300";

const nextConfig: NextConfig = {
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  poweredByHeader: false,
  experimental: {
    // The career assistant answers synchronously and a local model can take longer than the 30 s default of the
    // /api rewrite proxy. Keep this above AI_TIMEOUT_SECONDS (300 s by default).
    proxyTimeout: 330_000,
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
