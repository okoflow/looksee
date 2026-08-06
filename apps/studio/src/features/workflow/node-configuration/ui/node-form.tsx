"use client";

import { assertNever } from "@/shared/lib/assert-never";
import type { CameraSourceNodeData, NodeData } from "@/entities/workflow";
import { DiscordActionForm } from "./forms/actions/discord-action-form";
import { EmailActionForm } from "./forms/actions/email-action-form";
import { LogAlertActionForm } from "./forms/actions/log-alert-action-form";
import { MqttActionForm } from "./forms/actions/mqtt-action-form";
import { SlackActionForm } from "./forms/actions/slack-action-form";
import { SnapshotActionForm } from "./forms/actions/snapshot-action-form";
import { TelegramActionForm } from "./forms/actions/telegram-action-form";
import { WebhookActionForm } from "./forms/actions/webhook-action-form";
import { DetectForm } from "./forms/detection/detect-form";
import { ClassFilterForm } from "./forms/filters/class-filter-form";
import { CountThresholdFilterForm } from "./forms/filters/count-threshold-filter-form";
import { DebounceFilterForm } from "./forms/filters/debounce-filter-form";
import { DwellFilterForm } from "./forms/filters/dwell-filter-form";
import { IfElseFilterForm } from "./forms/filters/if-else/if-else-filter-form";
import { LineCrossingFilterForm } from "./forms/filters/line-crossing-filter-form";
import { SizeFilterForm } from "./forms/filters/size-filter-form";
import { TimeWindowFilterForm } from "./forms/filters/time-window-filter-form";
import { ZoneFilterForm } from "./forms/filters/zone-filter-form";
import { CameraSourceForm } from "./forms/source/camera-source-form";

interface NodeFormComponentProps {
  data: NodeData;
  modelIds: readonly string[];
  onChange: (data: NodeData) => void;
  upstreamSource: CameraSourceNodeData | null;
}

export function NodeForm({ data, modelIds, onChange, upstreamSource }: NodeFormComponentProps) {
  switch (data.kind) {
    case "camera_source":
      return <CameraSourceForm data={data} onChange={onChange} />;
    case "detect":
      return <DetectForm data={data} onChange={onChange} />;
    case "if_else_filter":
      return <IfElseFilterForm data={data} modelIds={modelIds} onChange={onChange} />;
    case "zone_filter":
      return <ZoneFilterForm data={data} onChange={onChange} upstreamSource={upstreamSource} />;
    case "class_filter":
      return <ClassFilterForm data={data} modelIds={modelIds} onChange={onChange} />;
    case "debounce_filter":
      return <DebounceFilterForm data={data} onChange={onChange} />;
    case "time_window_filter":
      return <TimeWindowFilterForm data={data} onChange={onChange} />;
    case "line_crossing_filter":
      return <LineCrossingFilterForm data={data} onChange={onChange} upstreamSource={upstreamSource} />;
    case "dwell_filter":
      return <DwellFilterForm data={data} onChange={onChange} upstreamSource={upstreamSource} />;
    case "count_threshold_filter":
      return <CountThresholdFilterForm data={data} onChange={onChange} upstreamSource={upstreamSource} />;
    case "size_filter":
      return <SizeFilterForm data={data} onChange={onChange} />;
    case "telegram_action":
      return <TelegramActionForm data={data} onChange={onChange} />;
    case "webhook_action":
      return <WebhookActionForm data={data} onChange={onChange} />;
    case "log_alert_action":
      return <LogAlertActionForm data={data} onChange={onChange} />;
    case "snapshot_action":
      return <SnapshotActionForm data={data} onChange={onChange} />;
    case "email_action":
      return <EmailActionForm data={data} onChange={onChange} />;
    case "mqtt_action":
      return <MqttActionForm data={data} onChange={onChange} />;
    case "discord_action":
      return <DiscordActionForm data={data} onChange={onChange} />;
    case "slack_action":
      return <SlackActionForm data={data} onChange={onChange} />;
    default:
      return assertNever(data);
  }
}
