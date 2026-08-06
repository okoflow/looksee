"use client";

import { Loader2Icon, PlayIcon, SquareIcon } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/shared/ui/button";
import { useUpdateWorkflow, type Workflow } from "@/entities/workflow";
import { startWebcamPublish, stopWebcamPublish } from "@/features/camera/publish-webcam";

interface MonitorRunButtonProps {
  workflow: Workflow;
}

export function MonitorRunButton({ workflow }: MonitorRunButtonProps) {
  const updateWorkflow = useUpdateWorkflow(workflow.id, {
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const handleRun = () => {
    updateWorkflow.mutate(
      { enabled: true },
      {
        onSuccess: (updatedWorkflow) => {
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
      <Button disabled={updateWorkflow.isPending} onClick={handleStop} size="sm" variant="destructive">
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
