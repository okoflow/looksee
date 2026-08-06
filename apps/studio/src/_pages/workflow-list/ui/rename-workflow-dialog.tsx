"use client";

import { type FormEventHandler, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/shared/ui/button";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/shared/ui/dialog";
import { Input } from "@/shared/ui/input";
import { useUpdateWorkflow } from "@/entities/workflow";

interface RenameWorkflowDialogProps {
  id: string;
  name: string;
  onOpenChange: (open: boolean) => void;
  open: boolean;
}

export function RenameWorkflowDialog({ id, name, onOpenChange, open }: RenameWorkflowDialogProps) {
  const [draftName, setDraftName] = useState(name);

  const renameWorkflow = useUpdateWorkflow(id, {
    onSuccess: () => {
      onOpenChange(false);
    },
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const handleOpenChange = (nextOpen: boolean) => {
    if (nextOpen) {
      setDraftName(name);
    }

    onOpenChange(nextOpen);
  };

  const handleSubmit: FormEventHandler<HTMLFormElement> = (event) => {
    event.preventDefault();

    const trimmedName = draftName.trim();

    if (trimmedName.length === 0 || trimmedName === name) {
      onOpenChange(false);

      return;
    }

    renameWorkflow.mutate({ name: trimmedName });
  };

  return (
    <Dialog onOpenChange={handleOpenChange} open={open}>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Rename workflow</DialogTitle>
        </DialogHeader>

        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <Input
            aria-label="Workflow name"
            maxLength={128}
            onChange={(event) => {
              setDraftName(event.currentTarget.value);
            }}
            value={draftName}
          />

          <DialogFooter>
            <Button
              onClick={() => {
                onOpenChange(false);
              }}
              type="button"
              variant="outline"
            >
              Cancel
            </Button>

            <Button disabled={renameWorkflow.isPending} type="submit">
              Rename
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
