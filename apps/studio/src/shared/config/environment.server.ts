import "server-only";

import { z } from "zod";
import {
  type PublicRuntimeEnvironment,
  publicRuntimeEnvironmentSchema,
  runtimeEnvironmentDefaults,
} from "./environment";

const TRAILING_SLASHES = /\/+$/;

const environmentVariableSchema = z
  .string()
  .transform((value) => {
    return value === "" ? undefined : value;
  })
  .optional();

const serverEnvironmentSchema = z.object({
  RUNTIME_API_URL: environmentVariableSchema,
  RUNTIME_DOCS_URL: environmentVariableSchema,
  RUNTIME_GITHUB_URL: environmentVariableSchema,
  RUNTIME_MEDIAMTX_MEDIA_PASSWORD: environmentVariableSchema,
  RUNTIME_MEDIAMTX_MEDIA_USER: environmentVariableSchema,
  RUNTIME_MEDIAMTX_WEBRTC_URL: environmentVariableSchema,
  RUNTIME_WS_URL: environmentVariableSchema,
  SERVER_API_URL: environmentVariableSchema,
});

export function readServerApiUrl(): string {
  const variables = serverEnvironmentSchema.parse(process.env);

  return (variables.SERVER_API_URL ?? variables.RUNTIME_API_URL ?? runtimeEnvironmentDefaults.apiUrl).replace(
    TRAILING_SLASHES,
    ""
  );
}

export function readRuntimeEnvironment(): PublicRuntimeEnvironment {
  const variables = serverEnvironmentSchema.parse(process.env);

  return publicRuntimeEnvironmentSchema.parse({
    apiUrl: variables.RUNTIME_API_URL ?? runtimeEnvironmentDefaults.apiUrl,
    docsUrl: variables.RUNTIME_DOCS_URL ?? runtimeEnvironmentDefaults.docsUrl,
    githubUrl: variables.RUNTIME_GITHUB_URL ?? runtimeEnvironmentDefaults.githubUrl,
    webSocketUrl: variables.RUNTIME_WS_URL ?? runtimeEnvironmentDefaults.webSocketUrl,
    mediamtxWebRTCUrl: variables.RUNTIME_MEDIAMTX_WEBRTC_URL ?? runtimeEnvironmentDefaults.mediamtxWebRTCUrl,
    mediamtxMediaUser: variables.RUNTIME_MEDIAMTX_MEDIA_USER ?? runtimeEnvironmentDefaults.mediamtxMediaUser,
    mediamtxMediaPassword:
      variables.RUNTIME_MEDIAMTX_MEDIA_PASSWORD ?? runtimeEnvironmentDefaults.mediamtxMediaPassword,
  });
}
