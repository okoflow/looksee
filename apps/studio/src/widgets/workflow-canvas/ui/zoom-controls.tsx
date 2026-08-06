"use client";

import { Panel, useReactFlow } from "@xyflow/react";
import { MinusIcon, PlusIcon } from "lucide-react";
import { Button } from "@/shared/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/shared/ui/tooltip";

export function ZoomControls() {
  const { zoomIn, zoomOut } = useReactFlow();

  const handleZoomIn = () => {
    zoomIn({ duration: 150 });
  };

  const handleZoomOut = () => {
    zoomOut({ duration: 150 });
  };

  return (
    <Panel
      className="mr-[calc(var(--spacing-editor-inspector)_+_var(--spacing-editor-gutter)*2)] mb-editor-gutter flex items-center gap-1 rounded-md border bg-card p-1 shadow-xs"
      position="bottom-right"
    >
      <Tooltip>
        <TooltipTrigger
          render={<Button aria-label="Zoom out" onClick={handleZoomOut} size="icon-sm" variant="ghost" />}
        >
          <MinusIcon />
        </TooltipTrigger>

        <TooltipContent>Zoom out</TooltipContent>
      </Tooltip>

      <Tooltip>
        <TooltipTrigger render={<Button aria-label="Zoom in" onClick={handleZoomIn} size="icon-sm" variant="ghost" />}>
          <PlusIcon />
        </TooltipTrigger>

        <TooltipContent>Zoom in</TooltipContent>
      </Tooltip>
    </Panel>
  );
}
