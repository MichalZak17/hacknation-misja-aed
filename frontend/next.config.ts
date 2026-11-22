import type { NextConfig } from "next";

/** Django (backend/). Every /api/* request is proxied there, so the browser stays on one origin. */
const BACKEND_URL = (process.env.BACKEND_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

const nextConfig: NextConfig = {
  // Dev server is reached over Tailscale (100.78.88.117:3001); Next 16 blocks dev assets/HMR from other origins.
  allowedDevOrigins: ["100.78.88.117"],
  cacheComponents: true,
  partialPrefetching: true,
  // Pass paths to Django exactly as requested (no slash added or stripped).
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
