"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { assertNever } from "@/shared/lib/assert-never";
import { alertQueryKeys } from "@/entities/alert";
import { workflowQueryKeys } from "@/entities/workflow";
import { cameraSocketUrl, openReconnectingSocket } from "../api/socket";
import { type DetectionFrame, parseSocketMessage } from "./messages";

const DETECTION_TTL_MS = 3000;
const FEED_LIMIT = 30;

export interface LiveFeedItem {
  id: number;
  kind: string;
  snapshotUrl: string | null;
  summary: string;
  ts: string;
  variant: "event" | "alert";
}

export interface LiveFeed {
  clear(): void;
  items: LiveFeedItem[];
}

interface CameraChannel {
  detectionFrame: DetectionFrame | null;
  feed: LiveFeed;
}

export function useCameraChannel(cameraId: string | null): CameraChannel {
  const queryClient = useQueryClient();

  const [detectionFrame, setDetectionFrame] = useState<DetectionFrame | null>(null);
  const [items, setItems] = useState<LiveFeedItem[]>([]);

  const nextIdRef = useRef(0);

  const clear = useCallback(() => {
    setItems([]);
  }, []);

  useEffect(() => {
    let detectionTimer: ReturnType<typeof setTimeout> | null = null;

    setDetectionFrame(null);
    setItems([]);

    if (!cameraId) {
      return;
    }

    const append = (item: Omit<LiveFeedItem, "id">) => {
      nextIdRef.current += 1;

      const entry = { ...item, id: nextIdRef.current };

      setItems((previous) => {
        return [entry, ...previous].slice(0, FEED_LIMIT);
      });
    };

    const socket = openReconnectingSocket(cameraSocketUrl(cameraId), (payload) => {
      const message = parseSocketMessage(payload);

      if (!message) {
        return;
      }

      switch (message.type) {
        case "detections":
          setDetectionFrame({
            detections: message.detections,
            frameWidth: message.frame_width,
            frameHeight: message.frame_height,
          });

          if (detectionTimer) {
            clearTimeout(detectionTimer);
          }

          detectionTimer = setTimeout(() => {
            setDetectionFrame(null);
          }, DETECTION_TTL_MS);
          break;
        case "worker":
          if (message.status === "error" && message.reason) {
            toast.error(`Camera worker error: ${message.reason}`);
          }

          queryClient.invalidateQueries({ queryKey: workflowQueryKeys.root });
          break;
        case "event":
          append({
            variant: "event",
            kind: message.kind,
            ts: message.ts,
            summary: summarizeLabels(message.detections),
            snapshotUrl: null,
          });
          break;
        case "alert":
          append({
            variant: "alert",
            kind: message.kind,
            ts: message.ts,
            summary: message.message,
            snapshotUrl: message.snapshot_url ?? null,
          });
          queryClient.invalidateQueries({ queryKey: alertQueryKeys.root });
          break;
        default:
          return assertNever(message);
      }
    });

    return () => {
      if (detectionTimer) {
        clearTimeout(detectionTimer);
      }

      socket.close();
    };
  }, [cameraId, queryClient]);

  return { detectionFrame, feed: { items, clear } };
}

function summarizeLabels(detections: { label: string }[]): string {
  const counts = new Map<string, number>();

  for (const detection of detections) {
    counts.set(detection.label, (counts.get(detection.label) ?? 0) + 1);
  }

  return [...counts.entries()]
    .map(([label, count]) => {
      return count > 1 ? `${label} ×${count}` : label;
    })
    .join(", ");
}
