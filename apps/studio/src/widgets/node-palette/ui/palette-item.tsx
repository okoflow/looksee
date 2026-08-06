import { LockIcon } from "lucide-react";
import type { DragEventHandler } from "react";
import { cn } from "@/shared/lib/cn";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/shared/ui/tooltip";
import { NODE_DRAG_MIME } from "@/features/workflow/graph-editing";
import type { NodeDefinition } from "@/features/workflow/node-configuration";

interface PaletteItemProps {
  definition: NodeDefinition;
  locked: boolean;
}

export function PaletteItem({ definition, locked }: PaletteItemProps) {
  const Icon = definition.icon;

  const handleDragStart: DragEventHandler<HTMLDivElement> = (event) => {
    if (locked) {
      event.preventDefault();
      return;
    }

    event.dataTransfer.setData(NODE_DRAG_MIME, definition.kind);
    event.dataTransfer.effectAllowed = "move";
  };

  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <div
            className={cn(
              "flex items-center gap-2 rounded-md border bg-card p-2 text-card-foreground transition",
              locked ? "cursor-not-allowed opacity-60" : "cursor-grab hover:border-ring active:cursor-grabbing"
            )}
            draggable={!locked}
            onDragStart={handleDragStart}
          />
        }
      >
        <div className={cn("flex size-7 shrink-0 items-center justify-center rounded-md", definition.iconClassName)}>
          <Icon className="size-4" />
        </div>

        <span className="truncate font-medium text-sm">{definition.label}</span>

        {locked ? (
          <LockIcon aria-label="Requires a license" className="ml-auto size-3.5 shrink-0 text-muted-foreground" />
        ) : null}
      </TooltipTrigger>

      <TooltipContent side="right">
        {locked ? `${definition.description} Requires a LookSee Enterprise license.` : definition.description}
      </TooltipContent>
    </Tooltip>
  );
}
