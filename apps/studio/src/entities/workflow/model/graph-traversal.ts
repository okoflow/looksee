interface GraphEdge {
  source: string;
  target: string;
}

export function buildAdjacencyMap(
  edges: readonly GraphEdge[],
  direction: "outgoing" | "incoming"
): Map<string, string[]> {
  const adjacency = new Map<string, string[]>();

  for (const edge of edges) {
    const from = direction === "outgoing" ? edge.source : edge.target;
    const to = direction === "outgoing" ? edge.target : edge.source;

    const neighbors = adjacency.get(from);

    if (neighbors === undefined) {
      adjacency.set(from, [to]);
    } else {
      neighbors.push(to);
    }
  }

  return adjacency;
}

export function collectReachable(
  startId: string,
  adjacency: ReadonlyMap<string, readonly string[]>,
  options: { includeStart: boolean }
): Set<string> {
  const visited = new Set<string>();
  const queue = options.includeStart ? [startId] : [...(adjacency.get(startId) ?? [])];

  while (queue.length > 0) {
    const nodeId = queue.pop();

    if (nodeId === undefined || visited.has(nodeId)) {
      continue;
    }

    visited.add(nodeId);
    queue.push(...(adjacency.get(nodeId) ?? []));
  }

  return visited;
}
