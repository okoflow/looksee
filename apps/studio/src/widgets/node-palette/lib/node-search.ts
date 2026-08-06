import type { NodeDefinition } from "@/features/workflow/node-configuration";

export function matchesNodeQuery(definition: NodeDefinition, query: string): boolean {
  const needle = query.trim().toLowerCase();

  if (needle === "") {
    return true;
  }

  return definition.label.toLowerCase().includes(needle) || definition.description.toLowerCase().includes(needle);
}
