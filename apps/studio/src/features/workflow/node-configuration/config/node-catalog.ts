import {
  ArrowLeftRightIcon,
  BellRingIcon,
  CalendarClockIcon,
  CameraIcon,
  ChartColumnBigIcon,
  HashIcon,
  MailIcon,
  MessageCircleIcon,
  PentagonIcon,
  RadioTowerIcon,
  ScalingIcon,
  ScanSearchIcon,
  SendIcon,
  SplitIcon,
  TagsIcon,
  TimerIcon,
  TimerResetIcon,
  VideoIcon,
  WebhookIcon,
} from "lucide-react";
import type { ComponentType, SVGProps } from "react";
import {
  ENTERPRISE_INTEGRATIONS_FEATURE,
  type LicensedFeature,
  MEASUREMENT_FILTERS_FEATURE,
} from "@/entities/entitlement";
import type { NodeData, NodeKind } from "@/entities/workflow";
import { DEFAULT_CONDITIONS } from "../model/if-else";

export const CONFIDENCE_THRESHOLD_STEP = 0.05;

export type PaletteCategory = "source" | "detection" | "logic" | "object" | "spatial" | "temporal" | "action";

export interface NodeDefinition {
  defaults: NodeData;
  description: string;
  feature?: LicensedFeature;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  iconClassName: string;
  kind: NodeKind;
  label: string;
  paletteCategory: PaletteCategory;
}

const NODE_DEFINITIONS_BY_KIND = {
  camera_source: {
    kind: "camera_source",
    paletteCategory: "source",
    label: "Camera",
    description: "Video input: an RTSP/RTMP/SRT stream, a WHEP server, or a browser webcam.",
    icon: VideoIcon,
    iconClassName: "bg-emerald-500/15 text-emerald-600",
    defaults: {
      kind: "camera_source",
      name: "Camera",
      source_type: "rtsp",
      url: "",
    },
  },
  detect: {
    kind: "detect",
    paletteCategory: "detection",
    label: "Detect",
    description: "Runs a model on frames and emits detection events.",
    icon: ScanSearchIcon,
    iconClassName: "bg-violet-500/15 text-violet-600",
    defaults: {
      kind: "detect",
      model_id: null,
      event_kinds: [],
      confidence_threshold: 0.5,
      inference_fps: 1,
    },
  },
  if_else_filter: {
    kind: "if_else_filter",
    paletteCategory: "logic",
    label: "If / Else",
    description: "Routes each event to the If or Else branch by a condition.",
    icon: SplitIcon,
    iconClassName: "bg-sky-500/15 text-sky-600",
    defaults: {
      kind: "if_else_filter",
      condition: DEFAULT_CONDITIONS.event_kind,
    },
  },
  zone_filter: {
    kind: "zone_filter",
    paletteCategory: "spatial",
    label: "Zone",
    description: "Passes events with detections inside a drawn polygon.",
    icon: PentagonIcon,
    iconClassName: "bg-orange-500/15 text-orange-600",
    defaults: { kind: "zone_filter", polygon: [] },
  },
  class_filter: {
    kind: "class_filter",
    paletteCategory: "object",
    label: "Class",
    description: "Passes events whose object class matches the list.",
    icon: TagsIcon,
    iconClassName: "bg-blue-500/15 text-blue-600",
    defaults: { kind: "class_filter", classes: [] },
  },
  debounce_filter: {
    kind: "debounce_filter",
    paletteCategory: "temporal",
    label: "Debounce",
    description: "Suppresses repeated events for a cooldown period.",
    icon: TimerResetIcon,
    iconClassName: "bg-rose-500/15 text-rose-600",
    defaults: { kind: "debounce_filter", seconds: 30 },
  },
  time_window_filter: {
    kind: "time_window_filter",
    paletteCategory: "temporal",
    label: "Schedule",
    description: "Passes events only within the configured hours and weekdays.",
    icon: CalendarClockIcon,
    iconClassName: "bg-cyan-500/15 text-cyan-600",
    defaults: {
      kind: "time_window_filter",
      start_hour: 8,
      end_hour: 20,
      weekdays: [0, 1, 2, 3, 4],
      invert: false,
    },
  },
  line_crossing_filter: {
    kind: "line_crossing_filter",
    paletteCategory: "spatial",
    feature: MEASUREMENT_FILTERS_FEATURE,
    label: "Line crossing",
    description: "Passes events when a tracked object crosses a drawn line.",
    icon: ArrowLeftRightIcon,
    iconClassName: "bg-amber-500/15 text-amber-600",
    defaults: { kind: "line_crossing_filter", line: [], direction: "any" },
  },
  dwell_filter: {
    kind: "dwell_filter",
    paletteCategory: "temporal",
    feature: MEASUREMENT_FILTERS_FEATURE,
    label: "Dwell",
    description: "Passes events when an object stays in a zone long enough.",
    icon: TimerIcon,
    iconClassName: "bg-pink-500/15 text-pink-600",
    defaults: { kind: "dwell_filter", polygon: [], min_seconds: 60 },
  },
  count_threshold_filter: {
    kind: "count_threshold_filter",
    paletteCategory: "object",
    feature: MEASUREMENT_FILTERS_FEATURE,
    label: "Count",
    description: "Passes events when the detection count crosses a threshold.",
    icon: ChartColumnBigIcon,
    iconClassName: "bg-indigo-500/15 text-indigo-600",
    defaults: {
      kind: "count_threshold_filter",
      polygon: [],
      operator: "gte",
      count: 1,
    },
  },
  size_filter: {
    kind: "size_filter",
    paletteCategory: "object",
    label: "Size",
    description: "Passes events by detection area relative to the frame.",
    icon: ScalingIcon,
    iconClassName: "bg-teal-500/15 text-teal-600",
    defaults: { kind: "size_filter", min_area: 0, max_area: 1 },
  },
  telegram_action: {
    kind: "telegram_action",
    paletteCategory: "action",
    label: "Telegram",
    description: "Sends a Telegram message for each event.",
    icon: SendIcon,
    iconClassName: "bg-sky-500/15 text-sky-600",
    defaults: {
      kind: "telegram_action",
      credential_id: "",
      chat_id: "",
      message_template: "[{kind}] camera={camera_id} at {ts}",
    },
  },
  webhook_action: {
    kind: "webhook_action",
    paletteCategory: "action",
    label: "Webhook",
    description: "Calls an HTTP endpoint with the event payload.",
    icon: WebhookIcon,
    iconClassName: "bg-purple-500/15 text-purple-600",
    defaults: { kind: "webhook_action", url: "", method: "POST" },
  },
  log_alert_action: {
    kind: "log_alert_action",
    paletteCategory: "action",
    label: "Alert",
    description: "Records the event in the alert log.",
    icon: BellRingIcon,
    iconClassName: "bg-red-500/15 text-red-600",
    defaults: { kind: "log_alert_action", severity: "warning", cooldown_seconds: 30 },
  },
  snapshot_action: {
    kind: "snapshot_action",
    paletteCategory: "action",
    label: "Snapshot",
    description: "Saves the current frame; later actions can attach it.",
    icon: CameraIcon,
    iconClassName: "bg-fuchsia-500/15 text-fuchsia-600",
    defaults: { kind: "snapshot_action", annotate: true },
  },
  email_action: {
    kind: "email_action",
    paletteCategory: "action",
    label: "Email",
    description: "Sends an email for each event.",
    icon: MailIcon,
    iconClassName: "bg-green-500/15 text-green-600",
    defaults: {
      kind: "email_action",
      credential_id: "",
      to: "",
      subject_template: "[{kind}] on camera {camera_id}",
      body_template: "{kind} at {ts}\ncamera: {camera_id}\nsnapshot: {snapshot_url}",
    },
  },
  mqtt_action: {
    kind: "mqtt_action",
    paletteCategory: "action",
    label: "MQTT",
    description: "Publishes the event to an MQTT topic.",
    icon: RadioTowerIcon,
    iconClassName: "bg-lime-500/15 text-lime-600",
    defaults: {
      kind: "mqtt_action",
      credential_id: "",
      topic: "looksee/events",
      payload_template: "",
    },
  },
  discord_action: {
    kind: "discord_action",
    paletteCategory: "action",
    label: "Discord",
    description: "Sends the event to a Discord channel via webhook.",
    icon: MessageCircleIcon,
    iconClassName: "bg-violet-500/15 text-violet-600",
    defaults: {
      kind: "discord_action",
      credential_id: "",
      message_template: "[{kind}] camera={camera_id} at {ts}",
    },
  },
  slack_action: {
    kind: "slack_action",
    paletteCategory: "action",
    feature: ENTERPRISE_INTEGRATIONS_FEATURE,
    label: "Slack",
    description: "Sends the event to a Slack channel via incoming webhook.",
    icon: HashIcon,
    iconClassName: "bg-emerald-500/15 text-emerald-600",
    defaults: {
      kind: "slack_action",
      credential_id: "",
      message_template: "[{kind}] camera={camera_id} at {ts}",
    },
  },
} satisfies Record<NodeKind, NodeDefinition>;

export const NODE_DEFINITIONS: NodeDefinition[] = Object.values(NODE_DEFINITIONS_BY_KIND);

export function isNodeKind(value: string): value is NodeKind {
  return value in NODE_DEFINITIONS_BY_KIND;
}

export function getNodeDefinition(kind: NodeKind): NodeDefinition {
  return NODE_DEFINITIONS_BY_KIND[kind];
}
