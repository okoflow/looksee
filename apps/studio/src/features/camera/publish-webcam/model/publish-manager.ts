import { toast } from "sonner";
import { getMediamtxMediaAuthorization } from "@/shared/config";
import { isTerminalConnectionState, publishWhip } from "@/shared/lib/webrtc";
import { cameraWhipUrl } from "../api/mediamtx";

export type PublishStatus = "connecting" | "live" | "reconnecting";

interface PublishState {
  status: PublishStatus;
  stream: MediaStream | null;
}

interface PublishSession {
  attempts: number;
  closePeer: (() => void) | null;
  generation: number;
  retryTimer: ReturnType<typeof setTimeout> | null;
  state: PublishState;
  stream: MediaStream | null;
}

const RECONNECT_BASE_DELAY_MS = 1000;
const RECONNECT_MAX_DELAY_MS = 10_000;

const sessions = new Map<string, PublishSession>();
const listeners = new Set<() => void>();

let statusSnapshot: Record<string, PublishStatus> = {};
let streamSnapshot: Record<string, MediaStream> = {};

function emit() {
  statusSnapshot = Object.fromEntries(
    [...sessions].map(([cameraId, session]) => {
      return [cameraId, session.state.status];
    })
  );

  streamSnapshot = Object.fromEntries(
    [...sessions].flatMap(([cameraId, session]) => {
      return session.state.stream ? [[cameraId, session.state.stream] as const] : [];
    })
  );

  for (const listener of listeners) {
    listener();
  }
}

export function subscribeToPublishStatus(listener: () => void) {
  listeners.add(listener);

  return () => {
    listeners.delete(listener);
  };
}

export function getPublishStatusSnapshot(): Record<string, PublishStatus> {
  return statusSnapshot;
}

export function getPublishStreamSnapshot(): Record<string, MediaStream> {
  return streamSnapshot;
}

export async function startWebcamPublish(cameraId: string): Promise<void> {
  if (sessions.has(cameraId)) {
    return;
  }

  const session: PublishSession = {
    attempts: 0,
    closePeer: null,
    generation: 0,
    retryTimer: null,
    state: { status: "connecting", stream: null },
    stream: null,
  };

  sessions.set(cameraId, session);

  emit();

  await attemptPublish(cameraId, session);
}

export function stopWebcamPublish(cameraId: string) {
  const session = sessions.get(cameraId);

  if (!session) {
    return;
  }

  sessions.delete(cameraId);

  if (session.retryTimer !== null) {
    clearTimeout(session.retryTimer);
  }

  emit();

  session.closePeer?.();
  releaseSessionStream(session);
}

async function attemptPublish(cameraId: string, session: PublishSession): Promise<void> {
  session.generation += 1;

  const { generation } = session;
  const controller = new AbortController();

  session.closePeer = () => {
    controller.abort();
  };

  try {
    const stream = await ensureSessionStream(cameraId, session);

    if (sessions.get(cameraId) !== session) {
      releaseSessionStream(session);

      return;
    }

    if (session.generation !== generation) {
      return;
    }

    session.state = { status: session.state.status, stream };

    emit();

    const { close, peerConnection } = await publishWhip(
      cameraWhipUrl(cameraId),
      getMediamtxMediaAuthorization(),
      stream,
      controller.signal
    );

    session.closePeer = () => {
      controller.abort();

      close();
    };

    peerConnection.addEventListener("connectionstatechange", () => {
      const state = peerConnection.connectionState;

      if (!isTerminalConnectionState(state)) {
        return;
      }

      if (sessions.get(cameraId) !== session || session.generation !== generation) {
        return;
      }

      session.closePeer?.();
      session.closePeer = null;
      scheduleReconnect(cameraId, session, null);
    });

    session.state = { status: "live", stream };
    session.attempts = 0;

    emit();
  } catch (caught) {
    session.closePeer?.();
    session.closePeer = null;

    if (!sessions.has(cameraId)) {
      releaseSessionStream(session);

      return;
    }

    scheduleReconnect(cameraId, session, caught);
  }
}

async function ensureSessionStream(cameraId: string, session: PublishSession): Promise<MediaStream> {
  const current = session.stream;

  if (current && hasLiveVideoTrack(current)) {
    return current;
  }

  if (current) {
    session.stream = null;
    stopTracks(current);
  }

  const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
  session.stream = stream;

  for (const track of stream.getVideoTracks()) {
    track.addEventListener(
      "ended",
      () => {
        if (sessions.get(cameraId) !== session || session.stream !== stream) {
          return;
        }

        session.closePeer?.();
        session.closePeer = null;
        scheduleReconnect(cameraId, session, null);
      },
      { once: true }
    );
  }

  return stream;
}

function scheduleReconnect(cameraId: string, session: PublishSession, caught: unknown) {
  if (session.retryTimer !== null) {
    return;
  }

  if (isPermissionDenied(caught)) {
    sessions.delete(cameraId);

    emit();

    releaseSessionStream(session);
    toast.error("Webcam access denied");

    return;
  }

  if (session.attempts === 0) {
    toast.error("Webcam publish interrupted, reconnecting");
  }

  session.attempts += 1;
  session.state = { status: "reconnecting", stream: session.stream };

  emit();

  const delay = Math.min(RECONNECT_BASE_DELAY_MS * 2 ** (session.attempts - 1), RECONNECT_MAX_DELAY_MS);

  session.retryTimer = setTimeout(() => {
    session.retryTimer = null;

    if (sessions.get(cameraId) !== session) {
      return;
    }

    attemptPublish(cameraId, session);
  }, delay);
}

function hasLiveVideoTrack(stream: MediaStream): boolean {
  return stream.getVideoTracks().some((track) => {
    return track.readyState === "live";
  });
}

function isPermissionDenied(caught: unknown): boolean {
  return caught instanceof DOMException && caught.name === "NotAllowedError";
}

function releaseSessionStream(session: PublishSession) {
  const { stream } = session;

  if (!stream) {
    return;
  }

  session.stream = null;
  stopTracks(stream);
}

function stopTracks(stream: MediaStream) {
  for (const track of stream.getTracks()) {
    track.stop();
  }
}
