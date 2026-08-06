"use client";

import { ExpandIcon, Redo2Icon, Trash2Icon } from "lucide-react";
import { useState } from "react";
import { type NormalizedPolygon, usePointsEditor } from "@/shared/lib/geometry";
import { Button } from "@/shared/ui/button";
import type { CameraSourceNodeData } from "@/entities/workflow";
import { ShapeEditorSurface } from "./shape-editor-surface";
import { ShapePreviewDialog } from "./shape-preview-dialog";

interface PointsPadProps {
  ariaLabel: string;
  emptyLabel: string;
  maxPoints?: number;
  onChange: (points: NormalizedPolygon) => void;
  points: NormalizedPolygon;
  previewTitle: string;
  shape: "line" | "polygon";
  unitLabel: string;
  upstreamSource: CameraSourceNodeData | null;
}

export function PointsPad({
  ariaLabel,
  emptyLabel,
  maxPoints,
  onChange,
  points,
  previewTitle,
  shape,
  unitLabel,
  upstreamSource,
}: PointsPadProps) {
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);

  const { removeLastPoint, clearPoints } = usePointsEditor({ maxPoints, onChange, points });

  const pointsLabel = points.length > 0 ? `${points.length} ${unitLabel}` : emptyLabel;

  const handleOpenPreview = () => {
    setIsPreviewOpen(true);
  };

  return (
    <>
      <ShapeEditorSurface
        ariaLabel={ariaLabel}
        className="rounded-md border bg-muted"
        maxPoints={maxPoints}
        onChange={onChange}
        points={points}
        shape={shape}
      />

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
      </div>

      <Button onClick={handleOpenPreview} size="sm" variant="outline">
        <ExpandIcon data-icon="inline-start" />
        Edit on preview
      </Button>

      <ShapePreviewDialog
        ariaLabel={ariaLabel}
        emptyLabel={emptyLabel}
        maxPoints={maxPoints}
        onChange={onChange}
        onOpenChange={setIsPreviewOpen}
        open={isPreviewOpen}
        points={points}
        shape={shape}
        title={previewTitle}
        unitLabel={unitLabel}
        upstreamSource={upstreamSource}
      />
    </>
  );
}
