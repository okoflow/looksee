"use client";

import { XIcon } from "lucide-react";
import { formatClockTime } from "@/shared/lib/format-time";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { ScrollArea } from "@/shared/ui/scroll-area";
import { Skeleton } from "@/shared/ui/skeleton";
import { eventKindLabel } from "@/entities/inference-model/@x/alert";
import { useAlerts, useDeleteAlert } from "../api/queries";
import { resolveSnapshotUrl } from "../lib/snapshot-url";
import { SnapshotPreview } from "./snapshot-preview";

const ALERT_LIMIT = 50;

interface WorkflowAlertsProps {
  workflowId: string;
}

export function WorkflowAlerts({ workflowId }: WorkflowAlertsProps) {
  const alerts = useAlerts({ workflow_id: workflowId, limit: ALERT_LIMIT });
  const deleteAlert = useDeleteAlert();

  if (alerts.isPending) {
    return <Skeleton className="h-full w-full" />;
  }

  if (alerts.data === undefined) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground text-sm">Couldn't load alerts.</div>
    );
  }

  if (alerts.data.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-muted-foreground text-sm">
        No alerts yet. An Alert node records them here when the flow fires.
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <ul className="divide-y">
        {alerts.data.map((alert) => {
          const snapshotUrl = resolveSnapshotUrl(alert.payload.snapshot_url);

          const handleDelete = () => {
            deleteAlert.mutate(alert.id);
          };

          return (
            <li className="flex items-center gap-2 px-3 py-1.5" key={alert.id}>
              <span className="shrink-0 font-mono text-muted-foreground text-xs">
                {formatClockTime(alert.created_at)}
              </span>

              <Badge variant={alert.severity === "critical" ? "destructive" : "outline"}>{alert.severity}</Badge>

              {snapshotUrl ? <SnapshotPreview caption={eventKindLabel(alert.kind)} url={snapshotUrl} /> : null}

              <span className="truncate text-sm">{alert.message}</span>

              <Button
                aria-label="Delete alert"
                className="ml-auto shrink-0"
                onClick={handleDelete}
                size="icon-xs"
                variant="ghost"
              >
                <XIcon />
              </Button>
            </li>
          );
        })}
      </ul>
    </ScrollArea>
  );
}
