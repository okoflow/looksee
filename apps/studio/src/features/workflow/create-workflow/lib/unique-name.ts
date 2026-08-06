export function uniqueName(base: string, takenNames: ReadonlySet<string>): string {
  if (!takenNames.has(base)) {
    return base;
  }

  let suffix = 2;

  while (takenNames.has(`${base} ${suffix}`)) {
    suffix += 1;
  }

  return `${base} ${suffix}`;
}
