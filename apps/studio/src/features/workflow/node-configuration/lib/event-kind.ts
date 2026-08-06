import { EVENT_KIND_MAX_LENGTH } from "@/entities/inference-model";

const INVALID_EVENT_KIND_CHARACTERS = /[^A-Z0-9]+/gu;
const INVALID_EVENT_KIND_PREFIX = /^[^A-Z]+/u;

export function normalizeEventKind(value: string): string {
  return value
    .toUpperCase()
    .replace(INVALID_EVENT_KIND_CHARACTERS, "_")
    .replace(INVALID_EVENT_KIND_PREFIX, "")
    .slice(0, EVENT_KIND_MAX_LENGTH);
}
