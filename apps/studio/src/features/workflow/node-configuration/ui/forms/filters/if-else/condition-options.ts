import type { IfElseCondition } from "@/entities/workflow";
import type { IfElseConditionField, NumericCondition } from "../../../../model/if-else";
import type { SelectOption } from "../../../fields/select-field";

type NumericOperator = NumericCondition["operator"];
type EventKindOperator = Extract<IfElseCondition, { field: "event_kind" }>["operator"];
type ObjectClassOperator = Extract<IfElseCondition, { field: "object_class" }>["operator"];

export const CONDITION_FIELD_OPTIONS: readonly SelectOption<IfElseConditionField>[] = [
  { value: "event_kind", label: "Event kind" },
  { value: "object_class", label: "Object class" },
  { value: "detection_count", label: "Detection count" },
  { value: "max_confidence", label: "Max confidence" },
];

export const EVENT_KIND_OPERATOR_OPTIONS: readonly SelectOption<EventKindOperator>[] = [
  { value: "is", label: "Is" },
  { value: "is_not", label: "Is not" },
];

export const OBJECT_CLASS_OPERATOR_OPTIONS: readonly SelectOption<ObjectClassOperator>[] = [
  { value: "contains", label: "Contains" },
  { value: "not_contains", label: "Does not contain" },
];

export const NUMERIC_OPERATOR_OPTIONS: readonly SelectOption<NumericOperator>[] = [
  { value: "eq", label: "Equals" },
  { value: "neq", label: "Does not equal" },
  { value: "gt", label: "Greater than" },
  { value: "gte", label: "At least" },
  { value: "lt", label: "Less than" },
  { value: "lte", label: "At most" },
];
