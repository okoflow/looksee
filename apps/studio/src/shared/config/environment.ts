import { z } from "zod";

const TRAILING_SLASHES = /\/+$/;

const httpUrlSchema = z.url({ protocol: /^https?$/ }).transform((value) => {
  return value.replace(TRAILING_SLASHES, "");
});

const webSocketUrlSchema = z.url({ protocol: /^wss?$/ }).transform((value) => {
  return value.replace(TRAILING_SLASHES, "");
});

export const publicRuntimeEnvironmentSchema = z.object({
  apiUrl: httpUrlSchema,
  docsUrl: httpUrlSchema,
  githubUrl: httpUrlSchema,
  mediamtxWebRTCUrl: httpUrlSchema,
  webSocketUrl: webSocketUrlSchema,
});

export type PublicRuntimeEnvironment = z.infer<typeof publicRuntimeEnvironmentSchema>;

declare global {
  interface Window {
    __ENVIRONMENT?: PublicRuntimeEnvironment;
  }
}

export const runtimeEnvironmentDefaults = publicRuntimeEnvironmentSchema.parse({
  apiUrl: "http://localhost:8000",
  docsUrl: "http://localhost:3002/docs",
  githubUrl: "https://github.com/okoflow/looksee",
  webSocketUrl: "ws://localhost:8000",
  mediamtxWebRTCUrl: "http://localhost:8889",
});

const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1"]);

// localhost and 127.0.0.1 are different sites to the browser, so the cookie-bearing
// api/ws hosts must follow the page's loopback host.
function alignLoopbackHost(value: string): string {
  const pageHost = globalThis.window?.location.hostname;

  if (pageHost === undefined || !LOOPBACK_HOSTS.has(pageHost)) {
    return value;
  }

  const url = new URL(value);

  if (!LOOPBACK_HOSTS.has(url.hostname) || url.hostname === pageHost) {
    return value;
  }

  url.hostname = pageHost;

  return url.toString().replace(TRAILING_SLASHES, "");
}

let parsedClientEnvironment: PublicRuntimeEnvironment | null = null;

function clientEnvironment(): PublicRuntimeEnvironment {
  if (parsedClientEnvironment) {
    return parsedClientEnvironment;
  }

  const env = globalThis.window?.__ENVIRONMENT;

  if (env) {
    parsedClientEnvironment = publicRuntimeEnvironmentSchema.parse(env);

    return parsedClientEnvironment;
  }

  return runtimeEnvironmentDefaults;
}

export function getApiUrl(): string {
  return alignLoopbackHost(clientEnvironment().apiUrl);
}

export function getDocsUrl(): string {
  return clientEnvironment().docsUrl;
}

export function getGithubUrl(): string {
  return clientEnvironment().githubUrl;
}

export function getWebSocketUrl(): string {
  return alignLoopbackHost(clientEnvironment().webSocketUrl);
}

export function getMediamtxWebRTCUrl(): string {
  return clientEnvironment().mediamtxWebRTCUrl;
}
