import { NODE_POLICIES, type OutputPort, type OutputPortId } from "./node-policies";
import { NODE_ROLES } from "./node-roles";
import type { NodeKind } from "./schema";

export interface ConnectionCandidate {
  source: string;
  sourceHandle?: string | null;
  target: string;
}

export interface ConnectionEdge {
  port: OutputPortId | null;
  source: string;
  target: string;
}

export interface ConnectionViolation {
  message: string;
}

export type ConnectionVerdict = { allowed: true } | { allowed: false; violation: ConnectionViolation };

export function effectiveOutputPort(sourceKind: NodeKind, rawPort: string | null | undefined): OutputPort | null {
  const { outputs } = NODE_POLICIES[sourceKind];

  if (rawPort !== null && rawPort !== undefined) {
    const declared = outputs.find((port) => {
      return port.id === rawPort;
    });

    return declared ?? null;
  }

  return outputs.at(0) ?? null;
}

export function effectiveOutputPortId(sourceKind: NodeKind, rawPort: string | null | undefined): OutputPortId | null {
  return effectiveOutputPort(sourceKind, rawPort)?.id ?? null;
}

export function validateConnection(
  kindsById: ReadonlyMap<string, NodeKind>,
  edges: readonly ConnectionEdge[],
  candidate: ConnectionCandidate
): ConnectionVerdict {
  if (candidate.source === candidate.target) {
    return refuse("A node cannot connect to itself");
  }

  const sourceKind = kindsById.get(candidate.source);
  const targetKind = kindsById.get(candidate.target);

  if (sourceKind === undefined || targetKind === undefined) {
    return refuse("The connection references a missing node");
  }

  if (NODE_POLICIES[sourceKind].outputs.length === 0) {
    return refuse(`A ${describeKind(sourceKind)} node has no outputs`);
  }

  const port = effectiveOutputPort(sourceKind, candidate.sourceHandle);

  if (port === null) {
    return refuse(`Unknown output port on a ${describeKind(sourceKind)} node`);
  }

  if (NODE_POLICIES[targetKind].input === "none") {
    return refuse(`A ${describeKind(targetKind)} node does not accept incoming connections`);
  }

  if (!port.targets.includes(NODE_ROLES[targetKind])) {
    return refuse(`A ${describeKind(sourceKind)} node cannot connect to a ${describeKind(targetKind)} node`);
  }

  const samePortEdges = edges.filter((edge) => {
    return edge.source === candidate.source && edge.port === port.id;
  });

  const isAlreadyConnected = samePortEdges.some((edge) => {
    return edge.target === candidate.target;
  });

  if (isAlreadyConnected) {
    return refuse("These nodes are already connected from this output");
  }

  if (port.maxConnections !== "many" && samePortEdges.length >= port.maxConnections) {
    return refuse(`The output of a ${describeKind(sourceKind)} node is already connected`);
  }

  return { allowed: true };
}

function refuse(message: string): ConnectionVerdict {
  return { allowed: false, violation: { message } };
}

function describeKind(kind: NodeKind): string {
  return kind.replaceAll("_", " ");
}
