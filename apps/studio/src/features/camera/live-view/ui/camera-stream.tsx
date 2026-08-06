"use client";

import { AlertCircleIcon, Loader2Icon, VideoOffIcon } from "lucide-react";
import { type PropsWithChildren, type RefObject, useEffect, useState } from "react";
import { assertNever } from "@/shared/lib/assert-never";
import { cn } from "@/shared/lib/cn";
import type { WhepSessionState } from "@/shared/lib/webrtc";
import { Button } from "@/shared/ui/button";
import { type ContainBox, fitContainBox } from "../lib/letterbox";
import type { DetectionFrame } from "../model/messages";
import { useWhepStream } from "../model/use-whep-stream";
import { BoundingBoxOverlay } from "./bounding-box-overlay";

interface CameraStreamProps {
  cameraId: string;
  className?: string;
  detectionFrame: DetectionFrame | null;
  localStream: MediaStream | null;
}

export function CameraStream({
  cameraId,
  children,
  className,
  detectionFrame,
  localStream,
}: PropsWithChildren<CameraStreamProps>) {
  const { videoRef, state, restart } = useWhepStream(cameraId, localStream === null);

  const contentBox = useVideoContentBox(videoRef);

  const isPlaying = localStream !== null || state.status === "playing";

  useEffect(() => {
    const video = videoRef.current;

    if (!(video && localStream)) {
      return;
    }

    video.srcObject = localStream;

    return () => {
      video.srcObject = null;
    };
  }, [localStream, videoRef]);

  return (
    <div className={cn("relative aspect-[16/9] w-full overflow-hidden rounded-md bg-black", className)}>
      <video autoPlay className="h-full w-full object-contain" muted playsInline ref={videoRef} />

      {isPlaying && detectionFrame ? <BoundingBoxOverlay frame={detectionFrame} videoRef={videoRef} /> : null}

      {isPlaying ? null : <SessionStateOverlay onRestart={restart} state={state} />}

      {children === null || children === undefined || contentBox === null ? null : (
        <div className="absolute" style={contentBox}>
          {children}
        </div>
      )}
    </div>
  );
}

function useVideoContentBox(videoRef: RefObject<HTMLVideoElement | null>): ContainBox | null {
  const [box, setBox] = useState<ContainBox | null>(null);

  useEffect(() => {
    const video = videoRef.current;

    if (!video) {
      return;
    }

    const update = () => {
      const rect = video.getBoundingClientRect();

      if (!(rect.width && rect.height)) {
        setBox(null);

        return;
      }

      const { videoWidth, videoHeight } = video;

      if (!(videoWidth && videoHeight)) {
        setBox({ left: 0, top: 0, width: rect.width, height: rect.height });

        return;
      }

      setBox(fitContainBox({ width: rect.width, height: rect.height }, { width: videoWidth, height: videoHeight }));
    };

    update();

    const resizeObserver = new ResizeObserver(update);

    resizeObserver.observe(video);

    video.addEventListener("resize", update);
    video.addEventListener("emptied", update);

    return () => {
      resizeObserver.disconnect();

      video.removeEventListener("resize", update);
      video.removeEventListener("emptied", update);
    };
  }, [videoRef]);

  return box;
}

interface SessionStateOverlayProps {
  onRestart: () => void;
  state: WhepSessionState;
}

function SessionStateOverlay({ onRestart, state }: SessionStateOverlayProps) {
  switch (state.status) {
    case "playing":
      return null;

    case "connecting":
      return (
        <OverlayBackdrop>
          <Loader2Icon className="animate-spin" />

          <span>Connecting…</span>
        </OverlayBackdrop>
      );

    case "waiting":
      return (
        <OverlayBackdrop>
          <VideoOffIcon />

          <span>Waiting for the camera stream…</span>
        </OverlayBackdrop>
      );

    case "error":
      return (
        <OverlayBackdrop>
          <AlertCircleIcon />

          <span>{state.error}</span>

          <Button onClick={onRestart} size="sm" variant="secondary">
            Retry
          </Button>
        </OverlayBackdrop>
      );

    default:
      return assertNever(state);
  }
}

function OverlayBackdrop({ children }: PropsWithChildren) {
  return (
    <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-black/60 text-sm text-white">
      {children}
    </div>
  );
}
