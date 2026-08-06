"use client";

import { Loader2Icon, WebcamIcon } from "lucide-react";
import { useSyncExternalStore } from "react";
import { Button } from "@/shared/ui/button";
import {
  getPublishStatusSnapshot,
  startWebcamPublish,
  stopWebcamPublish,
  subscribeToPublishStatus,
} from "../model/publish-manager";

interface WebcamPublishButtonProps {
  cameraId: string;
  cameraName: string;
}

export function WebcamPublishButton({ cameraId, cameraName }: WebcamPublishButtonProps) {
  const statusByCameraId = useSyncExternalStore(
    subscribeToPublishStatus,
    getPublishStatusSnapshot,
    getPublishStatusSnapshot
  );

  const status = statusByCameraId[cameraId];

  const handleStart = () => {
    startWebcamPublish(cameraId);
  };

  const handleStop = () => {
    stopWebcamPublish(cameraId);
  };

  if (status !== undefined) {
    return (
      <Button aria-label={`Stop publishing webcam to ${cameraName}`} onClick={handleStop} size="sm" variant="secondary">
        {status === "live" ? (
          <WebcamIcon className="text-detection" data-icon="inline-start" />
        ) : (
          <Loader2Icon className="animate-spin" data-icon="inline-start" />
        )}
        Stop publish
      </Button>
    );
  }

  return (
    <Button aria-label={`Publish webcam to ${cameraName}`} onClick={handleStart} size="sm">
      <WebcamIcon data-icon="inline-start" />
      Publish
    </Button>
  );
}
