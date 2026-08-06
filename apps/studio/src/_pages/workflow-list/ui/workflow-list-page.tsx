"use client";

import type { PropsWithChildren } from "react";
import { SidebarTrigger } from "@/shared/ui/sidebar";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table";
import { useWorkflows } from "@/entities/workflow";
import { CreateWorkflowDialog } from "@/features/workflow/create-workflow";
import { WorkflowRow } from "./workflow-row";

function MessageRow({ children }: PropsWithChildren) {
  return (
    <TableRow>
      <TableCell className="py-8 text-center text-muted-foreground" colSpan={4}>
        {children}
      </TableCell>
    </TableRow>
  );
}

function WorkflowRows() {
  const workflows = useWorkflows();

  if (workflows.isPending) {
    return <MessageRow>Loading…</MessageRow>;
  }

  if (workflows.isError) {
    return <MessageRow>Couldn't load workflows.</MessageRow>;
  }

  if (!workflows.data.length) {
    return <MessageRow>No workflows yet. Create one to get started.</MessageRow>;
  }

  return workflows.data.map((workflow) => {
    return <WorkflowRow key={workflow.id} workflow={workflow} />;
  });
}

export function WorkflowListPage() {
  return (
    <div className="flex flex-col">
      <header className="flex h-12 shrink-0 items-center gap-2 border-b px-3">
        <SidebarTrigger className="-ml-1" />

        <h1 className="font-medium text-sm">Workflows</h1>

        <div className="ml-auto">
          <CreateWorkflowDialog />
        </div>
      </header>

      <div className="p-4">
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>

                <TableHead>Nodes</TableHead>

                <TableHead>Status</TableHead>

                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>

            <TableBody>
              <WorkflowRows />
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
