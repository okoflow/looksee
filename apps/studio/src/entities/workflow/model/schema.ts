import { z } from "zod";
import { isoTimestampSchema, uuidSchema } from "@/shared/api";
import { normalizedPolygonSchema } from "@/shared/lib/geometry";
import { alertSeveritySchema } from "@/entities/alert/@x/workflow";
import { eventKindSchema, modelIdSchema } from "@/entities/inference-model/@x/workflow";
import {
  ALERT_COOLDOWN_LIMITS,
  AREA_FRACTION_LIMITS,
  CONFIDENCE_THRESHOLD_LIMITS,
  DAY_HOUR_LIMITS,
  DETECTION_COUNT_LIMITS,
  DURATION_SECONDS_LIMITS,
  INFERENCE_FPS_LIMITS,
  type NumericLimits,
  TEXT_LIMITS,
  WEEKDAY_LIMITS,
} from "./limits";

const MAX_EVENT_KINDS = 64;
const MAX_CLASSES = 64;
const MAX_POLYGON_POINTS = 100;

function boundedNumber(limits: NumericLimits) {
  return z.number().min(limits.min).max(limits.max);
}

function boundedInteger(limits: NumericLimits) {
  return z.number().int().min(limits.min).max(limits.max);
}

export const sourceTypeSchema = z.enum(["rtsp", "rtmp", "srt", "webrtc", "whep", "file"]);

export const cameraStatusSchema = z.enum(["pending", "active", "error", "disabled"]);

const numericConditionOperatorSchema = z.enum(["eq", "neq", "gt", "gte", "lt", "lte"]);
const nodeIdSchema = z.string().min(1).max(128);
const edgeIdSchema = z.string().min(1).max(256);

export const ifElseConditionSchema = z.discriminatedUnion("field", [
  z.object({
    field: z.literal("event_kind"),
    operator: z.enum(["is", "is_not"]),
    value: eventKindSchema.nullable(),
  }),
  z.object({
    field: z.literal("object_class"),
    operator: z.enum(["contains", "not_contains"]),
    value: z.string().max(TEXT_LIMITS.objectClass),
  }),
  z.object({
    field: z.literal("detection_count"),
    operator: numericConditionOperatorSchema,
    value: boundedInteger(DETECTION_COUNT_LIMITS),
  }),
  z.object({
    field: z.literal("max_confidence"),
    operator: numericConditionOperatorSchema,
    value: boundedNumber(CONFIDENCE_THRESHOLD_LIMITS),
  }),
]);

export const nodeDataSchema = z.discriminatedUnion("kind", [
  z.object({
    kind: z.literal("camera_source"),
    name: z.string().min(1).max(TEXT_LIMITS.cameraName),
    source_type: sourceTypeSchema,
    url: z.string().max(TEXT_LIMITS.sourceUrl),
  }),
  z.object({
    kind: z.literal("detect"),
    model_id: modelIdSchema.nullable(),
    event_kinds: z.array(eventKindSchema).max(MAX_EVENT_KINDS),
    confidence_threshold: boundedNumber(CONFIDENCE_THRESHOLD_LIMITS),
    inference_fps: boundedInteger(INFERENCE_FPS_LIMITS),
  }),
  z.object({
    kind: z.literal("if_else_filter"),
    condition: ifElseConditionSchema,
  }),
  z.object({
    kind: z.literal("zone_filter"),
    polygon: normalizedPolygonSchema.max(MAX_POLYGON_POINTS),
  }),
  z.object({
    kind: z.literal("class_filter"),
    classes: z.array(z.string().min(1).max(TEXT_LIMITS.classLabel)).max(MAX_CLASSES),
  }),
  z.object({
    kind: z.literal("debounce_filter"),
    seconds: boundedInteger(DURATION_SECONDS_LIMITS),
  }),
  z.object({
    kind: z.literal("time_window_filter"),
    start_hour: boundedInteger(DAY_HOUR_LIMITS),
    end_hour: boundedInteger(DAY_HOUR_LIMITS),
    weekdays: z.array(boundedInteger(WEEKDAY_LIMITS)).max(7),
    invert: z.boolean().default(false),
  }),
  z.object({
    kind: z.literal("line_crossing_filter"),
    line: normalizedPolygonSchema.max(2),
    direction: z.enum(["any", "in", "out"]),
  }),
  z.object({
    kind: z.literal("dwell_filter"),
    polygon: normalizedPolygonSchema.max(MAX_POLYGON_POINTS),
    min_seconds: boundedInteger(DURATION_SECONDS_LIMITS),
  }),
  z.object({
    kind: z.literal("count_threshold_filter"),
    polygon: normalizedPolygonSchema.max(MAX_POLYGON_POINTS),
    operator: z.enum(["gte", "lte"]),
    count: boundedInteger(DETECTION_COUNT_LIMITS),
  }),
  z
    .object({
      kind: z.literal("size_filter"),
      min_area: boundedNumber(AREA_FRACTION_LIMITS),
      max_area: boundedNumber(AREA_FRACTION_LIMITS),
    })
    .refine(({ min_area, max_area }) => min_area <= max_area, {
      message: "Maximum area must be greater than or equal to minimum area",
      path: ["max_area"],
    }),
  z.object({
    kind: z.literal("telegram_action"),
    credential_id: z.string().max(TEXT_LIMITS.credentialId),
    chat_id: z.string().max(TEXT_LIMITS.telegramChatId),
    message_template: z.string().max(TEXT_LIMITS.telegramMessage),
  }),
  z.object({
    kind: z.literal("webhook_action"),
    url: z.string().max(TEXT_LIMITS.sourceUrl),
    method: z.enum(["POST", "GET", "PUT"]),
  }),
  z.object({
    kind: z.literal("log_alert_action"),
    severity: alertSeveritySchema,
    cooldown_seconds: boundedInteger(ALERT_COOLDOWN_LIMITS).default(30),
  }),
  z.object({
    kind: z.literal("snapshot_action"),
    annotate: z.boolean(),
  }),
  z.object({
    kind: z.literal("email_action"),
    credential_id: z.string().max(TEXT_LIMITS.credentialId),
    to: z.string().max(TEXT_LIMITS.emailTo),
    subject_template: z.string().max(TEXT_LIMITS.emailSubject),
    body_template: z.string().max(TEXT_LIMITS.emailBody),
  }),
  z.object({
    kind: z.literal("mqtt_action"),
    credential_id: z.string().max(TEXT_LIMITS.credentialId),
    topic: z.string().max(TEXT_LIMITS.mqttTopic),
    payload_template: z.string().max(TEXT_LIMITS.mqttPayload),
  }),
  z.object({
    kind: z.literal("discord_action"),
    credential_id: z.string().max(TEXT_LIMITS.credentialId),
    message_template: z.string().max(TEXT_LIMITS.discordMessage),
  }),
  z.object({
    kind: z.literal("slack_action"),
    credential_id: z.string().max(TEXT_LIMITS.credentialId),
    message_template: z.string().max(TEXT_LIMITS.slackMessage),
  }),
]);

export const nodePositionSchema = z.object({ x: z.number().finite(), y: z.number().finite() });

export const workflowNodeSchema = z.object({
  id: nodeIdSchema,
  position: nodePositionSchema,
  data: nodeDataSchema,
});

export const workflowEdgeBranchSchema = z.enum(["if", "else"]);

export const workflowEdgeSchema = z.object({
  id: edgeIdSchema,
  source: nodeIdSchema,
  target: nodeIdSchema,
  branch: workflowEdgeBranchSchema.nullable().optional(),
});

export const canvasCommentSchema = z.object({
  id: nodeIdSchema,
  position: nodePositionSchema,
  text: z.string().max(TEXT_LIMITS.commentText),
});

export const workflowGraphSchema = z.object({
  nodes: z.array(workflowNodeSchema).max(200),
  edges: z.array(workflowEdgeSchema).max(400),
  comments: z.array(canvasCommentSchema).max(100).optional(),
});

export const workflowCameraSchema = z.object({
  id: uuidSchema,
  node_id: nodeIdSchema,
  name: z.string().min(1).max(TEXT_LIMITS.cameraName),
  source_type: sourceTypeSchema,
  status: cameraStatusSchema,
});

export const workflowSchema = z.object({
  id: uuidSchema,
  name: z.string().min(1).max(TEXT_LIMITS.workflowName),
  description: z.string().nullable(),
  enabled: z.boolean(),
  graph: workflowGraphSchema,
  cameras: z.array(workflowCameraSchema),
  created_at: isoTimestampSchema,
  updated_at: isoTimestampSchema,
});

export const workflowsSchema = z.array(workflowSchema);

export const workflowCreateSchema = z.object({
  name: z.string().min(1).max(TEXT_LIMITS.workflowName),
  description: z.string().max(TEXT_LIMITS.workflowDescription).nullable(),
  graph: workflowGraphSchema,
});

export const workflowSetupSchema = workflowCreateSchema.pick({ name: true, description: true });

export const workflowUpdateSchema = workflowCreateSchema.extend({ enabled: z.boolean() }).partial();

export type SourceType = z.infer<typeof sourceTypeSchema>;
export type CameraStatus = z.infer<typeof cameraStatusSchema>;
export type CanvasComment = z.infer<typeof canvasCommentSchema>;
export type IfElseCondition = z.infer<typeof ifElseConditionSchema>;
export type NodeData = z.infer<typeof nodeDataSchema>;
export type NodeKind = NodeData["kind"];
export type WorkflowNodeModel = z.infer<typeof workflowNodeSchema>;
export type WorkflowEdgeBranch = z.infer<typeof workflowEdgeBranchSchema>;
export type WorkflowEdgeModel = z.infer<typeof workflowEdgeSchema>;
export type WorkflowGraph = z.infer<typeof workflowGraphSchema>;
export type WorkflowCamera = z.infer<typeof workflowCameraSchema>;
export type Workflow = z.infer<typeof workflowSchema>;
export type WorkflowCreate = z.infer<typeof workflowCreateSchema>;
export type WorkflowSetup = z.infer<typeof workflowSetupSchema>;
export type WorkflowUpdate = z.infer<typeof workflowUpdateSchema>;
