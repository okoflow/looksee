"use client";

import { type KeyboardEventHandler, useState } from "react";
import { toast } from "sonner";
import { Input } from "@/shared/ui/input";
import { useUpdateWorkflow, type Workflow } from "@/entities/workflow";

interface WorkflowNameEditorProps {
  workflow: Workflow;
}

export function WorkflowNameEditor({ workflow }: WorkflowNameEditorProps) {
  const [isRenaming, setIsRenaming] = useState(false);
  const [draftName, setDraftName] = useState(workflow.name);

  const renameWorkflow = useUpdateWorkflow(workflow.id, {
    onError: (error) => {
      toast.error(error.message);
    },
  });

  const handleNameClick = () => {
    setDraftName(workflow.name);
    setIsRenaming(true);
  };

  const commitRename = () => {
    setIsRenaming(false);

    const trimmedName = draftName.trim();

    if (trimmedName.length === 0 || trimmedName === workflow.name) {
      return;
    }

    renameWorkflow.mutate({ name: trimmedName });
  };

  const handleKeyDown: KeyboardEventHandler<HTMLInputElement> = (event) => {
    if (event.key === "Enter") {
      commitRename();
    }

    if (event.key === "Escape") {
      setIsRenaming(false);
    }
  };

  if (isRenaming) {
    return (
      <Input
        aria-label="Workflow name"
        className="h-7 w-56"
        maxLength={128}
        onBlur={commitRename}
        onChange={(event) => {
          setDraftName(event.currentTarget.value);
        }}
        onKeyDown={handleKeyDown}
        ref={(element) => {
          element?.select();
        }}
        value={draftName}
      />
    );
  }

  return (
    <button
      className="truncate rounded font-medium transition hover:bg-muted hover:px-1.5"
      onClick={handleNameClick}
      title="Rename workflow"
      type="button"
    >
      {workflow.name}
    </button>
  );
}
