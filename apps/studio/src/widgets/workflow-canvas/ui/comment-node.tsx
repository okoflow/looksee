"use client";

import type { NodeProps } from "@xyflow/react";
import { useSetAtom } from "jotai";
import { XIcon } from "lucide-react";
import { type ChangeEventHandler, type KeyboardEventHandler, useRef, useState } from "react";
import { cn } from "@/shared/lib/cn";
import { useDraftState } from "@/shared/lib/use-draft-state";
import { Button } from "@/shared/ui/button";
import { TEXT_LIMITS } from "@/entities/workflow";
import { type CommentFlowNode, deleteNodeAtom, updateCommentTextAtom } from "@/features/workflow/graph-editing";

export function CommentNode({ data, id, selected }: NodeProps<CommentFlowNode>) {
  const updateCommentText = useSetAtom(updateCommentTextAtom);
  const deleteNode = useSetAtom(deleteNodeAtom);

  const [isEditing, setIsEditing] = useState(false);
  const isCancelingRef = useRef(false);

  const { draft, setDraft } = useDraftState(data.text);

  const handleChange: ChangeEventHandler<HTMLTextAreaElement> = (event) => {
    setDraft(event.currentTarget.value);
  };

  const handleDoubleClick = () => {
    setIsEditing(true);
  };

  const handleBlur = () => {
    setIsEditing(false);

    if (isCancelingRef.current) {
      isCancelingRef.current = false;

      return;
    }

    if (draft !== data.text) {
      updateCommentText({ commentId: id, text: draft });
    }
  };

  const handleKeyDown: KeyboardEventHandler<HTMLTextAreaElement> = (event) => {
    if (event.key === "Escape") {
      isCancelingRef.current = true;

      setDraft(data.text);
      setIsEditing(false);
    }
  };

  const handleTextareaMount = (element: HTMLTextAreaElement | null) => {
    if (element) {
      element.focus();
      element.setSelectionRange(element.value.length, element.value.length);
    }
  };

  const handleDelete = () => {
    deleteNode(id);
  };

  return (
    <div
      className={cn(
        "group/comment relative w-56 rounded-lg border border-amber-200 bg-amber-50 transition-shadow",
        selected && "ring-2 ring-amber-300/60"
      )}
      onDoubleClick={handleDoubleClick}
    >
      {isEditing ? (
        <textarea
          aria-label="Comment text"
          className="nodrag nowheel block min-h-16 w-full resize-none bg-transparent p-3 pr-8 text-amber-900 text-sm outline-none placeholder:text-amber-900/35"
          maxLength={TEXT_LIMITS.commentText}
          onBlur={handleBlur}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="Comment…"
          ref={handleTextareaMount}
          value={draft}
        />
      ) : (
        <p className="min-h-16 w-full whitespace-pre-wrap break-words p-3 pr-8 text-amber-900 text-sm">
          {data.text.length > 0 ? data.text : <span className="text-amber-900/35">Double-click to edit…</span>}
        </p>
      )}

      <Button
        aria-label="Delete comment"
        className={cn(
          "nodrag absolute top-1 right-1 text-amber-900/45 opacity-0 transition-opacity hover:bg-amber-900/10 hover:text-amber-900 group-hover/comment:opacity-100",
          selected && "opacity-100"
        )}
        onClick={handleDelete}
        size="icon-xs"
        variant="ghost"
      >
        <XIcon />
      </Button>
    </div>
  );
}
