import { getMediamtxWebRTCUrl } from "@/shared/config";

export function cameraWhepUrl(cameraId: string): string {
  return `${getMediamtxWebRTCUrl()}/${cameraId}/whep`;
}
