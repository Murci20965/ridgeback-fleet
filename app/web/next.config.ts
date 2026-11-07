import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Tailwind's Turbopack loader. Without it, the CSS has no utility classes.
  turbopack: {
    rules: {
      "*.css": { loaders: ["@tailwindcss/turbopack"] },
    },
  },
  // In production Vercel routes /api/v1 to FastAPI. This does the same for local development.
  async rewrites() {
    if (process.env.NODE_ENV !== "development") return [];
    const api = process.env.API_URL ?? "http://localhost:8000";
    return [{ source: "/api/v1/:path*", destination: `${api}/api/v1/:path*` }];
  },
};

export default nextConfig;
