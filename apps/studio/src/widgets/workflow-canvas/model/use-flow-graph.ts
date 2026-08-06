"use client";

import { type Connection, type Edge, useReactFlow } from "@xyflow/react";
import { useAtomValue, useSetAtom } from "jotai";
import { type DragEvent, type MouseEvent as ReactMouseEvent, useEffect } from "react";
import {
  activeToolAtom,
  addCommentAtom,
  addNodeAtom,
  applyEdgeChangesAtom,
  applyNodeChangesAtom,
  applyNodePositionsAtom,
  connectEdgeAtom,
  DROP_OFFSET_X,
  DROP_OFFSET_Y,
  type EditorFlowNode,
  flowEdgesAtom,
  flowNodesAtom,
  isGraphFlowNode,
  NODE_DRAG_MIME,
  nodeFocusRequestAtom,
  validateFlowConnection,
} from "@/features/workflow/graph-editing";
import { getNodeDefinition, isNodeKind } from "@/features/workflow/node-configuration";
import { layoutPositions } from "../lib/auto-layout";

export function useFlowGraph() {
  const { screenToFlowPosition, fitView, getNodes } = useReactFlow<EditorFlowNode>();

  const flowNodes = useAtomValue(flowNodesAtom);
  const flowEdges = useAtomValue(flowEdgesAtom);
  const nodeFocusRequest = useAtomValue(nodeFocusRequestAtom);
  const activeTool = useAtomValue(activeToolAtom);

  const applyNodeChanges = useSetAtom(applyNodeChangesAtom);
  const applyEdgeChanges = useSetAtom(applyEdgeChangesAtom);
  const connectEdge = useSetAtom(connectEdgeAtom);
  const addNode = useSetAtom(addNodeAtom);
  const addComment = useSetAtom(addCommentAtom);
  const applyNodePositions = useSetAtom(applyNodePositionsAtom);

  useEffect(() => {
    if (nodeFocusRequest === null) {
      return;
    }

    fitView({ nodes: [{ id: nodeFocusRequest.nodeId }], duration: 300, maxZoom: 1 });
  }, [nodeFocusRequest, fitView]);

  const handleDragOver = (event: DragEvent<HTMLDivElement>) => {
    if (event.dataTransfer.types.includes(NODE_DRAG_MIME)) {
      event.preventDefault();

      event.dataTransfer.dropEffect = "move";
    }
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    const kind = event.dataTransfer.getData(NODE_DRAG_MIME);

    if (!isNodeKind(kind)) {
      return;
    }

    event.preventDefault();

    const dropPoint = screenToFlowPosition({ x: event.clientX, y: event.clientY });

    addNode({
      data: { ...getNodeDefinition(kind).defaults },
      position: {
        x: dropPoint.x - DROP_OFFSET_X,
        y: dropPoint.y - DROP_OFFSET_Y,
      },
    });
  };

  const handlePaneClick = (event: ReactMouseEvent) => {
    if (activeTool !== "comment") {
      return;
    }

    addComment(screenToFlowPosition({ x: event.clientX, y: event.clientY }));
  };

  const handleAutoLayout = () => {
    applyNodePositions(layoutPositions(getNodes().filter(isGraphFlowNode), flowEdges));

    fitView({ duration: 300 });
  };

  const isValidConnection = (connection: Connection | Edge) => {
    return validateFlowConnection(flowNodes, flowEdges, connection).allowed;
  };

  return {
    activeTool,
    flowNodes,
    flowEdges,
    isValidConnection,
    handleNodesChange: applyNodeChanges,
    handleEdgesChange: applyEdgeChanges,
    handleAutoLayout,
    handleConnect: connectEdge,
    handleDragOver,
    handleDrop,
    handlePaneClick,
  };
}
