import { isHTTPError } from "ky";
import { api } from "@/shared/api";
import {
  authStatusSchema,
  type LoginInput,
  type SessionUser,
  type SetupInput,
  sessionUserSchema,
} from "../model/schema";

export async function getAuthStatus() {
  const payload: unknown = await api.get("auth/status").json();

  return authStatusSchema.parse(payload);
}

export async function getSessionUser(): Promise<SessionUser | null> {
  try {
    const payload: unknown = await api.get("auth/me").json();

    return sessionUserSchema.parse(payload);
  } catch (error) {
    if (isHTTPError(error) && error.response.status === 401) {
      return null;
    }

    throw error;
  }
}

export async function login(input: LoginInput) {
  const payload: unknown = await api.post("auth/login", { json: input }).json();

  return sessionUserSchema.parse(payload);
}

export async function setupOwner(input: SetupInput) {
  const payload: unknown = await api.post("auth/setup", { json: input }).json();

  return sessionUserSchema.parse(payload);
}

export async function logout() {
  await api.post("auth/logout");
}
