"use client";

import Link from "next/link";
import type { PropsWithChildren } from "react";
import { SidebarTrigger } from "@/shared/ui/sidebar";
import type { Workflow } from "@/entities/workflow";
import { WorkflowNameEditor } from "./workflow-name-editor";
import { WorkflowViewSwitcher } from "./workflow-view-switcher";

interface WorkflowPageHeaderProps {
  workflow: Workflow;
}

export function WorkflowPageHeader({ children, workflow }: PropsWithChildren<WorkflowPageHeaderProps>) {
  return (
    <header className="relative flex h-12 shrink-0 items-center gap-2 border-b px-3">
      <SidebarTrigger className="-ml-1" />

      <nav className="flex min-w-0 items-center gap-1.5 text-sm">
        <Link className="text-muted-foreground transition hover:text-foreground" href="/">
          Workflows
        </Link>

        <span className="text-muted-foreground">/</span>

        <WorkflowNameEditor workflow={workflow} />
      </nav>

      <div className="absolute left-1/2 -translate-x-1/2">
        <WorkflowViewSwitcher workflowId={workflow.id} />
      </div>

      <div className="ml-auto flex items-center gap-2">{children}</div>
    </header>
  );
}
