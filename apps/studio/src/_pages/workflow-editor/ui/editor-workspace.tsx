"use client";

import { NodeInspector } from "@/widgets/node-inspector";
import { NodePalette } from "@/widgets/node-palette";
import { WorkflowCanvas } from "@/widgets/workflow-canvas";

export function WorkflowEditorWorkspace() {
  return (
    <div className="relative min-h-0 flex-1">
      <WorkflowCanvas />

      <div className="inset-y-editor-gutter left-editor-gutter absolute z-10">
        <NodePalette />
      </div>

      <div className="inset-y-editor-gutter right-editor-gutter absolute z-10">
        <NodeInspector />
      </div>
    </div>
  );
}
