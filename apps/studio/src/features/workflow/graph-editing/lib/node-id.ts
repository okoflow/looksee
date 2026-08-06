export function generateNodeId(kind: string, existingIds: ReadonlySet<string>): string {
  let id = `${kind}-${Math.random().toString(36).slice(2, 8)}`;

  while (existingIds.has(id)) {
    id = `${kind}-${Math.random().toString(36).slice(2, 8)}`;
  }

  return id;
}
