import "server-only";

import { readServerApiUrl } from "@/shared/config/index.server";
import { authStatusSchema, type SessionUser, sessionUserSchema } from "../model/schema";

export async function fetchServerSessionUser(cookieHeader: string): Promise<SessionUser | null> {
  const response = await fetch(`${readServerApiUrl()}/auth/me`, {
    headers: { cookie: cookieHeader },
    cache: "no-store",
  });

  if (response.status === 401) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`session lookup failed with status ${response.status}`);
  }

  return sessionUserSchema.parse(await response.json());
}

export async function fetchServerAuthStatus() {
  const response = await fetch(`${readServerApiUrl()}/auth/status`, { cache: "no-store" });

  if (!response.ok) {
    throw new Error(`auth status failed with status ${response.status}`);
  }

  return authStatusSchema.parse(await response.json());
}
