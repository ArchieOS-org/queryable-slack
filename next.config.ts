import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // API rewrites to Python backend
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: '/api/:path*', // Proxy to Python functions
      },
    ]
  },
};

export default nextConfig;
