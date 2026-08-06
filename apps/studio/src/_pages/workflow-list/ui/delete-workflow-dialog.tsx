"use client";

import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/shared/ui/alert-dialog";
import { useDeleteWorkflow } from "@/entities/workflow";

interface DeleteWorkflowDialogProps {
  id: string;
  name: string;
  onOpenChange(open: boolean): void;
  open: boolean;
}

export function DeleteWorkflowDialog({ id, name, open, onOpenChange }: DeleteWorkflowDialogProps) {
  const deleteWorkflow = useDeleteWorkflow({
    onSuccess: () => {
      toast.success(`Deleted ${name}`);

      onOpenChange(false);
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const handleDelete = () => {
    return deleteWorkflow.mutate(id);
  };

  return (
    <AlertDialog onOpenChange={onOpenChange} open={open}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete workflow “{name}”?</AlertDialogTitle>

          <AlertDialogDescription>
            This removes the workflow and its cameras. Past alerts stay in history.
          </AlertDialogDescription>
        </AlertDialogHeader>

        <AlertDialogFooter>
          <AlertDialogCancel variant="ghost">Cancel</AlertDialogCancel>

          <AlertDialogAction disabled={deleteWorkflow.isPending} onClick={handleDelete} variant="destructive">
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
