"use client";

import type { NormalizedPolygon } from "@/shared/lib/geometry";
import { Field } from "@/shared/ui/field";
import { HintedFieldLabel } from "@/shared/ui/hint";
import { DETECTION_COUNT_LIMITS } from "@/entities/workflow";
import { BoundedNumberField } from "../../fields/bounded-number-field";
import { PointsPad } from "../../fields/points-pad";
import { SelectField, type SelectOption } from "../../fields/select-field";
import type { NodeFormProps } from "../../form-props";

type CountOperator = NodeFormProps<"count_threshold_filter">["data"]["operator"];

const COUNT_OPERATOR_OPTIONS: readonly SelectOption<CountOperator>[] = [
  { label: "At least", value: "gte" },
  { label: "At most", value: "lte" },
];

export function CountThresholdFilterForm({ data, onChange, upstreamSource }: NodeFormProps<"count_threshold_filter">) {
  const handlePolygonChange = (polygon: NormalizedPolygon) => {
    onChange({ ...data, polygon });
  };

  const handleOperatorChange = (operator: CountOperator) => {
    onChange({ ...data, operator });
  };

  const handleCountCommit = (count: number) => {
    onChange({ ...data, count });
  };

  return (
    <>
      <Field>
        <HintedFieldLabel hint="Objects are counted inside this polygon; empty = whole frame.">Zone</HintedFieldLabel>

        <PointsPad
          ariaLabel="Count zone drawing pad"
          emptyLabel="whole frame"
          onChange={handlePolygonChange}
          points={data.polygon}
          previewTitle="Count zone on camera preview"
          shape="polygon"
          unitLabel="corners"
          upstreamSource={upstreamSource ?? null}
        />
      </Field>

      <SelectField
        id="count-threshold-operator"
        label="Condition"
        onValueChange={handleOperatorChange}
        options={COUNT_OPERATOR_OPTIONS}
        value={data.operator}
      />

      <BoundedNumberField
        id="count-threshold-count"
        isInteger
        label="Object count"
        limits={DETECTION_COUNT_LIMITS}
        onCommit={handleCountCommit}
        value={data.count}
      />
    </>
  );
}
