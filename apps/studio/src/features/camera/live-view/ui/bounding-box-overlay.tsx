"use client";

import type { RefObject } from "react";
import { useEffect, useState } from "react";
import { containScale, fitContainBox } from "../lib/letterbox";
import type { DetectionFrame } from "../model/messages";

interface BoundingBoxOverlayProps {
  frame: DetectionFrame;
  videoRef: RefObject<HTMLVideoElement | null>;
}

interface DisplaySize {
  height: number;
  width: number;
}

export function BoundingBoxOverlay({ videoRef, frame }: BoundingBoxOverlayProps) {
  const displaySize = useDisplaySize(videoRef);

  if (!displaySize || frame.detections.length === 0) {
    return null;
  }

  const frameSize = { width: frame.frameWidth, height: frame.frameHeight };
  const scale = containScale(displaySize, frameSize);
  const { left: offsetX, top: offsetY } = fitContainBox(displaySize, frameSize);

  return (
    <div className="pointer-events-none absolute inset-0">
      {frame.detections.map((detection, index) => {
        const [x1, y1, x2, y2] = detection.bounding_box;

        const left = offsetX + x1 * scale;
        const top = offsetY + y1 * scale;
        const width = (x2 - x1) * scale;
        const height = (y2 - y1) * scale;

        const label = `${detection.label} ${(detection.confidence * 100).toFixed(0)}%`;

        const key = detection.tracker_id === null ? `${detection.label}-${index}` : `track-${detection.tracker_id}`;

        return (
          <div className="border-detection absolute border-2" key={key} style={{ left, top, width, height }}>
            <span className="bg-detection absolute -top-5 left-0 rounded-t-sm px-1 text-xs whitespace-nowrap text-white">
              {label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function useDisplaySize(videoRef: RefObject<HTMLVideoElement | null>): DisplaySize | null {
  const [size, setSize] = useState<DisplaySize | null>(null);

  useEffect(() => {
    const video = videoRef.current;

    if (!video) {
      return;
    }

    const update = () => {
      const rect = video.getBoundingClientRect();

      if (!(rect.width && rect.height)) {
        return;
      }

      setSize({ width: rect.width, height: rect.height });
    };

    update();

    const resizeObserver = new ResizeObserver(update);

    resizeObserver.observe(video);

    return () => {
      resizeObserver.disconnect();
    };
  }, [videoRef]);

  return size;
}
