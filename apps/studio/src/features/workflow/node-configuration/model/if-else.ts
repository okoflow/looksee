import type { IfElseCondition } from "@/entities/workflow";

export type IfElseConditionField = IfElseCondition["field"];
export type NumericCondition = Extract<IfElseCondition, { field: "detection_count" | "max_confidence" }>;

export const DEFAULT_CONDITIONS = {
  event_kind: {
    field: "event_kind",
    operator: "is",
    value: null,
  },
  object_class: {
    field: "object_class",
    operator: "contains",
    value: "",
  },
  detection_count: {
    field: "detection_count",
    operator: "gte",
    value: 1,
  },
  max_confidence: {
    field: "max_confidence",
    operator: "gte",
    value: 0.5,
  },
} as const satisfies Record<IfElseConditionField, IfElseCondition>;
