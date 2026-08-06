"use client";

import type { KeyboardEvent, MouseEvent } from "react";
import { type NormalizedPoint, type NormalizedPolygon, pointerToNormalizedPoint } from "./normalized-point";

type EditingKey = "Backspace" | "Escape";

const EDITING_KEY_HANDLERS: Record<EditingKey, (points: NormalizedPolygon) => NormalizedPolygon> = {
  Backspace: (points) => {
    return points.slice(0, -1);
  },
  Escape: () => {
    return [];
  },
};

function isEditingKey(key: string): key is EditingKey {
  return key in EDITING_KEY_HANDLERS;
}

interface UsePointsEditorArgs {
  maxPoints?: number;
  onChange: (points: NormalizedPolygon) => void;
  points: NormalizedPolygon;
}

interface PointsEditor {
  clearPoints: () => void;
  handleClick: (event: MouseEvent<Element>) => void;
  handleKeyDown: (event: KeyboardEvent<Element>) => void;
  movePoint: (index: number, point: NormalizedPoint) => void;
  removeLastPoint: () => void;
  removePoint: (index: number) => void;
}

export function usePointsEditor({ maxPoints, onChange, points }: UsePointsEditorArgs): PointsEditor {
  const handleClick = (event: MouseEvent<Element>) => {
    if (maxPoints !== undefined && points.length >= maxPoints) {
      return;
    }

    const point = pointerToNormalizedPoint(event, event.currentTarget.getBoundingClientRect());

    onChange([...points, point]);
  };

  const handleKeyDown = (event: KeyboardEvent<Element>) => {
    if (!isEditingKey(event.key)) {
      return;
    }

    event.preventDefault();

    onChange(EDITING_KEY_HANDLERS[event.key](points));
  };

  const movePoint = (index: number, point: NormalizedPoint) => {
    onChange(
      points.map((current, currentIndex) => {
        return currentIndex === index ? point : current;
      })
    );
  };

  const removePoint = (index: number) => {
    onChange(
      points.filter((_, currentIndex) => {
        return currentIndex !== index;
      })
    );
  };

  return {
    handleClick,
    handleKeyDown,
    movePoint,
    removePoint,
    removeLastPoint: () => {
      onChange(EDITING_KEY_HANDLERS.Backspace(points));
    },
    clearPoints: () => {
      onChange(EDITING_KEY_HANDLERS.Escape(points));
    },
  };
}
