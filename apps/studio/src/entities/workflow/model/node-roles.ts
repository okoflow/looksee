import type { NodeKind } from "./schema";

export type NodeRole = "source" | "detect" | "filter" | "action";

export const NODE_ROLES = {
  camera_source: "source",
  detect: "detect",
  if_else_filter: "filter",
  zone_filter: "filter",
  class_filter: "filter",
  debounce_filter: "filter",
  time_window_filter: "filter",
  line_crossing_filter: "filter",
  dwell_filter: "filter",
  count_threshold_filter: "filter",
  size_filter: "filter",
  telegram_action: "action",
  webhook_action: "action",
  log_alert_action: "action",
  snapshot_action: "action",
  email_action: "action",
  mqtt_action: "action",
  discord_action: "action",
  slack_action: "action",
} as const satisfies Record<NodeKind, NodeRole>;
