import { clamp } from "@/shared/lib/number";
import type { NumericLimits } from "@/entities/workflow";

export function clampToLimits(value: number, limits: NumericLimits): number {
  if (Number.isNaN(value)) {
    return limits.min;
  }

  return clamp(value, limits.min, limits.max);
}

export function parseDraftNumber(draft: string): number | null {
  const trimmed = draft.trim();

  if (trimmed === "") {
    return null;
  }

  const value = Number(trimmed);

  return Number.isFinite(value) ? value : null;
}

export function isDraftNumberValid(value: number | null, limits: NumericLimits, isInteger: boolean): boolean {
  if (value === null) {
    return false;
  }

  if (isInteger && !Number.isInteger(value)) {
    return false;
  }

  return limits.min <= value && value <= limits.max;
}
