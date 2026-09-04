"use client";

import { useSetAtom } from "jotai";
import { isHTTPError } from "ky";
import { Loader2Icon, PlayIcon, SquareIcon } from "lucide-react";
import { toast } from "sonner";
import { z } from "zod";
import { Button } from "@/shared/ui/button";
import { useUpdateWorkflow, validateGraph, type Workflow } from "@/entities/workflow";
import { startWebcamPublish, stopWebcamPublish } from "@/features/camera/publish-webcam";
import { acknowledgeSaveAtom, focusNodeAtom, serializeGraphAtom } from "@/features/workflow/graph-editing";

const invalidGraphErrorSchema = z.object({ node_id: z.string().min(1) });

function invalidNodeIdOf(error: unknown): string | null {
  if (!isHTTPError(error)) {
    return null;
  }

  const parsed = invalidGraphErrorSchema.safeParse(error.data);

  return parsed.success ? parsed.data.node_id : null;
}

interface RunWorkflowButtonProps {
  workflow: Workflow;
}

export function RunWorkflowButton({ workflow }: RunWorkflowButtonProps) {
  const updateWorkflow = useUpdateWorkflow(workflow.id, {
    onError: (error) => {
      const invalidNodeId = invalidNodeIdOf(error);

      if (invalidNodeId !== null) {
        focusNode(invalidNodeId);
      }

      toast.error(error.message);
    },
  });

  const serializeGraph = useSetAtom(serializeGraphAtom);
  const acknowledgeSave = useSetAtom(acknowledgeSaveAtom);
  const focusNode = useSetAtom(focusNodeAtom);

  const handleRun = () => {
    const graph = serializeGraph();
    const issues = validateGraph(graph);

    const firstError = issues.find((issue) => {
      return issue.severity === "error";
    });

    if (firstError !== undefined) {
      if (firstError.nodeId !== undefined) {
        focusNode(firstError.nodeId);
      }

      toast.error(firstError.message);

      return;
    }

    const warnings = issues.filter((issue) => {
      return issue.severity === "warning";
    });
    const firstWarning = warnings.at(0);

    if (firstWarning !== undefined) {
      toast.warning(
        warnings.length === 1 ? firstWarning.message : `${firstWarning.message} (+${warnings.length - 1} more)`
      );
    }

    updateWorkflow.mutate(
      { graph, enabled: true },
      {
        onSuccess: (updatedWorkflow) => {
          acknowledgeSave(graph);

          for (const camera of updatedWorkflow.cameras) {
            if (camera.source_type === "webrtc") {
              startWebcamPublish(camera.id);
            }
          }
        },
      }
    );
  };

  const handleStop = () => {
    updateWorkflow.mutate(
      { enabled: false },
      {
        onSuccess: (updatedWorkflow) => {
          for (const camera of updatedWorkflow.cameras) {
            stopWebcamPublish(camera.id);
          }
        },
      }
    );
  };

  if (workflow.enabled) {
    return (
      <Button disabled={updateWorkflow.isPending} onClick={handleStop} size="sm" variant="secondary">
        {updateWorkflow.isPending ? (
          <Loader2Icon className="animate-spin" data-icon="inline-start" />
        ) : (
          <SquareIcon data-icon="inline-start" />
        )}
        Stop
      </Button>
    );
  }

  return (
    <Button disabled={updateWorkflow.isPending} onClick={handleRun} size="sm">
      {updateWorkflow.isPending ? (
        <Loader2Icon className="animate-spin" data-icon="inline-start" />
      ) : (
        <PlayIcon data-icon="inline-start" />
      )}
      Run
    </Button>
  );
}
