import { atom } from "jotai";

export type EditorTool = "select" | "pan" | "comment";

export const activeToolAtom = atom<EditorTool>("select");

export function isEditorTool(value: unknown): value is EditorTool {
  return value === "select" || value === "pan" || value === "comment";
}
