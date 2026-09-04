import { isTerminalConnectionState } from "./connection-state";
import { playWhep, WhepNoStreamError } from "./whep";

export type WhepSessionState =
  | { status: "connecting" }
  | { status: "playing" }
  | { status: "waiting" }
  | { status: "error"; error: string };

const NO_STREAM_RETRY_DELAY_MS = 3000;

interface RunWhepSessionArgs {
  getAuthorization: () => Promise<string>;
  onStateChange: (state: WhepSessionState) => void;
  signal: AbortSignal;
  url: string;
  video: HTMLVideoElement;
}

export async function runWhepSession({
  getAuthorization,
  onStateChange,
  signal,
  url,
  video,
}: RunWhepSessionArgs): Promise<void> {
  const emit = (state: WhepSessionState) => {
    if (!signal.aborted) {
      onStateChange(state);
    }
  };

  while (!signal.aborted) {
    emit({ status: "connecting" });
    const attempt = new AbortController();

    try {
      // biome-ignore lint/performance/noAwaitInLoops: reconnect attempts are sequential
      const authorization = await getAuthorization();
      const peerConnection = await playWhep(url, authorization, video, AbortSignal.any([signal, attempt.signal]));

      await watchPlayback(peerConnection, emit, signal);
    } catch (caught) {
      if (signal.aborted) {
        return;
      }

      if (!(caught instanceof WhepNoStreamError)) {
        emit({
          status: "error",
          error: caught instanceof Error ? caught.message : "Stream failed",
        });

        return;
      }
    } finally {
      attempt.abort();
    }

    emit({ status: "waiting" });

    await abortableDelay(NO_STREAM_RETRY_DELAY_MS, signal);
  }
}

function watchPlayback(
  peerConnection: RTCPeerConnection,
  emit: (state: WhepSessionState) => void,
  signal: AbortSignal
) {
  return new Promise<void>((resolve) => {
    const finish = () => {
      clearTimeout(timer);
      peerConnection.removeEventListener("connectionstatechange", update);
      signal.removeEventListener("abort", finish);
      peerConnection.close();

      resolve();
    };
    const update = () => {
      const state = peerConnection.connectionState;

      if (state === "connected") {
        clearTimeout(timer);
        emit({ status: "playing" });
      } else if (isTerminalConnectionState(state)) {
        finish();
      }
    };
    const timer = setTimeout(finish, 30_000);

    peerConnection.addEventListener("connectionstatechange", update);
    signal.addEventListener("abort", finish, { once: true });

    if (signal.aborted) {
      finish();
    } else {
      update();
    }
  });
}

function abortableDelay(delayMs: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const finish = () => {
      clearTimeout(timer);
      signal.removeEventListener("abort", finish);

      resolve();
    };
    const timer = setTimeout(finish, delayMs);

    signal.addEventListener("abort", finish, { once: true });

    if (signal.aborted) {
      finish();
    }
  });
}
