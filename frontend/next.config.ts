import type { NextConfig } from "next";

// Inside Docker, the backend is reachable via the service name "backend".
// Outside Docker (local dev), it's on localhost:8000.
const BACKEND_URL = process.env.BACKEND_URL || "http://backend:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
      {
        source: "/storage/:path*",
        destination: `${BACKEND_URL}/storage/:path*`,
      },
    ];
  },
  images: {
    domains: ["localhost", "backend", "images.pexels.com", "oaidalleapiprodscus.blob.core.windows.net"],
  },
};

export default nextConfig;
