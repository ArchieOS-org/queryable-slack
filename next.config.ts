import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // For monorepo file tracing
  outputFileTracingRoot: path.join(__dirname, '../'),
  
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
