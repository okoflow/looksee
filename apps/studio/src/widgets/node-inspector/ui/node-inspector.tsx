"use client";

import { useAtomValue, useSetAtom } from "jotai";
import { FieldGroup } from "@/shared/ui/field";
import { ScrollArea } from "@/shared/ui/scroll-area";
import type { NodeData } from "@/entities/workflow";
import {
  deleteNodeAtom,
  selectedNodeAtom,
  selectedNodeModelIdsAtom,
  selectedNodeUpstreamSourceAtom,
  updateNodeDataAtom,
} from "@/features/workflow/graph-editing";
import { getNodeDefinition, NodeForm } from "@/features/workflow/node-configuration";
import { NodeInspectorEmpty } from "./inspector-empty-state";
import { NodeInspectorHeader } from "./inspector-header";

export function NodeInspector() {
  const selectedNode = useAtomValue(selectedNodeAtom);
  const modelIds = useAtomValue(selectedNodeModelIdsAtom);
  const upstreamSource = useAtomValue(selectedNodeUpstreamSourceAtom);

  const updateNodeData = useSetAtom(updateNodeDataAtom);
  const deleteNode = useSetAtom(deleteNodeAtom);

  if (!selectedNode) {
    return <NodeInspectorEmpty />;
  }

  const definition = getNodeDefinition(selectedNode.data.kind);

  const handleDelete = () => {
    deleteNode(selectedNode.id);
  };

  const handleNodeDataChange = (data: NodeData) => {
    updateNodeData({ nodeId: selectedNode.id, data });
  };

  return (
    <aside className="flex h-full w-editor-inspector shrink-0 flex-col overflow-hidden rounded-xl border bg-card">
      <NodeInspectorHeader description={definition.description} label={definition.label} onDelete={handleDelete} />

      <ScrollArea className="min-h-0 flex-1">
        <FieldGroup className="p-4">
          <NodeForm
            data={selectedNode.data}
            key={selectedNode.id}
            modelIds={modelIds}
            onChange={handleNodeDataChange}
            upstreamSource={upstreamSource}
          />
        </FieldGroup>
      </ScrollArea>
    </aside>
  );
}
