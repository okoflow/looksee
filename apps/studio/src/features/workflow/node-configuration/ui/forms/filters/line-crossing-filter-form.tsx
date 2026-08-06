"use client";

import type { NormalizedPolygon } from "@/shared/lib/geometry";
import { Field } from "@/shared/ui/field";
import { HintedFieldLabel } from "@/shared/ui/hint";
import { PointsPad } from "../../fields/points-pad";
import { SelectField, type SelectOption } from "../../fields/select-field";
import type { NodeFormProps } from "../../form-props";

type CrossingDirection = NodeFormProps<"line_crossing_filter">["data"]["direction"];

const CROSSING_DIRECTION_OPTIONS: readonly SelectOption<CrossingDirection>[] = [
  { label: "Any", value: "any" },
  { label: "In (left → right of the line)", value: "in" },
  { label: "Out (right → left of the line)", value: "out" },
];

export function LineCrossingFilterForm({ data, onChange, upstreamSource }: NodeFormProps<"line_crossing_filter">) {
  const handleLineChange = (line: NormalizedPolygon) => {
    onChange({ ...data, line });
  };

  const handleDirectionChange = (direction: CrossingDirection) => {
    onChange({ ...data, direction });
  };

  return (
    <>
      <Field>
        <HintedFieldLabel hint="Click two points to draw.">Line</HintedFieldLabel>

        <PointsPad
          ariaLabel="Line drawing pad"
          emptyLabel="not set"
          maxPoints={2}
          onChange={handleLineChange}
          points={data.line}
          previewTitle="Line on camera preview"
          shape="line"
          unitLabel="points"
          upstreamSource={upstreamSource ?? null}
        />
      </Field>

      <SelectField
        description="Based on the line's point order."
        id="line-crossing-direction"
        label="Direction"
        onValueChange={handleDirectionChange}
        options={CROSSING_DIRECTION_OPTIONS}
        value={data.direction}
      />
    </>
  );
}
