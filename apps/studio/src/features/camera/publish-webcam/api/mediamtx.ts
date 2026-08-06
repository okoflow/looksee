import { getMediamtxWebRTCUrl } from "@/shared/config";

export function cameraWhipUrl(cameraId: string): string {
  return `${getMediamtxWebRTCUrl()}/${cameraId}/whip`;
}
