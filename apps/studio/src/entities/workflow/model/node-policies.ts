import type { NodeRole } from "./node-roles";
import type { NodeKind } from "./schema";

export type OutputPortId = "out" | "if" | "else";

export interface OutputPort {
  id: OutputPortId;
  label?: string;
  maxConnections: number | "many";
  targets: readonly NodeRole[];
}

export interface NodePolicy {
  input: "none" | "many";
  outputs: readonly OutputPort[];
}

const FILTER_TARGET_ROLES: readonly NodeRole[] = ["filter", "action"];

const sourcePolicy: NodePolicy = {
  input: "none",
  outputs: [{ id: "out", maxConnections: 1, targets: ["detect"] }],
};

const detectPolicy: NodePolicy = {
  input: "many",
  outputs: [{ id: "out", maxConnections: "many", targets: FILTER_TARGET_ROLES }],
};

const filterPolicy: NodePolicy = {
  input: "many",
  outputs: [
    { id: "if", label: "If", maxConnections: "many", targets: FILTER_TARGET_ROLES },
    { id: "else", label: "Else", maxConnections: "many", targets: FILTER_TARGET_ROLES },
  ],
};

const snapshotPolicy: NodePolicy = {
  input: "many",
  outputs: [{ id: "out", maxConnections: "many", targets: ["action"] }],
};

const sinkPolicy: NodePolicy = {
  input: "many",
  outputs: [],
};

export const NODE_POLICIES = {
  camera_source: sourcePolicy,
  detect: detectPolicy,
  if_else_filter: filterPolicy,
  zone_filter: filterPolicy,
  class_filter: filterPolicy,
  debounce_filter: filterPolicy,
  time_window_filter: filterPolicy,
  line_crossing_filter: filterPolicy,
  dwell_filter: filterPolicy,
  count_threshold_filter: filterPolicy,
  size_filter: filterPolicy,
  telegram_action: sinkPolicy,
  webhook_action: sinkPolicy,
  log_alert_action: sinkPolicy,
  snapshot_action: snapshotPolicy,
  email_action: sinkPolicy,
  mqtt_action: sinkPolicy,
  discord_action: sinkPolicy,
  slack_action: sinkPolicy,
} as const satisfies Record<NodeKind, NodePolicy>;
