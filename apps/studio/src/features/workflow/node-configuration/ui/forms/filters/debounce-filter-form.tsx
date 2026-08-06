"use client";

import { DURATION_SECONDS_LIMITS } from "@/entities/workflow";
import { BoundedNumberField } from "../../fields/bounded-number-field";
import type { NodeFormProps } from "../../form-props";

export function DebounceFilterForm({ data, onChange }: NodeFormProps<"debounce_filter">) {
  const handleSecondsCommit = (seconds: number) => {
    onChange({ ...data, seconds });
  };

  return (
    <BoundedNumberField
      description="Suppress repeated events from the same camera."
      id="debounce-seconds"
      isInteger
      label="Seconds"
      limits={DURATION_SECONDS_LIMITS}
      onCommit={handleSecondsCommit}
      value={data.seconds}
    />
  );
}
