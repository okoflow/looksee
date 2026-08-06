const BYTE_UNITS = ["B", "KB", "MB", "GB"] as const;

export function formatBytes(size: number): string {
  let value = size;
  let unitIndex = 0;

  while (value >= 1024 && unitIndex < BYTE_UNITS.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }

  const rounded = unitIndex === 0 ? String(value) : String(Number(value.toFixed(1)));

  return `${rounded} ${BYTE_UNITS[unitIndex]}`;
}
