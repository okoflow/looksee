import { z } from "zod";
import { isoTimestampSchema, uuidSchema } from "@/shared/api";

export const credentialTypeSchema = z.enum(["telegram_bot", "slack_webhook", "discord_webhook", "smtp", "mqtt"]);

export const CREDENTIAL_TYPE_LABELS: Record<CredentialType, string> = {
  telegram_bot: "Telegram bot",
  slack_webhook: "Slack webhook",
  discord_webhook: "Discord webhook",
  smtp: "SMTP",
  mqtt: "MQTT",
};

export const credentialSchema = z.object({
  id: uuidSchema,
  name: z.string(),
  type: credentialTypeSchema,
  summary: z.string(),
  created_at: isoTimestampSchema,
  updated_at: isoTimestampSchema,
});

export const credentialsSchema = z.array(credentialSchema);

export const credentialCreateSchema = z.object({
  name: z.string().min(1).max(128),
  type: credentialTypeSchema,
  payload: z.record(z.string(), z.unknown()),
});

export const credentialUpdateSchema = z.object({
  name: z.string().min(1).max(128).optional(),
  payload: z.record(z.string(), z.unknown()).optional(),
});

export type CredentialType = z.infer<typeof credentialTypeSchema>;
export type Credential = z.infer<typeof credentialSchema>;
export type CredentialCreate = z.infer<typeof credentialCreateSchema>;
export type CredentialUpdate = z.infer<typeof credentialUpdateSchema>;
