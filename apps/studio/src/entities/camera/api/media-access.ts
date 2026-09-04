import { z } from "zod";
import { api, uuidSchema } from "@/shared/api";

const mediaAccessSchema = z.object({ token: z.string().min(1) });

export async function getCameraMediaAuthorization(
  cameraId: string,
  action: "read" | "publish",
  signal: AbortSignal
): Promise<string> {
  const id = uuidSchema.parse(cameraId);
  const payload: unknown = await api.post(`cameras/${id}/media-access`, { json: { action }, signal }).json();
  const { token } = mediaAccessSchema.parse(payload);

  return `Bearer ${token}`;
}
