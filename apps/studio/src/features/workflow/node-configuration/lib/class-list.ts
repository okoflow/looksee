export function parseClassList(value: string): string[] {
  return value
    .split(",")
    .map((className) => {
      return className.trim();
    })
    .filter(Boolean);
}

export function serializeClassList(classes: readonly string[]): string {
  return classes.join(", ");
}
