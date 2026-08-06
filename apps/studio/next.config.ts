import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  reactCompiler: true,
  typedRoutes: true,
  poweredByHeader: false,
  productionBrowserSourceMaps: true,
  experimental: {
    typedEnv: true,
  },
  logging: {
    browserToTerminal: "warn",
  },
};

export default nextConfig;
