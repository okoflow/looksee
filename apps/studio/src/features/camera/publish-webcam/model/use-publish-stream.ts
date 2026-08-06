"use client";

import { useSyncExternalStore } from "react";
import { getPublishStreamSnapshot, subscribeToPublishStatus } from "./publish-manager";

const EMPTY: Record<string, MediaStream> = {};

function getServerSnapshot() {
  return EMPTY;
}

export function usePublishStream(cameraId: string | null): MediaStream | null {
  const streams = useSyncExternalStore(subscribeToPublishStatus, getPublishStreamSnapshot, getServerSnapshot);

  if (cameraId === null) {
    return null;
  }

  return streams[cameraId] ?? null;
}
