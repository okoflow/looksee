import type { CameraStatus, SourceType } from "../model/schema";

export const SOURCE_TYPE_LABELS: Record<SourceType, string> = {
  rtsp: "RTSP",
  rtmp: "RTMP",
  srt: "SRT",
  webrtc: "Webcam",
  whep: "WHEP",
  file: "Video file",
};

export const SOURCE_TYPE_DESCRIPTIONS: Record<SourceType, string> = {
  rtsp: "Pull an IP camera or NVR",
  rtmp: "Pull an RTMP publisher",
  srt: "Pull a low-latency SRT feed",
  webrtc: "Publish from this browser",
  whep: "Pull a remote WebRTC server",
  file: "Loop a video from the asset store",
};

export const CAMERA_STATUS_LABELS: Record<CameraStatus, string> = {
  pending: "Starting",
  active: "Live",
  error: "Error",
  disabled: "Off",
};
