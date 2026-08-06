"use client";

import { Provider, useAtomValue, useSetAtom } from "jotai";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/shared/ui/button";
import { Skeleton } from "@/shared/ui/skeleton";
import { useWorkflow, type Workflow } from "@/entities/workflow";
import { startWebcamPublish } from "@/features/camera/publish-webcam";
import { createEditorStore, isDirtyAtom, loadGraphAtom } from "@/features/workflow/graph-editing";
import { WorkflowEditorHeader } from "./editor-header";
import { WorkflowEditorWorkspace } from "./editor-workspace";

interface WorkflowEditorPageProps {
  id: string;
}

export function WorkflowEditorPage({ id }: WorkflowEditorPageProps) {
  const workflow = useWorkflow(id);

  if (workflow.data !== undefined) {
    return <WorkflowEditorScope key={id} workflow={workflow.data} />;
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

interface WorkflowEditorScopeProps {
  workflow: Workflow;
}

function WorkflowEditorScope({ workflow }: WorkflowEditorScopeProps) {
  const [store] = useState(() => {
    return createEditorStore(workflow.graph);
  });

  return (
    <Provider store={store}>
      <WorkflowEditorContent workflow={workflow} />
    </Provider>
  );
}

function WorkflowEditorContent({ workflow }: WorkflowEditorScopeProps) {
  const isDirty = useAtomValue(isDirtyAtom);
  const loadGraph = useSetAtom(loadGraphAtom);

  useEffect(() => {
    if (!isDirty) {
      loadGraph(workflow.graph);
    }
  }, [workflow.graph, isDirty, loadGraph]);

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
      <WorkflowEditorHeader workflow={workflow} />

      <WorkflowEditorWorkspace />
    </div>
  );
}
