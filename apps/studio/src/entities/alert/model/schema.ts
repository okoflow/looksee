import { z } from "zod";
import { isoTimestampSchema, uuidSchema } from "@/shared/api";

export const alertSeveritySchema = z.enum(["info", "warning", "critical"]);

export const alertSchema = z.object({
  id: uuidSchema,
  kind: z.string(),
  severity: alertSeveritySchema,
  message: z.string(),
  payload: z.looseObject({ snapshot_url: z.string().optional() }),
  created_at: isoTimestampSchema,
});

export const alertsSchema = z.array(alertSchema);

export const alertScopeParamsSchema = z.object({
  workflow_id: uuidSchema.optional(),
});

export const alertListParamsSchema = alertScopeParamsSchema.extend({
  limit: z.number().int().min(1).max(500).optional(),
});

export type AlertSeverity = z.infer<typeof alertSeveritySchema>;
export type AlertScopeParams = z.infer<typeof alertScopeParamsSchema>;
export type AlertListParams = z.infer<typeof alertListParamsSchema>;
