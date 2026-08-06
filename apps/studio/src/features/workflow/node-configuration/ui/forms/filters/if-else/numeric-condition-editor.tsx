"use client";

import type { IfElseCondition, NumericLimits } from "@/entities/workflow";
import type { NumericCondition } from "../../../../model/if-else";
import { BoundedNumberField } from "../../../fields/bounded-number-field";
import { SelectField } from "../../../fields/select-field";
import { NUMERIC_OPERATOR_OPTIONS } from "./condition-options";

interface NumericConditionEditorProps {
  condition: NumericCondition;
  description?: string;
  isInteger?: boolean;
  limits: NumericLimits;
  onChange: (condition: IfElseCondition) => void;
  step?: number;
  valueLabel: string;
}

export function NumericConditionEditor({
  condition,
  description,
  isInteger = false,
  limits,
  onChange,
  step = 1,
  valueLabel,
}: NumericConditionEditorProps) {
  const handleOperatorChange = (operator: NumericCondition["operator"]) => {
    onChange({ ...condition, operator });
  };

  const handleValueCommit = (value: number) => {
    onChange({ ...condition, value });
  };

  return (
    <>
      <SelectField
        id="if-else-operator"
        label="Operator"
        onValueChange={handleOperatorChange}
        options={NUMERIC_OPERATOR_OPTIONS}
        value={condition.operator}
      />

      <BoundedNumberField
        description={description}
        id="if-else-value"
        isInteger={isInteger}
        label={valueLabel}
        limits={limits}
        onCommit={handleValueCommit}
        step={step}
        value={condition.value}
      />
    </>
  );
}
