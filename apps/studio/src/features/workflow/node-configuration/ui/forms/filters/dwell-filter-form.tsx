"use client";

import type { NormalizedPolygon } from "@/shared/lib/geometry";
import { Field } from "@/shared/ui/field";
import { HintedFieldLabel } from "@/shared/ui/hint";
import { DURATION_SECONDS_LIMITS } from "@/entities/workflow";
import { BoundedNumberField } from "../../fields/bounded-number-field";
import { PointsPad } from "../../fields/points-pad";
import type { NodeFormProps } from "../../form-props";

export function DwellFilterForm({ data, onChange, upstreamSource }: NodeFormProps<"dwell_filter">) {
  const handlePolygonChange = (polygon: NormalizedPolygon) => {
    onChange({ ...data, polygon });
  };

  const handleMinSecondsCommit = (minSeconds: number) => {
    onChange({ ...data, min_seconds: minSeconds });
  };

  return (
    <>
      <Field>
        <HintedFieldLabel hint="The object must stay inside this polygon.">Zone</HintedFieldLabel>

        <PointsPad
          ariaLabel="Dwell zone drawing pad"
          emptyLabel="not set"
          onChange={handlePolygonChange}
          points={data.polygon}
          previewTitle="Dwell zone on camera preview"
          shape="polygon"
          unitLabel="corners"
          upstreamSource={upstreamSource ?? null}
        />
      </Field>

      <BoundedNumberField
        id="dwell-min-seconds"
        isInteger
        label="Minimum duration (seconds)"
        limits={DURATION_SECONDS_LIMITS}
        onCommit={handleMinSecondsCommit}
        value={data.min_seconds}
      />
    </>
  );
}
