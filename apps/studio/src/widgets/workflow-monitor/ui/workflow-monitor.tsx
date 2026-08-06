"use client";

import { EraserIcon, VideoOffIcon } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from "@/shared/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/shared/ui/tabs";
import { WorkflowAlerts } from "@/entities/alert";
import {
  CAMERA_STATUS_LABELS,
  getCameraShapes,
  ShapeOverlay,
  type Workflow,
  type WorkflowCamera,
} from "@/entities/workflow";
import { CameraStream, LiveEventFeed, useCameraChannel } from "@/features/camera/live-view";
import { usePublishStream, WebcamPublishButton } from "@/features/camera/publish-webcam";

interface WorkflowMonitorProps {
  workflow: Workflow;
}

function activeCamera(cameras: WorkflowCamera[], preferredNodeId: string | null): WorkflowCamera | null {
  if (preferredNodeId !== null) {
    const preferred = cameras.find((camera) => {
      return camera.node_id === preferredNodeId;
    });

    if (preferred !== undefined) {
      return preferred;
    }
  }

  return cameras.at(0) ?? null;
}

export function WorkflowMonitor({ workflow }: WorkflowMonitorProps) {
  const [cameraNodeId, setCameraNodeId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("feed");

  const selectedCamera = activeCamera(workflow.cameras, cameraNodeId);
  const { detectionFrame, feed } = useCameraChannel(selectedCamera?.id ?? null);
  const localStream = usePublishStream(selectedCamera?.id ?? null);

  if (selectedCamera === null) {
    return (
      <div className="flex min-h-0 flex-1 p-editor-gutter">
        <div className="flex flex-1 flex-col items-center justify-center gap-2 rounded-xl border bg-card text-muted-foreground text-sm">
          <VideoOffIcon />
          Add a camera node in the editor to monitor this workflow.
        </div>
      </div>
    );
  }

  const cameraItems = workflow.cameras.map((camera) => {
    return { label: camera.name, value: camera.node_id };
  });

  const handleCameraChange = (nodeId: string | null) => {
    if (nodeId !== null) {
      setCameraNodeId(nodeId);
    }
  };

  const handleTabChange = (tab: string) => {
    setActiveTab(tab);
  };

  const handleClearFeed = () => {
    feed.clear();
  };

  const cameraShapes = getCameraShapes(workflow.graph, selectedCamera.node_id);

  return (
    <div className="flex min-h-0 flex-1 gap-editor-gutter p-editor-gutter">
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-xl border bg-card">
        <div className="flex h-12 shrink-0 items-center gap-2 border-b px-3">
          {workflow.cameras.length > 1 ? (
            <Select items={cameraItems} onValueChange={handleCameraChange} value={selectedCamera.node_id}>
              <SelectTrigger aria-label="Camera" className="w-48" size="sm">
                <SelectValue />
              </SelectTrigger>

              <SelectContent>
                <SelectGroup>
                  {cameraItems.map((camera) => {
                    return (
                      <SelectItem key={camera.value} value={camera.value}>
                        {camera.label}
                      </SelectItem>
                    );
                  })}
                </SelectGroup>
              </SelectContent>
            </Select>
          ) : (
            <span className="font-medium text-sm">{selectedCamera.name}</span>
          )}

          <Badge variant={selectedCamera.status === "active" ? "secondary" : "outline"}>
            {CAMERA_STATUS_LABELS[selectedCamera.status]}
          </Badge>

          {selectedCamera.source_type === "webrtc" ? (
            <div className="ml-auto">
              <WebcamPublishButton cameraId={selectedCamera.id} cameraName={selectedCamera.name} />
            </div>
          ) : null}
        </div>

        <div className="min-h-0 flex-1 bg-black">
          <CameraStream
            cameraId={selectedCamera.id}
            className="aspect-auto h-full rounded-none"
            detectionFrame={detectionFrame}
            key={selectedCamera.id}
            localStream={localStream}
          >
            {cameraShapes.length > 0
              ? cameraShapes.map((cameraShape) => {
                  return (
                    <ShapeOverlay
                      className={cameraShape.kind === "line" ? "stroke-detection" : undefined}
                      key={cameraShape.nodeId}
                      points={cameraShape.points}
                      shape={cameraShape.kind === "line" ? "line" : "polygon"}
                    />
                  );
                })
              : null}
          </CameraStream>
        </div>
      </div>

      <Tabs
        className="flex w-96 shrink-0 flex-col gap-0 overflow-hidden rounded-xl border bg-card"
        onValueChange={handleTabChange}
        value={activeTab}
      >
        <div className="flex h-12 shrink-0 items-center gap-2 border-b px-2">
          <TabsList>
            <TabsTrigger value="feed">Live</TabsTrigger>

            <TabsTrigger value="alerts">Alerts</TabsTrigger>
          </TabsList>

          {activeTab === "feed" ? (
            <Button
              aria-label="Clear the live feed"
              className="ml-auto"
              onClick={handleClearFeed}
              size="sm"
              variant="ghost"
            >
              <EraserIcon data-icon="inline-start" />
              Clear
            </Button>
          ) : null}
        </div>

        <TabsContent className="min-h-0 flex-1" value="feed">
          <LiveEventFeed items={feed.items} />
        </TabsContent>

        <TabsContent className="min-h-0 flex-1" value="alerts">
          <WorkflowAlerts workflowId={workflow.id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
