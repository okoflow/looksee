import {
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type EdgeChange,
  type NodeChange,
  type XYPosition,
} from "@xyflow/react";
import { atom, createStore, type Getter, type Setter } from "jotai";
import { selectAtom } from "jotai/utils";
import { arraysShallowEqual } from "@/shared/lib/arrays-shallow-equal";
import {
  type CameraSourceNodeData,
  getRuntimeModelIds,
  getUpstreamCameraSource,
  type NodeData,
  type WorkflowGraph,
} from "@/entities/workflow";
import { generateNodeId } from "../lib/node-id";
import {
  branchPresentation,
  COMMENT_TYPE_KEY,
  type CommentFlowNode,
  type EditorFlowNode,
  type FlowGraphNode,
  isCommentFlowNode,
  isGraphFlowNode,
  NODE_TYPE_KEY,
  reactFlowToDomain,
  resolveWorkflowEdgeBranch,
  toReactFlowEdges,
  toReactFlowNodes,
  validateFlowConnection,
} from "./flow-graph";
import { activeToolAtom } from "./tool-atoms";

export const flowNodesAtom = atom<EditorFlowNode[]>([]);
export const flowEdgesAtom = atom<Edge[]>([]);
export const isDirtyAtom = atom(false);

interface NodeFocusRequest {
  nodeId: string;
  requestId: number;
}

export const nodeFocusRequestAtom = atom<NodeFocusRequest | null>(null);

export interface SelectedNode {
  data: NodeData;
  id: string;
}

function selectedNodesEqual(left: SelectedNode | null, right: SelectedNode | null): boolean {
  if (left === null || right === null) {
    return left === right;
  }

  return left.id === right.id && left.data === right.data;
}

export const selectedNodeAtom = selectAtom(
  flowNodesAtom,
  (nodes) => {
    const node = nodes.filter(isGraphFlowNode).find((candidate) => {
      return candidate.selected;
    });

    return node === undefined ? null : { id: node.id, data: node.data.config };
  },
  selectedNodesEqual
);

const EMPTY_MODEL_IDS: string[] = [];

const selectedNodeModelIdsBaseAtom = atom((get) => {
  const selected = get(selectedNodeAtom);

  if (selected === null) {
    return EMPTY_MODEL_IDS;
  }

  return getRuntimeModelIds(reactFlowToDomain(get(flowNodesAtom), get(flowEdgesAtom)), selected.id);
});

export const selectedNodeModelIdsAtom = selectAtom(
  selectedNodeModelIdsBaseAtom,
  (ids) => {
    return ids;
  },
  arraysShallowEqual
);

const selectedNodeUpstreamSourceBaseAtom = atom((get) => {
  const selected = get(selectedNodeAtom);

  if (selected === null) {
    return null;
  }

  return getUpstreamCameraSource(reactFlowToDomain(get(flowNodesAtom), get(flowEdgesAtom)), selected.id);
});

function upstreamSourcesEqual(left: CameraSourceNodeData | null, right: CameraSourceNodeData | null): boolean {
  if (left === null || right === null) {
    return left === right;
  }

  return left.source_type === right.source_type && left.url === right.url && left.name === right.name;
}

export const selectedNodeUpstreamSourceAtom = selectAtom(
  selectedNodeUpstreamSourceBaseAtom,
  (source) => {
    return source;
  },
  upstreamSourcesEqual
);

interface HistorySnapshot {
  edges: Edge[];
  nodes: EditorFlowNode[];
  tag: string | null;
}

const HISTORY_LIMIT = 100;
const REMOVAL_MERGE_WINDOW_MS = 100;

const pastAtom = atom<HistorySnapshot[]>([]);
const futureAtom = atom<HistorySnapshot[]>([]);
const dragStartSnapshotAtom = atom<HistorySnapshot | null>(null);
const lastRemovalPushAtAtom = atom(0);

export const canUndoAtom = atom((get) => {
  return get(pastAtom).length > 0;
});

export const canRedoAtom = atom((get) => {
  return get(futureAtom).length > 0;
});

function snapshotOf(get: Getter, tag: string | null = null): HistorySnapshot {
  return { edges: get(flowEdgesAtom), nodes: get(flowNodesAtom), tag };
}

function pushHistory(get: Getter, set: Setter, snapshot: HistorySnapshot) {
  const past = get(pastAtom);
  const top = past.at(-1);

  set(futureAtom, []);

  if (snapshot.tag !== null && top !== undefined && top.tag === snapshot.tag) {
    return;
  }

  set(pastAtom, [...past.slice(-(HISTORY_LIMIT - 1)), snapshot]);
}

function pushRemovalHistory(get: Getter, set: Setter) {
  const now = Date.now();

  if (now - get(lastRemovalPushAtAtom) < REMOVAL_MERGE_WINDOW_MS) {
    return;
  }

  set(lastRemovalPushAtAtom, now);
  pushHistory(get, set, snapshotOf(get));
}

export const undoAtom = atom(null, (get, set) => {
  const past = get(pastAtom);
  const snapshot = past.at(-1);

  if (snapshot === undefined) {
    return;
  }

  set(pastAtom, past.slice(0, -1));
  set(futureAtom, [...get(futureAtom), snapshotOf(get)]);
  set(flowNodesAtom, snapshot.nodes);
  set(flowEdgesAtom, snapshot.edges);
  set(isDirtyAtom, true);
});

export const redoAtom = atom(null, (get, set) => {
  const future = get(futureAtom);
  const snapshot = future.at(-1);

  if (snapshot === undefined) {
    return;
  }

  set(futureAtom, future.slice(0, -1));
  set(pastAtom, [...get(pastAtom), snapshotOf(get)]);
  set(flowNodesAtom, snapshot.nodes);
  set(flowEdgesAtom, snapshot.edges);
  set(isDirtyAtom, true);
});

export const serializeGraphAtom = atom(null, (get): WorkflowGraph => {
  return reactFlowToDomain(get(flowNodesAtom), get(flowEdgesAtom));
});

export const loadGraphAtom = atom(null, (get, set, graph: WorkflowGraph) => {
  const selectedIds = new Set(
    get(flowNodesAtom).flatMap((node) => {
      return node.selected ? [node.id] : [];
    })
  );

  set(
    flowNodesAtom,
    toReactFlowNodes(graph).map((node) => {
      return selectedIds.has(node.id) ? { ...node, selected: true } : node;
    })
  );
  set(flowEdgesAtom, toReactFlowEdges(graph));
  set(dragStartSnapshotAtom, null);
});

function isDragStartChange(change: NodeChange<EditorFlowNode>): boolean {
  return change.type === "position" && change.dragging === true;
}

function isDragEndChange(change: NodeChange<EditorFlowNode>): boolean {
  return change.type === "position" && change.dragging === false;
}

function isRemoveChange(change: NodeChange<EditorFlowNode> | EdgeChange): boolean {
  return change.type === "remove";
}

export const applyNodeChangesAtom = atom(null, (get, set, changes: NodeChange<EditorFlowNode>[]) => {
  if (changes.some(isDragStartChange) && get(dragStartSnapshotAtom) === null) {
    set(dragStartSnapshotAtom, snapshotOf(get));
  }

  const removed = changes.some(isRemoveChange);

  if (removed) {
    pushRemovalHistory(get, set);
  }

  const beforeChanges = snapshotOf(get);

  set(flowNodesAtom, applyNodeChanges(changes, get(flowNodesAtom)));

  const dragEnded = changes.some(isDragEndChange);

  if (dragEnded) {
    pushHistory(get, set, get(dragStartSnapshotAtom) ?? beforeChanges);
    set(dragStartSnapshotAtom, null);
  }

  if (removed || dragEnded) {
    set(isDirtyAtom, true);
  }
});

export const applyEdgeChangesAtom = atom(null, (get, set, changes: EdgeChange[]) => {
  const removed = changes.some(isRemoveChange);

  if (removed) {
    pushRemovalHistory(get, set);
  }

  set(flowEdgesAtom, applyEdgeChanges(changes, get(flowEdgesAtom)));

  if (removed) {
    set(isDirtyAtom, true);
  }
});

export const connectEdgeAtom = atom(null, (get, set, connection: Connection) => {
  const verdict = validateFlowConnection(get(flowNodesAtom), get(flowEdgesAtom), connection);

  if (!verdict.allowed) {
    console.warn("connection rejected:", verdict.violation.message);

    return;
  }

  pushHistory(get, set, snapshotOf(get));

  const branch = resolveWorkflowEdgeBranch(connection.sourceHandle, false);

  set(flowEdgesAtom, addEdge({ ...connection, ...branchPresentation(branch) }, get(flowEdgesAtom)));
  set(isDirtyAtom, true);
});

interface AddNodeArgs {
  data: NodeData;
  position: XYPosition;
}

export const addNodeAtom = atom(null, (get, set, { data, position }: AddNodeArgs) => {
  pushHistory(get, set, snapshotOf(get));

  const nodes = get(flowNodesAtom);

  const existingIds = new Set(
    nodes.map((node) => {
      return node.id;
    })
  );

  const nextNode: FlowGraphNode = {
    id: generateNodeId(data.kind, existingIds),
    type: NODE_TYPE_KEY,
    position,
    data: { config: data },
    selected: true,
  };

  set(flowNodesAtom, [...withClearedSelection(nodes), nextNode]);
  set(isDirtyAtom, true);
});

export const addCommentAtom = atom(null, (get, set, position: XYPosition) => {
  pushHistory(get, set, snapshotOf(get));

  const nodes = get(flowNodesAtom);

  const existingIds = new Set(
    nodes.map((node) => {
      return node.id;
    })
  );

  const comment: CommentFlowNode = {
    id: generateNodeId("comment", existingIds),
    type: COMMENT_TYPE_KEY,
    position,
    data: { text: "" },
    selected: true,
  };

  set(flowNodesAtom, [...withClearedSelection(nodes), comment]);
  set(isDirtyAtom, true);
  set(activeToolAtom, "select");
});

interface UpdateCommentTextArgs {
  commentId: string;
  text: string;
}

export const updateCommentTextAtom = atom(null, (get, set, { commentId, text }: UpdateCommentTextArgs) => {
  pushHistory(get, set, snapshotOf(get, `comment-text:${commentId}`));

  set(
    flowNodesAtom,
    get(flowNodesAtom).map((node) => {
      return isCommentFlowNode(node) && node.id === commentId ? { ...node, data: { text } } : node;
    })
  );
  set(isDirtyAtom, true);
});

export const applyNodePositionsAtom = atom(null, (get, set, positions: ReadonlyMap<string, XYPosition>) => {
  pushHistory(get, set, snapshotOf(get));

  set(
    flowNodesAtom,
    get(flowNodesAtom).map((node) => {
      const position = positions.get(node.id);

      return position === undefined ? node : { ...node, position };
    })
  );
  set(isDirtyAtom, true);
});

interface UpdateNodeDataArgs {
  data: NodeData;
  nodeId: string;
}

export const updateNodeDataAtom = atom(null, (get, set, { data, nodeId }: UpdateNodeDataArgs) => {
  pushHistory(get, set, snapshotOf(get, `node-data:${nodeId}`));

  set(
    flowNodesAtom,
    get(flowNodesAtom).map((node) => {
      return isGraphFlowNode(node) && node.id === nodeId ? { ...node, data: { config: data } } : node;
    })
  );
  set(isDirtyAtom, true);
});

export const deleteNodeAtom = atom(null, (get, set, nodeId: string) => {
  pushHistory(get, set, snapshotOf(get));

  set(
    flowNodesAtom,
    get(flowNodesAtom).filter((node) => {
      return node.id !== nodeId;
    })
  );
  set(
    flowEdgesAtom,
    get(flowEdgesAtom).filter((edge) => {
      return edge.source !== nodeId && edge.target !== nodeId;
    })
  );
  set(isDirtyAtom, true);
});

export const focusNodeAtom = atom(null, (get, set, nodeId: string) => {
  set(
    flowNodesAtom,
    get(flowNodesAtom).map((node) => {
      const selected = node.id === nodeId;

      return (node.selected ?? false) === selected ? node : { ...node, selected };
    })
  );

  const previous = get(nodeFocusRequestAtom);

  set(nodeFocusRequestAtom, { nodeId, requestId: (previous?.requestId ?? 0) + 1 });
});

function withClearedSelection(nodes: readonly EditorFlowNode[]): EditorFlowNode[] {
  return nodes.map((node) => {
    return node.selected ? { ...node, selected: false } : node;
  });
}

export function createEditorStore(graph: WorkflowGraph) {
  const store = createStore();

  store.set(loadGraphAtom, graph);

  return store;
}
