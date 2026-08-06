"use client";

import { NodeInspector } from "@/widgets/node-inspector";
import { NodePalette } from "@/widgets/node-palette";
import { WorkflowCanvas } from "@/widgets/workflow-canvas";

export function WorkflowEditorWorkspace() {
  return (
    <div className="relative min-h-0 flex-1">
      <WorkflowCanvas />

      <div className="absolute inset-y-editor-gutter left-editor-gutter z-10">
        <NodePalette />
      </div>

      <div className="absolute inset-y-editor-gutter right-editor-gutter z-10">
        <NodeInspector />
      </div>
    </div>
  );
}
