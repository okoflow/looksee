"use client";

import Link from "next/link";
import { useEffect } from "react";
import { Button } from "@/shared/ui/button";
import { Skeleton } from "@/shared/ui/skeleton";
import { useWorkflow, type Workflow } from "@/entities/workflow";
import { startWebcamPublish } from "@/features/camera/publish-webcam";
import { WorkflowMonitor } from "@/widgets/workflow-monitor";
import { WorkflowPageHeader } from "@/widgets/workflow-page-header";
import { MonitorRunButton } from "./monitor-run-button";

interface WorkflowMonitorPageProps {
  id: string;
}

export function WorkflowMonitorPage({ id }: WorkflowMonitorPageProps) {
  const workflow = useWorkflow(id);

  if (workflow.data !== undefined) {
    return <WorkflowMonitorContent workflow={workflow.data} />;
  }

  if (workflow.isError) {
    return (
      <div className="flex flex-col items-start gap-3 p-6">
        <p className="font-medium text-sm">Failed to load the workflow.</p>

        <p className="text-muted-foreground text-sm">{workflow.error.message}</p>

        <Button nativeButton={false} render={<Link href="/" />} variant="outline">
          Back to workflows
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 p-6">
      <Skeleton className="h-8 w-48" />

      <Skeleton className="h-120 w-full" />
    </div>
  );
}

interface WorkflowMonitorContentProps {
  workflow: Workflow;
}

function WorkflowMonitorContent({ workflow }: WorkflowMonitorContentProps) {
  useEffect(() => {
    if (!workflow.enabled) {
      return;
    }

    for (const camera of workflow.cameras) {
      if (camera.source_type === "webrtc") {
        startWebcamPublish(camera.id);
      }
    }
  }, [workflow.enabled, workflow.cameras]);

  return (
    <div className="flex h-svh min-h-0 flex-col">
      <WorkflowPageHeader workflow={workflow}>
        <MonitorRunButton workflow={workflow} />
      </WorkflowPageHeader>

      <WorkflowMonitor workflow={workflow} />
    </div>
  );
}
