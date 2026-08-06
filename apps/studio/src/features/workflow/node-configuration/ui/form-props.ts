import type { CameraSourceNodeData, NodeData, NodeKind } from "@/entities/workflow";

export interface NodeFormProps<K extends NodeKind> {
  data: Extract<NodeData, { kind: K }>;
  onChange: (data: Extract<NodeData, { kind: K }>) => void;
  upstreamSource?: CameraSourceNodeData | null;
}
