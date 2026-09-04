"use client";

import { useAtomValue, useSetAtom } from "jotai";
import { toast } from "sonner";
import { Button } from "@/shared/ui/button";
import { useUpdateWorkflow, type Workflow } from "@/entities/workflow";
import { acknowledgeSaveAtom, isDirtyAtom, serializeGraphAtom } from "@/features/workflow/graph-editing";
import { WorkflowPageHeader } from "@/widgets/workflow-page-header";
import { RunWorkflowButton } from "./run-workflow-button";

interface WorkflowEditorHeaderProps {
  workflow: Workflow;
}

export function WorkflowEditorHeader({ workflow }: WorkflowEditorHeaderProps) {
  const updateWorkflow = useUpdateWorkflow(workflow.id, {
    onSuccess: (_workflow, submitted) => {
      toast.success("Workflow saved");

      if (submitted.graph !== undefined) {
        acknowledgeSave(submitted.graph);
      }
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const isDirty = useAtomValue(isDirtyAtom);
  const acknowledgeSave = useSetAtom(acknowledgeSaveAtom);
  const serializeGraph = useSetAtom(serializeGraphAtom);

  const handleSave = () => {
    updateWorkflow.mutate({ graph: serializeGraph() });
  };

  return (
    <WorkflowPageHeader workflow={workflow}>
      <Button disabled={!isDirty || updateWorkflow.isPending} onClick={handleSave} size="sm" variant="outline">
        Save
      </Button>

      <RunWorkflowButton workflow={workflow} />
    </WorkflowPageHeader>
  );
}
