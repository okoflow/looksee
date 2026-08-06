"use client";

import {
  Background,
  BackgroundVariant,
  ConnectionLineType,
  type NodeTypes,
  Panel,
  ReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import { NetworkIcon } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { COMMENT_TYPE_KEY, NODE_TYPE_KEY, useEditorHotkeys } from "@/features/workflow/graph-editing";
import { useFlowGraph } from "../model/use-flow-graph";
import { CanvasToolbar } from "./canvas-toolbar";
import { CommentNode } from "./comment-node";
import { FlowNode } from "./flow-node";
import { ZoomControls } from "./zoom-controls";

const nodeTypes = {
  [NODE_TYPE_KEY]: FlowNode,
  [COMMENT_TYPE_KEY]: CommentNode,
} satisfies NodeTypes;

export function WorkflowCanvas() {
  return (
    <ReactFlowProvider>
      <CanvasInner />
    </ReactFlowProvider>
  );
}

function CanvasInner() {
  useEditorHotkeys();

  const {
    activeTool,
    flowNodes,
    flowEdges,
    isValidConnection,
    handleNodesChange,
    handleEdgesChange,
    handleAutoLayout,
    handleConnect,
    handleDragOver,
    handleDrop,
    handlePaneClick,
  } = useFlowGraph();

  return (
    <div className="size-full" data-canvas-tool={activeTool} onDragOver={handleDragOver} onDrop={handleDrop}>
      <ReactFlow
        connectionLineType={ConnectionLineType.Bezier}
        edges={flowEdges}
        elementsSelectable={activeTool !== "pan"}
        fitView
        isValidConnection={isValidConnection}
        nodes={flowNodes}
        nodesDraggable={activeTool !== "pan"}
        nodeTypes={nodeTypes}
        onConnect={handleConnect}
        onEdgesChange={handleEdgesChange}
        onNodesChange={handleNodesChange}
        onPaneClick={handlePaneClick}
        panOnDrag={activeTool === "pan" ? true : [1, 2]}
        panOnScroll
        selectionOnDrag={activeTool === "select"}
        snapGrid={[16, 16]}
        snapToGrid
        zoomOnScroll={false}
      >
        <Background gap={16} variant={BackgroundVariant.Dots} />

        <CanvasToolbar />

        <ZoomControls />

        <Panel
          className="mb-editor-gutter ml-[calc(var(--spacing-editor-palette)_+_var(--spacing-editor-gutter)*2)] flex items-center rounded-md border bg-card p-1 shadow-xs"
          position="bottom-left"
        >
          <Button onClick={handleAutoLayout} size="sm" variant="ghost">
            <NetworkIcon className="-rotate-90" data-icon="inline-start" />
            Arrange
          </Button>
        </Panel>
      </ReactFlow>
    </div>
  );
}
