"use client";

import type { KeyboardEvent } from "react";
import { useDraftState } from "@/shared/lib/use-draft-state";

type DraftEditingKey = "Enter" | "Escape";

const DRAFT_KEY_HANDLERS: Record<
  DraftEditingKey,
  (event: KeyboardEvent<HTMLInputElement>, resetDraft: () => void) => void
> = {
  Enter: (event) => {
    event.currentTarget.blur();
  },
  Escape: (_event, resetDraft) => {
    resetDraft();
  },
};

function isDraftEditingKey(key: string): key is DraftEditingKey {
  return key in DRAFT_KEY_HANDLERS;
}

interface DraftValue {
  draft: string;
  handleKeyDown: (event: KeyboardEvent<HTMLInputElement>) => void;
  resetDraft: () => void;
  setDraft: (draft: string) => void;
}

export function useDraftValue(value: string): DraftValue {
  const { draft, resetDraft, setDraft } = useDraftState(value);

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (isDraftEditingKey(event.key)) {
      DRAFT_KEY_HANDLERS[event.key](event, resetDraft);
    }
  };

  return { draft, handleKeyDown, resetDraft, setDraft };
}
