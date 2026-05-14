import type { NextConfig } from "next";

function stripSlash(v: string | undefined): string {
  return (v ?? "").replace(/\/$/, "");
}

/**
 * Proxy: browser → Next (`fetch("/api/…")`) → this URL (uvicorn on the Pi).
 * Set only `ROBOT_API_REWRITE_TARGET` here — not `NEXT_PUBLIC_*` (those are for direct browser→Pi in api.ts).
 * Use http://<PI_LAN_IP>:8000, not 127.0.0.1 on the dev laptop unless the API runs on the same machine.
 */
const rewriteTarget = stripSlash(process.env.ROBOT_API_REWRITE_TARGET);

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    if (!rewriteTarget) return [];
    return [{ source: "/api/:path*", destination: `${rewriteTarget}/api/:path*` }];
  },
};

export default nextConfig;
