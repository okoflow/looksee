"use client";

import { AREA_FRACTION_LIMITS, type NumericLimits } from "@/entities/workflow";
import { BoundedNumberField } from "../../fields/bounded-number-field";
import type { NodeFormProps } from "../../form-props";

const PERCENT_SCALE = 100;
const PERCENT_DECIMALS = 10;

const AREA_PERCENT_LIMITS: NumericLimits = {
  min: AREA_FRACTION_LIMITS.min * PERCENT_SCALE,
  max: AREA_FRACTION_LIMITS.max * PERCENT_SCALE,
};

function toPercent(fraction: number): number {
  return Math.round(fraction * PERCENT_SCALE * PERCENT_DECIMALS) / PERCENT_DECIMALS;
}

function toFraction(percent: number): number {
  return percent / PERCENT_SCALE;
}

export function SizeFilterForm({ data, onChange }: NodeFormProps<"size_filter">) {
  const handleMinAreaCommit = (percent: number) => {
    const minArea = toFraction(percent);

    onChange({ ...data, min_area: minArea, max_area: Math.max(data.max_area, minArea) });
  };

  const handleMaxAreaCommit = (percent: number) => {
    const maxArea = toFraction(percent);

    onChange({ ...data, min_area: Math.min(data.min_area, maxArea), max_area: maxArea });
  };

  return (
    <>
      <BoundedNumberField
        description="Bounding-box area relative to the frame."
        id="size-min-area"
        label="Minimum area (%)"
        limits={AREA_PERCENT_LIMITS}
        onCommit={handleMinAreaCommit}
        step={0.1}
        value={toPercent(data.min_area)}
      />

      <BoundedNumberField
        description="Bounds adjust each other to keep minimum ≤ maximum."
        id="size-max-area"
        label="Maximum area (%)"
        limits={AREA_PERCENT_LIMITS}
        onCommit={handleMaxAreaCommit}
        step={0.1}
        value={toPercent(data.max_area)}
      />
    </>
  );
}
