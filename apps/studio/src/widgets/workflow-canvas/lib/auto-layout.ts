import dagre from "@dagrejs/dagre";
import type { XYPosition } from "@xyflow/react";

const FALLBACK_NODE_WIDTH = 176;
const FALLBACK_NODE_HEIGHT = 58;
const RANK_SEPARATION = 90;
const NODE_SEPARATION = 40;

interface LayoutNode {
  id: string;
  measured?: {
    height?: number;
    width?: number;
  };
}

interface LayoutEdge {
  source: string;
  target: string;
}

export function layoutPositions(nodes: readonly LayoutNode[], edges: readonly LayoutEdge[]): Map<string, XYPosition> {
  const graph = new dagre.graphlib.Graph();

  graph.setGraph({ rankdir: "LR", ranksep: RANK_SEPARATION, nodesep: NODE_SEPARATION });
  graph.setDefaultEdgeLabel(() => {
    return {};
  });

  for (const node of nodes) {
    graph.setNode(node.id, {
      width: node.measured?.width ?? FALLBACK_NODE_WIDTH,
      height: node.measured?.height ?? FALLBACK_NODE_HEIGHT,
    });
  }

  for (const edge of edges) {
    graph.setEdge(edge.source, edge.target);
  }

  dagre.layout(graph);

  return new Map(
    nodes.map((node) => {
      const placed = graph.node(node.id);

      return [
        node.id,
        {
          x: placed.x - placed.width / 2,
          y: placed.y - placed.height / 2,
        },
      ];
    })
  );
}
