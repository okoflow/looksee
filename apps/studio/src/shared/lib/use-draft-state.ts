"use client";

import { useState } from "react";

interface DraftState {
  draft: string;
  resetDraft: () => void;
  setDraft: (draft: string) => void;
}

export function useDraftState(value: string): DraftState {
  const [draft, setDraft] = useState(value);
  const [lastValue, setLastValue] = useState(value);

  if (lastValue !== value) {
    setLastValue(value);
    setDraft(value);
  }

  const resetDraft = () => {
    setDraft(value);
  };

  return { draft, resetDraft, setDraft };
}
