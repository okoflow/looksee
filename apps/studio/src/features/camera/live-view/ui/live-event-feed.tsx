"use client";

import { formatClockTime } from "@/shared/lib/format-time";
import { Badge } from "@/shared/ui/badge";
import { ScrollArea } from "@/shared/ui/scroll-area";
import { resolveSnapshotUrl, SnapshotPreview } from "@/entities/alert";
import { eventKindLabel } from "@/entities/inference-model";
import type { LiveFeedItem } from "../model/use-camera-channel";

interface LiveEventFeedProps {
  items: LiveFeedItem[];
}

export function LiveEventFeed({ items }: LiveEventFeedProps) {
  if (items.length === 0) {
    return (
      <div className="flex h-full min-w-0 flex-1 items-center justify-center p-6 text-center text-muted-foreground text-sm">
        Events and alerts show up here while the camera runs.
      </div>
    );
  }

  return (
    <ScrollArea className="h-full min-w-0 flex-1">
      <ul className="divide-y">
        {items.map((item) => {
          const snapshotUrl = resolveSnapshotUrl(item.snapshotUrl);

          return (
            <li className="flex items-center gap-2 px-3 py-1.5" key={item.id}>
              <span className="shrink-0 font-mono text-muted-foreground text-xs">{formatClockTime(item.ts)}</span>

              <Badge variant={item.variant === "alert" ? "destructive" : "outline"}>
                {item.variant === "alert" ? "Alert" : eventKindLabel(item.kind)}
              </Badge>

              {snapshotUrl ? <SnapshotPreview caption={eventKindLabel(item.kind)} url={snapshotUrl} /> : null}

              <span className="truncate text-sm">{item.summary}</span>
            </li>
          );
        })}
      </ul>
    </ScrollArea>
  );
}
