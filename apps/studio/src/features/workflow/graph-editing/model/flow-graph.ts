import type { Connection, Edge, Node } from "@xyflow/react";
import {
  type ConnectionVerdict,
  effectiveOutputPortId,
  NODE_ROLES,
  type NodeData,
  validateConnection,
  type WorkflowEdgeBranch,
  type WorkflowGraph,
} from "@/entities/workflow";

export const NODE_TYPE_KEY = "looksee";
export const COMMENT_TYPE_KEY = "comment";

export interface FlowNodeData extends Record<string, unknown> {
  config: NodeData;
}

export interface CommentNodeData extends Record<string, unknown> {
  text: string;
}

export type FlowGraphNode = Node<FlowNodeData, typeof NODE_TYPE_KEY>;
export type CommentFlowNode = Node<CommentNodeData, typeof COMMENT_TYPE_KEY>;
export type EditorFlowNode = FlowGraphNode | CommentFlowNode;

export function isGraphFlowNode(node: EditorFlowNode): node is FlowGraphNode {
  return node.type === NODE_TYPE_KEY;
}

export function isCommentFlowNode(node: EditorFlowNode): node is CommentFlowNode {
  return node.type === COMMENT_TYPE_KEY;
}

const BRANCH_LABELS: Record<WorkflowEdgeBranch, string> = {
  if: "If",
  else: "Else",
};

export function toReactFlowNodes(graph: WorkflowGraph): EditorFlowNode[] {
  const graphNodes = graph.nodes.map<EditorFlowNode>((node) => {
    return {
      id: node.id,
      type: NODE_TYPE_KEY,
      position: node.position,
      data: { config: node.data },
    };
  });

  const commentNodes = (graph.comments ?? []).map<EditorFlowNode>((comment) => {
    return {
      id: comment.id,
      type: COMMENT_TYPE_KEY,
      position: comment.position,
      data: { text: comment.text },
    };
  });

  return [...graphNodes, ...commentNodes];
}

function isWorkflowEdgeBranch(value: string | null | undefined): value is WorkflowEdgeBranch {
  return value === "if" || value === "else";
}

export function resolveWorkflowEdgeBranch(
  value: string | null | undefined,
  isFilterSource: boolean
): WorkflowEdgeBranch | undefined {
  if (isWorkflowEdgeBranch(value)) {
    return value;
  }

  if (isFilterSource) {
    return "if";
  }
}

export function branchPresentation(branch: WorkflowEdgeBranch | undefined): Partial<Edge> {
  if (!branch) {
    return {};
  }

  return {
    label: BRANCH_LABELS[branch],
    labelBgBorderRadius: 4,
    labelBgPadding: [4, 2],
    labelBgStyle: { fill: "var(--card)", fillOpacity: 0.95 },
    labelStyle: { fill: "var(--foreground)", fontSize: 11, fontWeight: 600 },
  };
}

interface KindedNode {
  id: string;
  kind: NodeData["kind"];
}

function filterNodeIds(nodes: readonly KindedNode[]): Set<string> {
  return new Set(
    nodes.flatMap((node) => {
      return NODE_ROLES[node.kind] === "filter" ? [node.id] : [];
    })
  );
}

export function toReactFlowEdges(graph: WorkflowGraph): Edge[] {
  const filters = filterNodeIds(
    graph.nodes.map((node) => {
      return { id: node.id, kind: node.data.kind };
    })
  );

  return graph.edges.map<Edge>((edge) => {
    const branch = resolveWorkflowEdgeBranch(edge.branch, filters.has(edge.source));

    return {
      id: edge.id,
      source: edge.source,
      target: edge.target,
      sourceHandle: branch,
      ...branchPresentation(branch),
    };
  });
}

export function validateFlowConnection(
  nodes: readonly EditorFlowNode[],
  edges: readonly Edge[],
  connection: Connection | Edge
): ConnectionVerdict {
  const kindsById = new Map(
    nodes.filter(isGraphFlowNode).map((node) => {
      return [node.id, node.data.config.kind] as const;
    })
  );

  const connectionEdges = edges.flatMap((edge) => {
    const sourceKind = kindsById.get(edge.source);

    if (sourceKind === undefined) {
      return [];
    }

    return [
      {
        port: effectiveOutputPortId(sourceKind, edge.sourceHandle),
        source: edge.source,
        target: edge.target,
      },
    ];
  });

  return validateConnection(kindsById, connectionEdges, {
    source: connection.source,
    sourceHandle: connection.sourceHandle,
    target: connection.target,
  });
}

export function reactFlowToDomain(nodes: readonly EditorFlowNode[], edges: Edge[]): WorkflowGraph {
  const graphNodes = nodes.filter(isGraphFlowNode);

  const filters = filterNodeIds(
    graphNodes.map((node) => {
      return { id: node.id, kind: node.data.config.kind };
    })
  );

  return {
    nodes: graphNodes.map((node) => {
      return {
        id: node.id,
        position: node.position,
        data: node.data.config,
      };
    }),
    edges: edges.map((edge) => {
      const branch = resolveWorkflowEdgeBranch(edge.sourceHandle, filters.has(edge.source));

      return {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        ...(branch ? { branch } : {}),
      };
    }),
    comments: nodes.filter(isCommentFlowNode).map((comment) => {
      return {
        id: comment.id,
        position: comment.position,
        text: comment.data.text,
      };
    }),
  };
}
