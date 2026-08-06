import { type ConnectionEdge, effectiveOutputPortId, validateConnection } from "./connection-rules";
import { buildAdjacencyMap, collectReachable } from "./graph-traversal";
import type { NodeKind, WorkflowGraph } from "./schema";

export interface GraphIssue {
  message: string;
  nodeId?: string;
  severity: "error" | "warning";
}

export function validateGraph(graph: WorkflowGraph): GraphIssue[] {
  const kindsById = new Map(
    graph.nodes.map((node) => {
      return [node.id, node.data.kind] as const;
    })
  );

  const issues = [...edgeIssues(graph, kindsById), ...structureIssues(graph, kindsById)];

  return [
    ...issues.filter((issue) => {
      return issue.severity === "error";
    }),
    ...issues.filter((issue) => {
      return issue.severity === "warning";
    }),
  ];
}

function edgeIssues(graph: WorkflowGraph, kindsById: ReadonlyMap<string, NodeKind>): GraphIssue[] {
  const issues: GraphIssue[] = [];
  const seenEdges: ConnectionEdge[] = [];

  for (const edge of graph.edges) {
    const verdict = validateConnection(kindsById, seenEdges, {
      source: edge.source,
      sourceHandle: edge.branch,
      target: edge.target,
    });

    if (!verdict.allowed) {
      issues.push({
        message: verdict.violation.message,
        nodeId: edge.source,
        severity: "warning",
      });
    }

    const sourceKind = kindsById.get(edge.source);

    if (sourceKind !== undefined) {
      seenEdges.push({
        port: effectiveOutputPortId(sourceKind, edge.branch),
        source: edge.source,
        target: edge.target,
      });
    }
  }

  return issues;
}

function structureIssues(graph: WorkflowGraph, kindsById: ReadonlyMap<string, NodeKind>): GraphIssue[] {
  const cameraIds = graph.nodes.flatMap((node) => {
    return node.data.kind === "camera_source" ? [node.id] : [];
  });

  if (cameraIds.length === 0) {
    return [
      {
        message: "The workflow needs at least one camera source",
        severity: "error",
      },
    ];
  }

  const issues: GraphIssue[] = [];

  const knownEdges = graph.edges.filter((edge) => {
    return kindsById.has(edge.source) && kindsById.has(edge.target);
  });
  const adjacency = buildAdjacencyMap(knownEdges, "outgoing");

  const cycleNodeId = findCycle(cameraIds, adjacency);

  if (cycleNodeId !== null) {
    issues.push({
      message: "The workflow contains a cycle through this node",
      nodeId: cycleNodeId,
      severity: "error",
    });
  }

  const reachable = new Set(cameraIds);

  for (const cameraId of cameraIds) {
    const reachableFromCamera = collectReachable(cameraId, adjacency, { includeStart: false });

    for (const nodeId of reachableFromCamera) {
      reachable.add(nodeId);
    }

    const detectIds = [...reachableFromCamera].filter((nodeId) => {
      return kindsById.get(nodeId) === "detect";
    });

    if (detectIds.length === 0) {
      issues.push({
        message: "The camera must reach exactly one Detect node",
        nodeId: cameraId,
        severity: "error",
      });
    } else if (detectIds.length > 1) {
      issues.push({
        message: "The camera reaches more than one Detect node",
        nodeId: cameraId,
        severity: "error",
      });
    }
  }

  for (const node of graph.nodes) {
    if (!reachable.has(node.id)) {
      issues.push({
        message: "Not connected to a camera — this node is ignored when the workflow runs",
        nodeId: node.id,
        severity: "warning",
      });
    }
  }

  return issues;
}

function findCycle(startIds: readonly string[], adjacency: ReadonlyMap<string, readonly string[]>): string | null {
  const visiting = new Set<string>();
  const visited = new Set<string>();

  const visit = (nodeId: string): string | null => {
    if (visiting.has(nodeId)) {
      return nodeId;
    }

    if (visited.has(nodeId)) {
      return null;
    }

    visiting.add(nodeId);

    for (const targetId of adjacency.get(nodeId) ?? []) {
      const cycleNodeId = visit(targetId);

      if (cycleNodeId !== null) {
        return cycleNodeId;
      }
    }

    visiting.delete(nodeId);
    visited.add(nodeId);

    return null;
  };

  for (const startId of startIds) {
    const cycleNodeId = visit(startId);

    if (cycleNodeId !== null) {
      return cycleNodeId;
    }
  }

  return null;
}
