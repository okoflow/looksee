"use client";

import { Handle, type NodeProps, Position, useNodeConnections } from "@xyflow/react";
import { cn } from "@/shared/lib/cn";
import { NODE_POLICIES, type OutputPort, type OutputPortId } from "@/entities/workflow";
import type { FlowGraphNode } from "@/features/workflow/graph-editing";
import { getNodeDefinition, summarizeNodeData } from "@/features/workflow/node-configuration";

const PORT_HANDLE_CLASSES: Record<OutputPortId, string> = {
  out: "bg-foreground!",
  if: "bg-sky-500!",
  else: "bg-violet-500!",
};

const PORT_LABEL_CLASSES: Record<OutputPortId, string> = {
  out: "text-foreground",
  if: "text-sky-700",
  else: "text-violet-700",
};

export function FlowNode({ data, selected }: NodeProps<FlowGraphNode>) {
  const { config } = data;

  const definition = getNodeDefinition(config.kind);
  const policy = NODE_POLICIES[config.kind];

  const outgoing = useNodeConnections({ handleType: "source" });

  const Icon = definition.icon;

  const shouldShowTarget = policy.input !== "none";
  const shouldShowPortLabels = policy.outputs.some((port) => {
    return port.label !== undefined;
  });
  const shouldShowLegacyOutput = policy.outputs.length === 0 && outgoing.length > 0;

  return (
    <div
      className={cn("relative min-w-44 rounded-lg border bg-card text-card-foreground shadow-xs transition", {
        "border-ring ring-3 ring-ring/40": selected,
      })}
    >
      {shouldShowTarget ? (
        <Handle
          aria-label={`${definition.label} input`}
          className="size-2! border-2! border-background! bg-foreground!"
          position={Position.Left}
          type="target"
        />
      ) : null}

      <div className={cn("flex items-center gap-2 p-2.5", { "pr-14": shouldShowPortLabels })}>
        <div className={cn("flex size-7 items-center justify-center rounded-md", definition.iconClassName)}>
          <Icon className="size-4" />
        </div>

        <div className="flex min-w-0 flex-col">
          <span className="truncate font-medium text-sm">{definition.label}</span>

          <span className="truncate text-muted-foreground text-xs">{summarizeNodeData(config)}</span>
        </div>
      </div>

      {shouldShowPortLabels ? (
        <div className="pointer-events-none absolute inset-y-0 right-3 flex flex-col justify-center gap-1 font-semibold text-[10px] leading-none">
          {policy.outputs.map((port) => {
            return port.label === undefined ? null : (
              <span className={PORT_LABEL_CLASSES[port.id]} key={port.id}>
                {port.label}
              </span>
            );
          })}
        </div>
      ) : null}

      {policy.outputs.map((port, index) => {
        const hasSingleOutput = policy.outputs.length === 1;

        return (
          <Handle
            aria-label={portAriaLabel(definition.label, port)}
            className={cn("size-2! border-2! border-background!", PORT_HANDLE_CLASSES[port.id])}
            id={hasSingleOutput ? undefined : port.id}
            key={port.id}
            position={Position.Right}
            style={hasSingleOutput ? undefined : { top: portTop(index, policy.outputs.length) }}
            type="source"
          />
        );
      })}

      {shouldShowLegacyOutput ? (
        <Handle
          aria-label={`${definition.label} legacy output`}
          className="size-2! border-2! border-background! bg-foreground!"
          isConnectable={false}
          position={Position.Right}
          type="source"
        />
      ) : null}
    </div>
  );
}

function portAriaLabel(nodeLabel: string, port: OutputPort): string {
  return port.label === undefined ? `${nodeLabel} output` : `${nodeLabel} ${port.label} output`;
}

function portTop(index: number, count: number): string {
  return `${((index + 1) / (count + 1)) * 100}%`;
}
