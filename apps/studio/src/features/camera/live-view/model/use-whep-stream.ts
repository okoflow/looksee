"use client";

import { type RefObject, useEffect, useRef, useState } from "react";
import { getMediamtxMediaAuthorization } from "@/shared/config";
import { runWhepSession, type WhepSessionState } from "@/shared/lib/webrtc";
import { cameraWhepUrl } from "../api/mediamtx";

interface WhepStream {
  restart: () => void;
  state: WhepSessionState;
  videoRef: RefObject<HTMLVideoElement | null>;
}

export function useWhepStream(cameraId: string, isEnabled: boolean): WhepStream {
  const [state, setState] = useState<WhepSessionState>({ status: "connecting" });
  const [sessionToken, setSessionToken] = useState(0);

  const videoRef = useRef<HTMLVideoElement | null>(null);

  // biome-ignore lint/correctness/useExhaustiveDependencies(sessionToken): restart token forces a new WHEP session
  useEffect(() => {
    const video = videoRef.current;

    if (!(video && isEnabled)) {
      return;
    }

    const controller = new AbortController();

    runWhepSession({
      url: cameraWhepUrl(cameraId),
      authorization: getMediamtxMediaAuthorization(),
      video,
      signal: controller.signal,
      onStateChange: setState,
    });

    return () => {
      controller.abort();
    };
  }, [cameraId, isEnabled, sessionToken]);

  const restart = () => {
    setSessionToken((current) => {
      return current + 1;
    });
  };

  return { restart, state, videoRef };
}
