import ReconnectingWebSocket from "reconnecting-websocket";
import { getWebSocketUrl } from "@/shared/config";

export interface ReconnectingSocketHandle {
  close: () => void;
}

export function openReconnectingSocket(url: string, onMessage: (payload: string) => void): ReconnectingSocketHandle {
  const socket = new ReconnectingWebSocket(url, [], {
    connectionTimeout: 10_000,
    maxEnqueuedMessages: 0,
    maxReconnectionDelay: 30_000,
    minReconnectionDelay: 1000,
    minUptime: 0,
    reconnectionDelayGrowFactor: 2,
  });

  const handleMessage = (message: MessageEvent) => {
    if (typeof message.data === "string") {
      onMessage(message.data);
    }
  };

  socket.addEventListener("message", handleMessage);

  return {
    close: () => {
      socket.removeEventListener("message", handleMessage);
      socket.close(1000, "client closed");
    },
  };
}

export function cameraSocketUrl(cameraId: string): string {
  return `${getWebSocketUrl()}/ws/cameras/${cameraId}`;
}
