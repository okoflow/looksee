export function workflowRoute(workflowId: string): `/workflows/${string}` {
  return `/workflows/${encodeURIComponent(workflowId)}`;
}

export function workflowMonitorRoute(workflowId: string): `/workflows/${string}/monitor` {
  return `/workflows/${encodeURIComponent(workflowId)}/monitor`;
}
