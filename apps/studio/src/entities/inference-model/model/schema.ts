import { z } from "zod";

export const EVENT_KIND_MAX_LENGTH = 64;

export const modelIdSchema = z
  .string()
  .min(1)
  .max(64)
  .regex(/^[a-z0-9_-]+$/);

export const eventKindSchema = z
  .string()
  .min(1)
  .max(EVENT_KIND_MAX_LENGTH)
  .regex(/^[A-Z][A-Z0-9_]*$/);

export const inferenceModelClassSchema = z.object({
  label: z.string().min(1).max(128),
  event_kind: eventKindSchema.nullable(),
});

export const inferenceModelSchema = z.object({
  id: modelIdSchema,
  name: z.string().min(1).max(128),
  classes: z.array(inferenceModelClassSchema),
  recommended_confidence_threshold: z.number().min(0).max(1).nullable(),
});

export const inferenceModelsSchema = z.array(inferenceModelSchema);

export type InferenceModel = z.infer<typeof inferenceModelSchema>;
