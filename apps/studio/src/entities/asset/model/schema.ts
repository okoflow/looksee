import { z } from "zod";
import { isoTimestampSchema } from "@/shared/api";

export const assetSchema = z.object({
  key: z.string().min(1),
  size: z.number().int().min(0),
  etag: z.string(),
  last_modified: isoTimestampSchema,
});

export const assetsSchema = z.array(assetSchema);

export type Asset = z.infer<typeof assetSchema>;
