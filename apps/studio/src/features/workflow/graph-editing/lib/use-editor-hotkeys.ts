"use client";

import { useSetAtom } from "jotai";
import { useEffect } from "react";
import { redoAtom, undoAtom } from "../model/editor-atoms";
import { activeToolAtom, type EditorTool } from "../model/tool-atoms";

const TOOL_HOTKEYS: Record<string, EditorTool> = {
  v: "select",
  h: "pan",
  c: "comment",
};

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false;
  }

  return (
    target instanceof HTMLInputElement ||
    target instanceof HTMLTextAreaElement ||
    target instanceof HTMLSelectElement ||
    target.isContentEditable
  );
}

type HistoryAction = "redo" | "undo";

function resolveHistoryAction(event: KeyboardEvent): HistoryAction | null {
  if (!(event.metaKey || event.ctrlKey)) {
    return null;
  }

  const key = event.key.toLowerCase();

  if (key === "z") {
    return event.shiftKey ? "redo" : "undo";
  }

  if (key === "y") {
    return "redo";
  }

  return null;
}

function resolveToolHotkey(event: KeyboardEvent): EditorTool | null {
  if (event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) {
    return null;
  }

  return TOOL_HOTKEYS[event.key.toLowerCase()] ?? null;
}

export function useEditorHotkeys() {
  const undo = useSetAtom(undoAtom);
  const redo = useSetAtom(redoAtom);
  const setActiveTool = useSetAtom(activeToolAtom);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (isEditableTarget(event.target)) {
        return;
      }

      const historyAction = resolveHistoryAction(event);

      if (historyAction !== null) {
        event.preventDefault();

        if (historyAction === "redo") {
          redo();
        } else {
          undo();
        }

        return;
      }

      const tool = resolveToolHotkey(event);

      if (tool !== null) {
        setActiveTool(tool);
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [undo, redo, setActiveTool]);
}
