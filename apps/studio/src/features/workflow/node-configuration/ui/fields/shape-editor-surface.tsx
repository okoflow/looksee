"use client";

import { type KeyboardEventHandler, type MouseEvent, type PointerEvent, useRef } from "react";
import { cn } from "@/shared/lib/cn";
import {
  type NormalizedPoint,
  type NormalizedPolygon,
  pointerToNormalizedPoint,
  usePointsEditor,
} from "@/shared/lib/geometry";
import { ShapeOverlay } from "@/entities/workflow";

interface ShapeEditorSurfaceProps {
  ariaLabel: string;
  className?: string;
  isEscapeClearing?: boolean;
  maxPoints?: number;
  onChange: (points: NormalizedPolygon) => void;
  points: NormalizedPolygon;
  shape: "line" | "polygon";
}

export function ShapeEditorSurface({
  ariaLabel,
  className,
  isEscapeClearing = true,
  maxPoints,
  onChange,
  points,
  shape,
}: ShapeEditorSurfaceProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  const { handleClick, handleKeyDown, movePoint, removePoint } = usePointsEditor({ maxPoints, onChange, points });

  const handleSurfaceKeyDown: KeyboardEventHandler<HTMLDivElement> = (event) => {
    if (event.key === "Escape" && !isEscapeClearing) {
      return;
    }

    handleKeyDown(event);
  };

  const handleVertexMove = (index: number, event: PointerEvent<HTMLButtonElement>) => {
    const container = containerRef.current;

    if (container) {
      movePoint(index, pointerToNormalizedPoint(event, container.getBoundingClientRect()));
    }
  };

  return (
    <div
      aria-label={ariaLabel}
      className={cn("relative aspect-[16/9] w-full cursor-crosshair overflow-hidden", className)}
      onClick={handleClick}
      onKeyDown={handleSurfaceKeyDown}
      ref={containerRef}
      role="application"
      // biome-ignore lint/a11y/noNoninteractiveTabindex: the drawing surface needs focus so Backspace/Escape keyboard editing works
      tabIndex={0}
    >
      <ShapeOverlay points={points} shape={shape} />

      {points.map((point, index) => {
        return (
          <VertexHandle
            index={index}
            // biome-ignore lint/suspicious/noArrayIndexKey: point order is stable while dragging, and a value-based key would remount the captured handle mid-drag
            key={`point-${index}`}
            onMove={handleVertexMove}
            onRemove={removePoint}
            point={point}
          />
        );
      })}
    </div>
  );
}

interface VertexHandleProps {
  index: number;
  onMove: (index: number, event: PointerEvent<HTMLButtonElement>) => void;
  onRemove: (index: number) => void;
  point: NormalizedPoint;
}

function VertexHandle({ index, onMove, onRemove, point }: VertexHandleProps) {
  const [x, y] = point;

  const handleClick = (event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
  };

  const handleDoubleClick = (event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    onRemove(index);
  };

  const handlePointerDown = (event: PointerEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event: PointerEvent<HTMLButtonElement>) => {
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      onMove(index, event);
    }
  };

  return (
    <button
      aria-label={`Point ${index + 1} — drag to move, double-click to remove`}
      className="absolute size-3 -translate-x-1/2 -translate-y-1/2 cursor-grab rounded-full border-2 border-background bg-primary shadow-xs active:cursor-grabbing"
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      style={{ left: `${x * 100}%`, top: `${y * 100}%` }}
      type="button"
    />
  );
}
