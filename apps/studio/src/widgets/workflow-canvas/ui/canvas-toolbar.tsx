"use client";

import { Panel } from "@xyflow/react";
import { useAtom, useAtomValue, useSetAtom } from "jotai";
import { HandIcon, MessageSquarePlusIcon, MousePointer2Icon, Redo2Icon, Undo2Icon } from "lucide-react";
import type { ComponentType, SVGProps } from "react";
import { Button } from "@/shared/ui/button";
import { Separator } from "@/shared/ui/separator";
import { ToggleGroup, ToggleGroupItem } from "@/shared/ui/toggle-group";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/shared/ui/tooltip";
import {
  activeToolAtom,
  canRedoAtom,
  canUndoAtom,
  type EditorTool,
  isEditorTool,
  redoAtom,
  undoAtom,
} from "@/features/workflow/graph-editing";

interface ToolItem {
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  label: string;
  tool: EditorTool;
}

const TOOL_ITEMS: readonly ToolItem[] = [
  { tool: "select", label: "Select (V)", icon: MousePointer2Icon },
  { tool: "pan", label: "Pan (H)", icon: HandIcon },
  { tool: "comment", label: "Comment (C)", icon: MessageSquarePlusIcon },
];

export function CanvasToolbar() {
  const [activeTool, setActiveTool] = useAtom(activeToolAtom);
  const canUndo = useAtomValue(canUndoAtom);
  const canRedo = useAtomValue(canRedoAtom);
  const undo = useSetAtom(undoAtom);
  const redo = useSetAtom(redoAtom);

  const handleToolChange = (value: unknown[]) => {
    const [tool] = value;

    if (isEditorTool(tool)) {
      setActiveTool(tool);
    }
  };

  const handleUndo = () => {
    undo();
  };

  const handleRedo = () => {
    redo();
  };

  return (
    <Panel
      className="mb-editor-gutter flex items-center gap-1 rounded-md border bg-card p-1 shadow-xs"
      position="bottom-center"
    >
      <ToggleGroup onValueChange={handleToolChange} size="sm" value={[activeTool]}>
        {TOOL_ITEMS.map((item) => {
          const Icon = item.icon;

          return (
            <Tooltip key={item.tool}>
              <TooltipTrigger render={<ToggleGroupItem aria-label={item.label} value={item.tool} />}>
                <Icon />
              </TooltipTrigger>

              <TooltipContent>{item.label}</TooltipContent>
            </Tooltip>
          );
        })}
      </ToggleGroup>

      <Separator className="h-5" orientation="vertical" />

      <Tooltip>
        <TooltipTrigger
          render={<Button aria-label="Undo" disabled={!canUndo} onClick={handleUndo} size="icon-sm" variant="ghost" />}
        >
          <Undo2Icon />
        </TooltipTrigger>

        <TooltipContent>Undo (⌘Z)</TooltipContent>
      </Tooltip>

      <Tooltip>
        <TooltipTrigger
          render={<Button aria-label="Redo" disabled={!canRedo} onClick={handleRedo} size="icon-sm" variant="ghost" />}
        >
          <Redo2Icon />
        </TooltipTrigger>

        <TooltipContent>Redo (⇧⌘Z)</TooltipContent>
      </Tooltip>
    </Panel>
  );
}
