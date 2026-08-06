"use client";

import { useAtom, useSetAtom } from "jotai";
import { toast } from "sonner";
import { Button } from "@/shared/ui/button";
import { useUpdateWorkflow, type Workflow } from "@/entities/workflow";
import { isDirtyAtom, serializeGraphAtom } from "@/features/workflow/graph-editing";
import { WorkflowPageHeader } from "@/widgets/workflow-page-header";
import { RunWorkflowButton } from "./run-workflow-button";

interface WorkflowEditorHeaderProps {
  workflow: Workflow;
}

export function WorkflowEditorHeader({ workflow }: WorkflowEditorHeaderProps) {
  const updateWorkflow = useUpdateWorkflow(workflow.id, {
    onSuccess: () => {
      toast.success("Workflow saved");

      setIsDirty(false);
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const [isDirty, setIsDirty] = useAtom(isDirtyAtom);
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
