"use client";

import { assertNever } from "@/shared/lib/assert-never";
import { EVENT_KIND_MAX_LENGTH, eventKindLabel } from "@/entities/inference-model";
import {
  CONFIDENCE_THRESHOLD_LIMITS,
  DETECTION_COUNT_LIMITS,
  type IfElseCondition,
  TEXT_LIMITS,
} from "@/entities/workflow";
import { CONFIDENCE_THRESHOLD_STEP } from "../../../../config/node-catalog";
import { normalizeEventKind } from "../../../../lib/event-kind";
import { useModelCatalog } from "../../../../lib/use-model-catalog";
import { CatalogValueField } from "../../../fields/catalog-value-field";
import { SelectField } from "../../../fields/select-field";
import { EVENT_KIND_OPERATOR_OPTIONS, OBJECT_CLASS_OPERATOR_OPTIONS } from "./condition-options";
import { NumericConditionEditor } from "./numeric-condition-editor";

interface ConditionEditorProps {
  condition: IfElseCondition;
  modelIds: readonly string[];
  onChange: (condition: IfElseCondition) => void;
}

export function ConditionEditor({ condition, modelIds, onChange }: ConditionEditorProps) {
  const { eventKinds, fallbackDescription, isLoading, objectClasses } = useModelCatalog(modelIds);

  switch (condition.field) {
    case "event_kind": {
      const handleOperatorChange = (operator: typeof condition.operator) => {
        onChange({ ...condition, operator });
      };

      const handleValueChange = (value: string | null) => {
        onChange({ ...condition, value });
      };

      return (
        <>
          <SelectField
            id="if-else-operator"
            label="Operator"
            onValueChange={handleOperatorChange}
            options={EVENT_KIND_OPERATOR_OPTIONS}
            value={condition.operator}
          />

          <CatalogValueField
            catalogOptions={eventKinds}
            currentValue={condition.value}
            fallbackDescription={fallbackDescription}
            formatOption={eventKindLabel}
            id="if-else-value"
            isLoading={isLoading}
            label="Event kind"
            maxLength={EVENT_KIND_MAX_LENGTH}
            normalizeManualValue={normalizeEventKind}
            onChange={handleValueChange}
          />
        </>
      );
    }
    case "object_class": {
      const handleOperatorChange = (operator: typeof condition.operator) => {
        onChange({ ...condition, operator });
      };

      const handleValueChange = (value: string | null) => {
        onChange({ ...condition, value: value ?? "" });
      };

      return (
        <>
          <SelectField
            id="if-else-operator"
            label="Operator"
            onValueChange={handleOperatorChange}
            options={OBJECT_CLASS_OPERATOR_OPTIONS}
            value={condition.operator}
          />

          <CatalogValueField
            catalogOptions={objectClasses}
            currentValue={condition.value === "" ? null : condition.value}
            fallbackDescription={fallbackDescription}
            id="if-else-value"
            isLoading={isLoading}
            label="Object class"
            maxLength={TEXT_LIMITS.objectClass}
            normalizeManualValue={truncateObjectClass}
            onChange={handleValueChange}
          />
        </>
      );
    }
    case "detection_count":
      return (
        <NumericConditionEditor
          condition={condition}
          description="Detections in the current event."
          isInteger
          limits={DETECTION_COUNT_LIMITS}
          onChange={onChange}
          valueLabel="Detection count"
        />
      );
    case "max_confidence":
      return (
        <NumericConditionEditor
          condition={condition}
          description="Highest confidence in the current event (0–1)."
          limits={CONFIDENCE_THRESHOLD_LIMITS}
          onChange={onChange}
          step={CONFIDENCE_THRESHOLD_STEP}
          valueLabel="Max confidence"
        />
      );
    default:
      return assertNever(condition);
  }
}

function truncateObjectClass(value: string): string {
  return value.slice(0, TEXT_LIMITS.objectClass);
}
