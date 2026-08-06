import type { NormalizedPolygon } from "@/shared/lib/geometry";
import { buildAdjacencyMap, collectReachable } from "./graph-traversal";
import type { NodeData, WorkflowGraph } from "./schema";

export type CameraSourceNodeData = Extract<NodeData, { kind: "camera_source" }>;

export interface CameraShape {
  kind: "line" | "zone";
  nodeId: string;
  points: NormalizedPolygon;
}

export function getUpstreamCameraSource(graph: WorkflowGraph, nodeId: string): CameraSourceNodeData | null {
  const nodeDataById = new Map(
    graph.nodes.map((node) => {
      return [node.id, node.data] as const;
    })
  );

  const incomingByNode = buildAdjacencyMap(graph.edges, "incoming");
  const ancestorIds = collectReachable(nodeId, incomingByNode, { includeStart: true });

  for (const ancestorId of ancestorIds) {
    const nodeData = nodeDataById.get(ancestorId);

    if (nodeData?.kind === "camera_source") {
      return nodeData;
    }
  }

  return null;
}

export function getCameraShapes(graph: WorkflowGraph, cameraNodeId: string): CameraShape[] {
  const nodeDataById = new Map(
    graph.nodes.map((node) => {
      return [node.id, node.data] as const;
    })
  );

  const outgoingByNode = buildAdjacencyMap(graph.edges, "outgoing");
  const descendantIds = collectReachable(cameraNodeId, outgoingByNode, { includeStart: false });

  const shapes: CameraShape[] = [];

  for (const descendantId of [...descendantIds].sort()) {
    const nodeData = nodeDataById.get(descendantId);

    if (nodeData?.kind === "zone_filter" && nodeData.polygon.length >= 3) {
      shapes.push({ kind: "zone", nodeId: descendantId, points: nodeData.polygon });
    }

    if (nodeData?.kind === "line_crossing_filter" && nodeData.line.length >= 2) {
      shapes.push({ kind: "line", nodeId: descendantId, points: nodeData.line });
    }
  }

  return shapes;
}

export function getRuntimeModelIds(graph: WorkflowGraph, nodeId: string): string[] {
  const nodeDataById = new Map(
    graph.nodes.map((node) => {
      return [node.id, node.data] as const;
    })
  );

  const incomingByNode = buildAdjacencyMap(graph.edges, "incoming");
  const ancestorIds = collectReachable(nodeId, incomingByNode, { includeStart: true });

  const modelIds = new Set<string>();

  for (const ancestorId of ancestorIds) {
    if (ancestorId === nodeId) {
      continue;
    }

    const nodeData = nodeDataById.get(ancestorId);

    if (nodeData?.kind === "detect" && nodeData.model_id !== null) {
      modelIds.add(nodeData.model_id);
    }
  }

  return Array.from(modelIds).sort();
}
