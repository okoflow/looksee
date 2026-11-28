const DETECTED_SUFFIX = /_DETECTED$/u;
const FIRST_CHARACTER = /^./u;

export function eventKindLabel(kind: string): string {
  const normalized = kind.replace(DETECTED_SUFFIX, "").replaceAll("_", " ").toLowerCase();

  return normalized.replace(FIRST_CHARACTER, (first) => {
    return first.toUpperCase();
  });
}
