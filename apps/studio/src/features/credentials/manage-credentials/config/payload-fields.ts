import type { CredentialType } from "@/entities/credential";

export interface PayloadFieldConfig {
  defaultValue?: string;
  key: string;
  kind: "text" | "password" | "number";
  label: string;
  placeholder?: string;
  required?: boolean;
}

export const PAYLOAD_FIELDS: Record<CredentialType, PayloadFieldConfig[]> = {
  telegram_bot: [
    {
      key: "bot_token",
      label: "Bot token",
      kind: "password",
      placeholder: "123456:ABC-…",
      required: true,
    },
  ],
  slack_webhook: [
    {
      key: "webhook_url",
      label: "Webhook URL",
      kind: "password",
      placeholder: "https://hooks.slack.com/services/…",
      required: true,
    },
  ],
  discord_webhook: [
    {
      key: "webhook_url",
      label: "Webhook URL",
      kind: "password",
      placeholder: "https://discord.com/api/webhooks/…",
      required: true,
    },
  ],
  smtp: [
    { key: "host", label: "Host", kind: "text", placeholder: "smtp.example.com", required: true },
    { key: "port", label: "Port", kind: "number", defaultValue: "587" },
    { key: "username", label: "Username", kind: "text" },
    { key: "password", label: "Password", kind: "password" },
    { key: "from_address", label: "From address", kind: "text", placeholder: "alerts@example.com" },
  ],
  mqtt: [
    { key: "host", label: "Host", kind: "text", placeholder: "broker.example.com", required: true },
    { key: "port", label: "Port", kind: "number", defaultValue: "1883" },
    { key: "username", label: "Username", kind: "text" },
    { key: "password", label: "Password", kind: "password" },
  ],
};

export function emptyPayloadDraft(type: CredentialType): Record<string, string> {
  return Object.fromEntries(PAYLOAD_FIELDS[type].map((field) => [field.key, field.defaultValue ?? ""]));
}

export function buildPayload(type: CredentialType, draft: Record<string, string>): Record<string, unknown> {
  const payload: Record<string, unknown> = {};

  for (const field of PAYLOAD_FIELDS[type]) {
    const value = (draft[field.key] ?? "").trim();

    if (value === "") {
      continue;
    }

    payload[field.key] = field.kind === "number" ? Number(value) : value;
  }

  return payload;
}
