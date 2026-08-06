const TERMINAL_CONNECTION_STATES: ReadonlySet<RTCPeerConnectionState> = new Set(["closed", "disconnected", "failed"]);

export function isTerminalConnectionState(state: RTCPeerConnectionState): boolean {
  return TERMINAL_CONNECTION_STATES.has(state);
}
