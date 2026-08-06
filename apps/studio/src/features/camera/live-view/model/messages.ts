import { z } from "zod";
import { isoTimestampSchema, uuidSchema } from "@/shared/api";
import { alertSeveritySchema } from "@/entities/alert";
import { eventKindSchema } from "@/entities/inference-model";
import { cameraStatusSchema } from "@/entities/workflow";

const boundingBoxSchema = z
  .tuple([z.number(), z.number(), z.number(), z.number()])
  .refine(([xMin, yMin, xMax, yMax]) => xMin <= xMax && yMin <= yMax, {
    message: "Bounding box minimums must not exceed maximums",
  });

const detectionSchema = z.object({
  label: z.string().min(1).max(128),
  bounding_box: boundingBoxSchema,
  confidence: z.number().min(0).max(1),
  class_id: z.number().int().min(0),
  tracker_id: z.number().int().min(0).nullable(),
});

const frameMessageFields = {
  ts: isoTimestampSchema,
  frame_width: z.number().int().min(1),
  frame_height: z.number().int().min(1),
  detections: z.array(detectionSchema),
};

const detectionsMessageSchema = z.object({
  type: z.literal("detections"),
  ...frameMessageFields,
});

const eventMessageSchema = z.object({
  type: z.literal("event"),
  kind: eventKindSchema,
  ...frameMessageFields,
});

const workerMessageSchema = z.object({
  type: z.literal("worker"),
  status: cameraStatusSchema,
  ts: isoTimestampSchema,
  reason: z.string().nullable().optional(),
});

const alertMessageSchema = z.object({
  type: z.literal("alert"),
  id: uuidSchema,
  kind: eventKindSchema,
  severity: alertSeveritySchema,
  message: z.string(),
  ts: isoTimestampSchema,
  snapshot_url: z.string().nullable().optional(),
});

const socketMessageSchema = z.discriminatedUnion("type", [
  detectionsMessageSchema,
  eventMessageSchema,
  workerMessageSchema,
  alertMessageSchema,
]);

type SocketMessage = z.infer<typeof socketMessageSchema>;
type Detection = z.infer<typeof detectionSchema>;

export interface DetectionFrame {
  detections: Detection[];
  frameHeight: number;
  frameWidth: number;
}

export function parseSocketMessage(payload: string): SocketMessage | null {
  let parsed: unknown;

  try {
    parsed = JSON.parse(payload);
  } catch {
    console.warn("camera socket sent malformed JSON", payload.slice(0, 200));

    return null;
  }

  const result = socketMessageSchema.safeParse(parsed);

  if (!result.success) {
    console.warn("camera socket sent an unrecognized message", result.error.message);

    return null;
  }

  return result.data;
}
