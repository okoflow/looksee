import { assertNever } from "@/shared/lib/assert-never";
import { eventKindLabel } from "@/entities/inference-model";
import { type NodeData, SOURCE_TYPE_LABELS } from "@/entities/workflow";
import type { NumericCondition } from "../model/if-else";

export function summarizeNodeData(config: NodeData): string {
  switch (config.kind) {
    case "camera_source":
      return `${config.name} · ${SOURCE_TYPE_LABELS[config.source_type]}`;
    case "detect":
      return summarizeDetect(config);
    case "if_else_filter":
      return summarizeIfElseCondition(config.condition);
    case "zone_filter":
      return config.polygon.length > 0 ? `${config.polygon.length} points` : "no polygon";
    case "class_filter":
      return config.classes.length > 0 ? config.classes.join(", ") : "any class";
    case "debounce_filter":
      return `${config.seconds}s`;
    case "time_window_filter":
      return summarizeTimeWindow(config);
    case "line_crossing_filter":
      return config.line.length === 2 ? `${config.direction} direction` : "no line";
    case "dwell_filter":
      return `${config.min_seconds}s · ${polygonLabel(config.polygon.length, "no polygon")}`;
    case "count_threshold_filter":
      return `count ${config.operator === "gte" ? "≥" : "≤"} ${config.count} · ${polygonLabel(
        config.polygon.length,
        "whole frame"
      )}`;
    case "size_filter":
      return `${Math.round(config.min_area * 100)}–${Math.round(config.max_area * 100)}% area`;
    case "webhook_action":
      return textOrPlaceholder(config.url, "no url");
    case "log_alert_action":
      return config.cooldown_seconds > 0
        ? `${config.severity} · ${config.cooldown_seconds}s cooldown`
        : config.severity;
    case "snapshot_action":
      return config.annotate ? "annotated frame" : "raw frame";
    case "telegram_action":
    case "email_action":
    case "mqtt_action":
    case "discord_action":
    case "slack_action":
      return summarizeCredentialAction(config);
    default:
      return assertNever(config);
  }
}

type CredentialActionData = Extract<
  NodeData,
  { kind: "telegram_action" | "email_action" | "mqtt_action" | "discord_action" | "slack_action" }
>;

function summarizeCredentialAction(config: CredentialActionData): string {
  if (config.credential_id === "") {
    return "no credential";
  }

  switch (config.kind) {
    case "telegram_action":
      return textOrPlaceholder(config.chat_id, "no chat");
    case "email_action":
      return textOrPlaceholder(config.to, "no recipient");
    case "mqtt_action":
      return textOrPlaceholder(config.topic, "no topic");
    case "discord_action":
    case "slack_action":
      return "credential linked";
    default:
      return assertNever(config);
  }
}

function summarizeTimeWindow(config: Extract<NodeData, { kind: "time_window_filter" }>): string {
  const window = `${padHour(config.start_hour)}:00–${padHour(config.end_hour)}:00`;
  const prefix = config.invert ? "outside " : "";
  const days = config.weekdays.length > 0 && config.weekdays.length < 7 ? ` · ${config.weekdays.length} days` : "";

  return `${prefix}${window}${days}`;
}

function polygonLabel(pointCount: number, emptyLabel: string): string {
  return pointCount > 0 ? `${pointCount} points` : emptyLabel;
}

function summarizeDetect(config: Extract<NodeData, { kind: "detect" }>): string {
  if (config.model_id === null) {
    return "No model selected";
  }

  if (config.event_kinds.length === 0) {
    return `${config.model_id} · all events`;
  }

  return `${config.model_id} · ${config.event_kinds.map(eventKindLabel).join(", ")}`;
}

function summarizeIfElseCondition(condition: Extract<NodeData, { kind: "if_else_filter" }>["condition"]): string {
  switch (condition.field) {
    case "event_kind":
      return condition.value === null
        ? "event kind not configured"
        : `event ${condition.operator === "is" ? "is" : "is not"} ${eventKindLabel(condition.value)}`;
    case "object_class":
      return condition.value === ""
        ? "object class not configured"
        : `class ${condition.operator === "contains" ? "contains" : "excludes"} ${condition.value}`;
    case "detection_count":
      return `detections ${operatorSymbol(condition.operator)} ${condition.value}`;
    case "max_confidence":
      return `confidence ${operatorSymbol(condition.operator)} ${Math.round(condition.value * 100)}%`;
    default:
      return assertNever(condition);
  }
}

function operatorSymbol(operator: NumericCondition["operator"]): string {
  switch (operator) {
    case "eq":
      return "=";
    case "neq":
      return "≠";
    case "gt":
      return ">";
    case "gte":
      return "≥";
    case "lt":
      return "<";
    case "lte":
      return "≤";
    default:
      return assertNever(operator);
  }
}

function textOrPlaceholder(text: string, placeholder: string): string {
  return text === "" ? placeholder : text;
}

function padHour(hour: number): string {
  return hour.toString().padStart(2, "0");
}
