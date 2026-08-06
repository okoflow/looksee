import { z } from "zod";
import { isoTimestampSchema, uuidSchema } from "@/shared/api";

export const sessionUserSchema = z.object({
  id: uuidSchema,
  email: z.string(),
  name: z.string(),
  role: z.enum(["owner", "member"]),
  created_at: isoTimestampSchema,
});

export const authStatusSchema = z.object({
  requires_setup: z.boolean(),
});

export const loginSchema = z.object({
  email: z.email(),
  password: z.string().min(1).max(256),
});

export const setupSchema = z.object({
  email: z.email(),
  name: z.string().min(1).max(128),
  password: z
    .string()
    .min(8, "At least 8 characters")
    .max(256)
    .regex(/[0-9]/, "At least one number")
    .regex(/[A-Z]/, "At least one capital letter"),
});

export type SessionUser = z.infer<typeof sessionUserSchema>;
export type AuthStatus = z.infer<typeof authStatusSchema>;
export type LoginInput = z.infer<typeof loginSchema>;
export type SetupInput = z.infer<typeof setupSchema>;
