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
import { type Credential, useDeleteCredential } from "@/entities/credential";

interface DeleteCredentialDialogProps {
  credential: Credential;
  onOpenChange: (open: boolean) => void;
  open: boolean;
}

export function DeleteCredentialDialog({ credential, onOpenChange, open }: DeleteCredentialDialogProps) {
  const deleteCredential = useDeleteCredential({
    onSuccess: () => {
      toast.success(`Deleted ${credential.name}`);

      onOpenChange(false);
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  return (
    <AlertDialog onOpenChange={onOpenChange} open={open}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete credential “{credential.name}”?</AlertDialogTitle>

          <AlertDialogDescription>
            Actions that reference it stop delivering until they are pointed at another credential.
          </AlertDialogDescription>
        </AlertDialogHeader>

        <AlertDialogFooter>
          <AlertDialogCancel variant="ghost">Cancel</AlertDialogCancel>

          <AlertDialogAction
            disabled={deleteCredential.isPending}
            onClick={() => {
              deleteCredential.mutate(credential.id);
            }}
            variant="destructive"
          >
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
