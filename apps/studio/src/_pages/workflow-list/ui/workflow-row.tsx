"use client";

import { MoreHorizontalIcon, PencilIcon, PenLineIcon, Trash2Icon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { workflowRoute } from "@/shared/routes";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/shared/ui/dropdown-menu";
import { TableCell, TableRow } from "@/shared/ui/table";
import type { Workflow } from "@/entities/workflow";
import { DeleteWorkflowDialog } from "./delete-workflow-dialog";
import { RenameWorkflowDialog } from "./rename-workflow-dialog";

interface WorkflowRowProps {
  workflow: Workflow;
}

export function WorkflowRow({ workflow }: WorkflowRowProps) {
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isRenameDialogOpen, setIsRenameDialogOpen] = useState(false);

  const handleDeleteClick = () => {
    setIsDeleteDialogOpen(true);
  };

  const handleRenameClick = () => {
    setIsRenameDialogOpen(true);
  };

  return (
    <TableRow>
      <TableCell className="font-medium">
        <Link className="hover:underline" href={workflowRoute(workflow.id)}>
          {workflow.name}
        </Link>
      </TableCell>

      <TableCell className="text-muted-foreground text-sm">{workflow.graph.nodes.length} nodes</TableCell>

      <TableCell>
        <Badge variant={workflow.enabled ? "secondary" : "outline"}>{workflow.enabled ? "Active" : "Off"}</Badge>
      </TableCell>

      <TableCell className="text-right">
        <DropdownMenu>
          <DropdownMenuTrigger
            render={<Button aria-label={`Actions for ${workflow.name}`} size="icon-sm" variant="ghost" />}
          >
            <MoreHorizontalIcon />
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end">
            <DropdownMenuGroup>
              <DropdownMenuItem render={<Link href={workflowRoute(workflow.id)} />}>
                <PencilIcon />
                Open
              </DropdownMenuItem>

              <DropdownMenuItem onClick={handleRenameClick}>
                <PenLineIcon />
                Rename
              </DropdownMenuItem>
            </DropdownMenuGroup>

            <DropdownMenuSeparator />

            <DropdownMenuGroup>
              <DropdownMenuItem onClick={handleDeleteClick} variant="destructive">
                <Trash2Icon />
                Delete
              </DropdownMenuItem>
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>

        <DeleteWorkflowDialog
          id={workflow.id}
          name={workflow.name}
          onOpenChange={setIsDeleteDialogOpen}
          open={isDeleteDialogOpen}
        />

        <RenameWorkflowDialog
          id={workflow.id}
          name={workflow.name}
          onOpenChange={setIsRenameDialogOpen}
          open={isRenameDialogOpen}
        />
      </TableCell>
    </TableRow>
  );
}
