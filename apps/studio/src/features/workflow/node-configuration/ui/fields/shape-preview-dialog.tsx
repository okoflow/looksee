"use client";

import { Redo2Icon, Trash2Icon } from "lucide-react";
import { type NormalizedPolygon, usePointsEditor } from "@/shared/lib/geometry";
import { Button } from "@/shared/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/shared/ui/dialog";
import { assetContentUrl } from "@/entities/asset";
import type { CameraSourceNodeData } from "@/entities/workflow";
import { ShapeEditorSurface } from "./shape-editor-surface";

interface ShapePreviewDialogProps {
  ariaLabel: string;
  emptyLabel: string;
  maxPoints?: number;
  onChange: (points: NormalizedPolygon) => void;
  onOpenChange: (open: boolean) => void;
  open: boolean;
  points: NormalizedPolygon;
  shape: "line" | "polygon";
  title: string;
  unitLabel: string;
  upstreamSource: CameraSourceNodeData | null;
}

export function ShapePreviewDialog({
  ariaLabel,
  emptyLabel,
  maxPoints,
  onChange,
  onOpenChange,
  open,
  points,
  shape,
  title,
  unitLabel,
  upstreamSource,
}: ShapePreviewDialogProps) {
  const { clearPoints, removeLastPoint } = usePointsEditor({ maxPoints, onChange, points });

  const isFilePreview = upstreamSource?.source_type === "file" && upstreamSource.url.length > 0;

  const pointsLabel = points.length > 0 ? `${points.length} ${unitLabel}` : emptyLabel;

  const handleDone = () => {
    onOpenChange(false);
  };

  return (
    <Dialog onOpenChange={onOpenChange} open={open}>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>

          <DialogDescription>Click to add a point, drag to move it, double-click to remove.</DialogDescription>
        </DialogHeader>

        <div className="relative aspect-[16/9] w-full overflow-hidden rounded-lg border bg-black">
          {isFilePreview ? (
            <video
              autoPlay
              className="absolute inset-0 h-full w-full object-contain"
              loop
              muted
              playsInline
              src={assetContentUrl(upstreamSource.url)}
            />
          ) : (
            <span className="absolute inset-0 flex items-center justify-center px-8 text-center text-muted-foreground text-sm">
              No file preview for this camera — draw on the frame; the Monitor page shows it over the live stream.
            </span>
          )}

          <ShapeEditorSurface
            ariaLabel={ariaLabel}
            className="absolute inset-0"
            isEscapeClearing={false}
            maxPoints={maxPoints}
            onChange={onChange}
            points={points}
            shape={shape}
          />
        </div>

        <div className="flex items-center gap-1">
          <Button disabled={points.length === 0} onClick={removeLastPoint} size="sm" variant="ghost">
            <Redo2Icon className="-scale-x-100" data-icon="inline-start" />
            Undo
          </Button>

          <Button disabled={points.length === 0} onClick={clearPoints} size="sm" variant="ghost">
            <Trash2Icon data-icon="inline-start" />
            Clear
          </Button>

          <span className="ml-auto text-muted-foreground text-xs">{pointsLabel}</span>

          <Button onClick={handleDone} size="sm">
            Done
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
