const BACKEND = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001";

const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
