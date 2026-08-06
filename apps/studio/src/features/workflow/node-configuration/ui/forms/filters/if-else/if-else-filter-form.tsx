"use client";

import type { IfElseCondition } from "@/entities/workflow";
import { DEFAULT_CONDITIONS, type IfElseConditionField } from "../../../../model/if-else";
import { SelectField } from "../../../fields/select-field";
import type { NodeFormProps } from "../../../form-props";
import { ConditionEditor } from "./condition-editor";
import { CONDITION_FIELD_OPTIONS } from "./condition-options";

interface IfElseFilterFormProps extends NodeFormProps<"if_else_filter"> {
  modelIds: readonly string[];
}

export function IfElseFilterForm({ data, modelIds, onChange }: IfElseFilterFormProps) {
  const handleFieldChange = (field: IfElseConditionField) => {
    if (field === data.condition.field) {
      return;
    }

    onChange({ ...data, condition: DEFAULT_CONDITIONS[field] });
  };

  const handleConditionChange = (condition: IfElseCondition) => {
    onChange({ ...data, condition });
  };

  return (
    <>
      <SelectField
        description="Match → If; no match → Else; no event → neither."
        id="if-else-field"
        label="Field"
        onValueChange={handleFieldChange}
        options={CONDITION_FIELD_OPTIONS}
        value={data.condition.field}
      />

      <ConditionEditor condition={data.condition} modelIds={modelIds} onChange={handleConditionChange} />
    </>
  );
}
