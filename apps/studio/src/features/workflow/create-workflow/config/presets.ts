import {
  CarIcon,
  FlameIcon,
  HardHatIcon,
  ListOrderedIcon,
  ShieldAlertIcon,
  SquareParkingIcon,
  TimerIcon,
  UsersIcon,
} from "lucide-react";
import type { ComponentType, SVGProps } from "react";
import type {
  NodeData,
  WorkflowEdgeBranch,
  WorkflowEdgeModel,
  WorkflowGraph,
  WorkflowNodeModel,
} from "@/entities/workflow";

export interface PresetField {
  defaultValue: number;
  description?: string;
  key: string;
  label: string;
  max?: number;
  min?: number;
}

export type PresetParams = Record<string, string | number>;

export type PresetParamLookup = (key: string) => number;

export interface WorkflowPreset {
  buildGraph: (param: PresetParamLookup) => WorkflowGraph;
  defaultName: string;
  description: string;
  fields: PresetField[];
  hint?: string;
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  id: string;
  title: string;
  vertical: string;
}

// Node cards grow with their summary text (filter cards reach ~280px with the
// If/Else gutter), so the column step keeps a clear gap between neighbours.
const STEP_X = 340;
const BRANCH_Y = 150;

function node(id: string, column: number, y: number, data: NodeData): WorkflowNodeModel {
  return { id, position: { x: column * STEP_X, y }, data };
}

function edge(source: string, target: string, branch?: WorkflowEdgeBranch): WorkflowEdgeModel {
  return { id: `${source}-${target}`, source, target, ...(branch ? { branch } : {}) };
}

function chain(first: string, ...rest: string[]): WorkflowEdgeModel[] {
  const edges: WorkflowEdgeModel[] = [];

  let source = first;

  for (const target of rest) {
    edges.push(edge(source, target));

    source = target;
  }

  return edges;
}

function camera(name: string): NodeData {
  return {
    kind: "camera_source",
    name,
    source_type: "rtsp",
    url: "",
  };
}

function telegram(): NodeData {
  return {
    kind: "telegram_action",
    credential_id: "",
    chat_id: "",
    message_template: "[{kind}] camera={camera_id} at {ts}\n{snapshot_url}",
  };
}

export const WORKFLOW_PRESETS: WorkflowPreset[] = [
  {
    id: "after_hours_intrusion",
    title: "After-hours intrusion",
    vertical: "Security",
    description: "Person or vehicle on site outside working hours — Telegram alert with a snapshot.",
    icon: ShieldAlertIcon,
    defaultName: "After-hours intrusion",
    hint: "Pick a model on the Detect node and select its person/vehicle events, configure Camera and Telegram, then draw the protected zone in the editor.",
    fields: [
      {
        key: "work_start",
        label: "Workday starts (hour)",
        defaultValue: 8,
        min: 0,
        max: 23,
      },
      {
        key: "work_end",
        label: "Workday ends (hour)",
        defaultValue: 20,
        min: 0,
        max: 23,
      },
    ],
    buildGraph: (param) => {
      return {
        nodes: [
          node("camera", 0, 0, camera("Site camera")),
          node("detect", 1, 0, {
            kind: "detect",
            model_id: null,
            event_kinds: [],
            confidence_threshold: 0.5,
            inference_fps: 1,
          }),
          node("zone", 2, 0, { kind: "zone_filter", polygon: [] }),
          node("schedule", 3, 0, {
            kind: "time_window_filter",
            start_hour: param("work_start"),
            end_hour: param("work_end"),
            weekdays: [0, 1, 2, 3, 4],
            invert: true,
          }),
          node("debounce", 4, 0, { kind: "debounce_filter", seconds: 60 }),
          node("snapshot", 5, 0, { kind: "snapshot_action", annotate: true }),
          node("telegram", 6, -BRANCH_Y / 2, telegram()),
          node("alert", 6, BRANCH_Y / 2, { kind: "log_alert_action", severity: "critical", cooldown_seconds: 30 }),
        ],
        edges: [
          ...chain("camera", "detect", "zone", "schedule", "debounce", "snapshot"),
          edge("snapshot", "telegram"),
          edge("snapshot", "alert"),
        ],
      };
    },
  },
  {
    id: "people_counting",
    title: "People counting",
    vertical: "Retail",
    description: "Count visitors crossing an entrance line; every crossing is logged as an event.",
    icon: UsersIcon,
    defaultName: "People counting",
    hint: "Pick a model on the Detect node and select its person event, configure the Camera node, then draw the entrance line in the editor.",
    fields: [],
    buildGraph: () => {
      return {
        nodes: [
          node("camera", 0, 0, camera("Entrance camera")),
          node("detect", 1, 0, {
            kind: "detect",
            model_id: null,
            event_kinds: [],
            confidence_threshold: 0.5,
            inference_fps: 5,
          }),
          node("line", 2, 0, { kind: "line_crossing_filter", line: [], direction: "any" }),
          node("debounce", 3, 0, { kind: "debounce_filter", seconds: 2 }),
          node("alert", 4, 0, { kind: "log_alert_action", severity: "info", cooldown_seconds: 30 }),
        ],
        edges: chain("camera", "detect", "line", "debounce", "alert"),
      };
    },
  },
  {
    id: "loitering",
    title: "Loitering",
    vertical: "Security",
    description: "Someone lingers near the entrance, ATM or lobby too long — alert with a snapshot.",
    icon: TimerIcon,
    defaultName: "Loitering watch",
    hint: "Pick a model on the Detect node and select its person event, configure Camera and Telegram, then draw the watch zone in the editor.",
    fields: [
      {
        key: "min_seconds",
        label: "Alert after (seconds)",
        defaultValue: 180,
        min: 1,
        max: 3600,
      },
    ],
    buildGraph: (param) => {
      return {
        nodes: [
          node("camera", 0, 0, camera("Entrance camera")),
          node("detect", 1, 0, {
            kind: "detect",
            model_id: null,
            event_kinds: [],
            confidence_threshold: 0.5,
            inference_fps: 1,
          }),
          node("dwell", 2, 0, {
            kind: "dwell_filter",
            polygon: [],
            min_seconds: param("min_seconds"),
          }),
          node("debounce", 3, 0, { kind: "debounce_filter", seconds: 60 }),
          node("snapshot", 4, 0, { kind: "snapshot_action", annotate: true }),
          node("telegram", 5, -BRANCH_Y / 2, telegram()),
          node("alert", 5, BRANCH_Y / 2, { kind: "log_alert_action", severity: "warning", cooldown_seconds: 30 }),
        ],
        edges: [
          ...chain("camera", "detect", "dwell", "debounce", "snapshot"),
          edge("snapshot", "telegram"),
          edge("snapshot", "alert"),
        ],
      };
    },
  },
  {
    id: "parking",
    title: "Parking occupancy",
    vertical: "Parking",
    description: "Track free spaces in a lot and flag cars parked past the limit, with photo evidence.",
    icon: CarIcon,
    defaultName: "Parking lot",
    hint: "Pick a model on the Detect node and select its vehicle events, configure the Camera node, then draw the lot polygons in the editor.",
    fields: [
      {
        key: "free_when_lte",
        label: "“Spaces free” when cars ≤",
        defaultValue: 8,
        min: 0,
        max: 1000,
        description: "Lot capacity minus one: fewer cars than this means free spaces.",
      },
      {
        key: "overtime_minutes",
        label: "Overtime after (minutes)",
        defaultValue: 30,
        min: 1,
        max: 60,
      },
    ],
    buildGraph: (param) => {
      return {
        nodes: [
          node("camera", 0, 0, camera("Parking camera")),
          node("detect", 1, 0, {
            kind: "detect",
            model_id: null,
            event_kinds: [],
            confidence_threshold: 0.5,
            inference_fps: 1,
          }),
          node("count", 2, -BRANCH_Y, {
            kind: "count_threshold_filter",
            polygon: [],
            operator: "lte",
            count: param("free_when_lte"),
          }),
          node("count-debounce", 3, -BRANCH_Y, { kind: "debounce_filter", seconds: 300 }),
          node("free-alert", 4, -BRANCH_Y, { kind: "log_alert_action", severity: "info", cooldown_seconds: 30 }),
          node("dwell", 2, BRANCH_Y, {
            kind: "dwell_filter",
            polygon: [],
            min_seconds: param("overtime_minutes") * 60,
          }),
          node("dwell-debounce", 3, BRANCH_Y, { kind: "debounce_filter", seconds: 600 }),
          node("snapshot", 4, BRANCH_Y, { kind: "snapshot_action", annotate: true }),
          node("overtime-alert", 5, BRANCH_Y, { kind: "log_alert_action", severity: "warning", cooldown_seconds: 30 }),
        ],
        edges: [
          edge("camera", "detect"),
          ...chain("detect", "count", "count-debounce", "free-alert"),
          ...chain("detect", "dwell", "dwell-debounce", "snapshot", "overtime-alert"),
        ],
      };
    },
  },
  {
    id: "queue",
    title: "Queue monitor",
    vertical: "Retail",
    description: "Queue grows past N people — notify the manager to open another till.",
    icon: ListOrderedIcon,
    defaultName: "Queue monitor",
    hint: "Pick a model on the Detect node and select its person event, configure Camera and Telegram, then draw the queue area in the editor.",
    fields: [
      {
        key: "max_queue",
        label: "Alert when queue ≥",
        defaultValue: 5,
        min: 1,
        max: 1000,
      },
    ],
    buildGraph: (param) => {
      return {
        nodes: [
          node("camera", 0, 0, camera("Checkout camera")),
          node("detect", 1, 0, {
            kind: "detect",
            model_id: null,
            event_kinds: [],
            confidence_threshold: 0.5,
            inference_fps: 1,
          }),
          node("count", 2, 0, {
            kind: "count_threshold_filter",
            polygon: [],
            operator: "gte",
            count: param("max_queue"),
          }),
          node("debounce", 3, 0, { kind: "debounce_filter", seconds: 120 }),
          node("telegram", 4, -BRANCH_Y / 2, telegram()),
          node("alert", 4, BRANCH_Y / 2, { kind: "log_alert_action", severity: "warning", cooldown_seconds: 30 }),
        ],
        edges: [
          ...chain("camera", "detect", "count", "debounce"),
          edge("debounce", "telegram"),
          edge("debounce", "alert"),
        ],
      };
    },
  },
  {
    id: "ppe_helmet",
    title: "Helmet compliance",
    vertical: "Safety",
    description: "Worker without a helmet in the work zone during shift hours — alert with photo evidence.",
    icon: HardHatIcon,
    defaultName: "Helmet compliance",
    hint: "Pick a PPE model (bare-head class) on the Detect node, configure Camera and Telegram, then draw the work zone in the editor.",
    fields: [
      {
        key: "shift_start",
        label: "Shift starts (hour)",
        defaultValue: 8,
        min: 0,
        max: 23,
      },
      {
        key: "shift_end",
        label: "Shift ends (hour)",
        defaultValue: 18,
        min: 0,
        max: 23,
      },
    ],
    buildGraph: (param) => {
      return {
        nodes: [
          node("camera", 0, 0, camera("Work zone camera")),
          node("detect", 1, 0, {
            kind: "detect",
            model_id: null,
            event_kinds: ["HEAD_DETECTED"],
            confidence_threshold: 0.4,
            inference_fps: 1,
          }),
          node("zone", 2, 0, { kind: "zone_filter", polygon: [] }),
          node("schedule", 3, 0, {
            kind: "time_window_filter",
            start_hour: param("shift_start"),
            end_hour: param("shift_end"),
            weekdays: [0, 1, 2, 3, 4],
            invert: false,
          }),
          node("debounce", 4, 0, { kind: "debounce_filter", seconds: 120 }),
          node("snapshot", 5, 0, { kind: "snapshot_action", annotate: true }),
          node("telegram", 6, -BRANCH_Y / 2, telegram()),
          node("alert", 6, BRANCH_Y / 2, { kind: "log_alert_action", severity: "warning", cooldown_seconds: 30 }),
        ],
        edges: [
          ...chain("camera", "detect", "zone", "schedule", "debounce", "snapshot"),
          edge("snapshot", "telegram"),
          edge("snapshot", "alert"),
        ],
      };
    },
  },
  {
    id: "fire_smoke",
    title: "Fire & smoke",
    vertical: "Safety",
    description: "Smoke or flame in frame, around the clock — critical alert with a snapshot.",
    icon: FlameIcon,
    defaultName: "Fire & smoke watch",
    hint: "Pick a fire & smoke model on the Detect node, then configure Camera and Telegram nodes.",
    fields: [
      {
        key: "cooldown_seconds",
        label: "Alert cooldown (seconds)",
        defaultValue: 60,
        min: 1,
        max: 3600,
      },
    ],
    buildGraph: (param) => {
      return {
        nodes: [
          node("camera", 0, 0, camera("Site camera")),
          node("detect", 1, 0, {
            kind: "detect",
            model_id: null,
            event_kinds: ["FIRE_DETECTED", "SMOKE_DETECTED"],
            confidence_threshold: 0.3,
            inference_fps: 2,
          }),
          node("debounce", 2, 0, {
            kind: "debounce_filter",
            seconds: param("cooldown_seconds"),
          }),
          node("snapshot", 3, 0, { kind: "snapshot_action", annotate: true }),
          node("telegram", 4, -BRANCH_Y / 2, telegram()),
          node("alert", 4, BRANCH_Y / 2, { kind: "log_alert_action", severity: "critical", cooldown_seconds: 30 }),
        ],
        edges: [
          ...chain("camera", "detect", "debounce", "snapshot"),
          edge("snapshot", "telegram"),
          edge("snapshot", "alert"),
        ],
      };
    },
  },
  {
    id: "parking_spaces",
    title: "Free parking spaces",
    vertical: "Parking",
    description: "Per-space occupancy model — announce free spaces and notify when the lot fills up.",
    icon: SquareParkingIcon,
    defaultName: "Parking spaces",
    hint: "Pick a parking-space model (empty/occupied classes) on the Detect node, then configure Camera and Telegram nodes.",
    fields: [
      {
        key: "min_free",
        label: "Announce when free spaces ≥",
        defaultValue: 1,
        min: 1,
        max: 1000,
      },
      {
        key: "full_when",
        label: "Lot full when occupied ≥",
        defaultValue: 20,
        min: 1,
        max: 1000,
        description: "Set to the lot capacity to get a “lot is full” notification.",
      },
    ],
    buildGraph: (param) => {
      return {
        nodes: [
          node("camera", 0, 0, camera("Parking camera")),
          node("detect", 1, 0, {
            kind: "detect",
            model_id: null,
            event_kinds: ["SPACE_EMPTY_DETECTED", "SPACE_OCCUPIED_DETECTED"],
            confidence_threshold: 0.5,
            inference_fps: 1,
          }),
          node("branch", 2, 0, {
            kind: "if_else_filter",
            condition: { field: "event_kind", operator: "is", value: "SPACE_EMPTY_DETECTED" },
          }),
          node("free-count", 3, -BRANCH_Y, {
            kind: "count_threshold_filter",
            polygon: [],
            operator: "gte",
            count: param("min_free"),
          }),
          node("free-debounce", 4, -BRANCH_Y, { kind: "debounce_filter", seconds: 300 }),
          node("free-alert", 5, -BRANCH_Y, { kind: "log_alert_action", severity: "info", cooldown_seconds: 30 }),
          node("full-count", 3, BRANCH_Y, {
            kind: "count_threshold_filter",
            polygon: [],
            operator: "gte",
            count: param("full_when"),
          }),
          node("full-debounce", 4, BRANCH_Y, { kind: "debounce_filter", seconds: 300 }),
          node("telegram", 5, BRANCH_Y / 2, telegram()),
          node("full-alert", 5, (BRANCH_Y * 3) / 2, {
            kind: "log_alert_action",
            severity: "warning",
            cooldown_seconds: 30,
          }),
        ],
        edges: [
          ...chain("camera", "detect", "branch"),
          edge("branch", "free-count", "if"),
          ...chain("free-count", "free-debounce", "free-alert"),
          edge("branch", "full-count", "else"),
          ...chain("full-count", "full-debounce"),
          edge("full-debounce", "telegram"),
          edge("full-debounce", "full-alert"),
        ],
      };
    },
  },
];

export function presetDefaults(preset: WorkflowPreset): PresetParams {
  return Object.fromEntries(
    preset.fields.map((field) => {
      return [field.key, field.defaultValue];
    })
  );
}
