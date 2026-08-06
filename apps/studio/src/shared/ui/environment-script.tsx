import { connection } from "next/server";
import { readRuntimeEnvironment } from "../config/environment.server";

export async function EnvironmentScript() {
  await connection();

  const runtimeEnvironment = readRuntimeEnvironment();

  return (
    <script
      // biome-ignore lint/security/noDangerouslySetInnerHtml: serializing trusted server-side config for the client
      dangerouslySetInnerHTML={{
        __html: `window.__ENVIRONMENT=${JSON.stringify(runtimeEnvironment).replaceAll("<", "\\u003c")};`,
      }}
      id="runtime-environment"
    />
  );
}
