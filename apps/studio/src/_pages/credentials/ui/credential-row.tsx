"use client";

import { MoreHorizontalIcon, PencilIcon, Trash2Icon } from "lucide-react";
import { useState } from "react";
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
import { CREDENTIAL_TYPE_LABELS, type Credential } from "@/entities/credential";
import { DeleteCredentialDialog, EditCredentialDialog } from "@/features/credentials/manage-credentials";

interface CredentialRowProps {
  credential: Credential;
}

export function CredentialRow({ credential }: CredentialRowProps) {
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);

  const handleEditClick = () => {
    setIsEditDialogOpen(true);
  };

  const handleDeleteClick = () => {
    setIsDeleteDialogOpen(true);
  };

  return (
    <TableRow>
      <TableCell className="font-medium">{credential.name}</TableCell>

      <TableCell>
        <Badge variant="secondary">{CREDENTIAL_TYPE_LABELS[credential.type]}</Badge>
      </TableCell>

      <TableCell className="text-muted-foreground">{credential.summary}</TableCell>

      <TableCell className="text-right">
        <DropdownMenu>
          <DropdownMenuTrigger
            render={<Button aria-label={`Actions for ${credential.name}`} size="icon-sm" variant="ghost" />}
          >
            <MoreHorizontalIcon />
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end">
            <DropdownMenuGroup>
              <DropdownMenuItem onClick={handleEditClick}>
                <PencilIcon />
                Edit
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

        <EditCredentialDialog credential={credential} onOpenChange={setIsEditDialogOpen} open={isEditDialogOpen} />

        <DeleteCredentialDialog
          credential={credential}
          onOpenChange={setIsDeleteDialogOpen}
          open={isDeleteDialogOpen}
        />
      </TableCell>
    </TableRow>
  );
}
